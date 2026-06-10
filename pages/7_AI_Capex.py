"""
AI Capex & Fundamentals — Secco Capital.
Blended capital-allocation + fundamentals view for the mega-cap AI cohort
(NVDA, META, AAPL, MSFT, GOOGL, AMZN). All fundamentals are 10-K annual values
from SEC EDGAR (via src/fundamentals_*); market cap is derived from SEC year-end
share counts × split-adjusted Yahoo Finance prices. Reads the shared SQLite DB
(data/fundamentals.db); use "Refresh from SEC" to (re)ingest.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

from src import fundamentals_process as fp
from src.config import (
    FUNDAMENTALS_TICKERS as TICKERS,
    FUNDAMENTALS_METRICS as METRICS,
    get_sec_user_agent,
)
from src.viz_helpers import COLORS

st.set_page_config(
    page_title="AI Capex & Fundamentals | Secco Capital",
    page_icon="◼",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=DM+Sans:wght@400;500;600;700&display=swap');
    .stApp { background-color: #F8FAFC; color: #1E293B; }
    .block-container { padding-top: 2rem; padding-bottom: 1rem; max-width: 1500px; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stDeployButton { display: none; }
    header[data-testid="stHeader"] { background: #F8FAFC; }
    .fd-header { display: flex; justify-content: space-between; align-items: center;
        padding: 0.75rem 0 1.25rem 0; border-bottom: 1px solid #E2E8F0; margin-bottom: 1.25rem; }
    .fd-title { font-family: 'DM Sans', sans-serif; font-size: 1.4rem; font-weight: 700; color: #1E293B; letter-spacing: -0.02em; }
    .fd-subtitle { font-family: 'DM Sans', sans-serif; font-size: 0.8rem; color: #64748B; margin-top: 2px; }
    .fd-timestamp { font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #64748B; text-align: right; }
    .section-header { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 600;
        color: #64748B; text-transform: uppercase; letter-spacing: 0.12em;
        padding: 1.1rem 0 0.5rem 0; border-bottom: 1px solid #E2E8F0; margin-bottom: 0.8rem; }
    .stButton > button { background: #FFFFFF; color: #1E293B; border: 1px solid #CBD5E1;
        font-family: 'DM Sans', sans-serif; font-size: 0.78rem; font-weight: 600; border-radius: 4px; padding: 0.4rem 1.2rem; }
    .stButton > button:hover { background: #F1F5F9; border-color: #4F7FD6; color: #1E293B; }
</style>
""", unsafe_allow_html=True)

NAVY_PALETTE = ["#0A2A4A", "#15528A", "#2E7BC4", "#5BA0DA", "#93C0EA", "#1B4079"]
TICKER_PALETTE = [COLORS["accent"], COLORS["green"], "#1E3A8A",
                  COLORS["red"], COLORS["neutral"], COLORS["text_secondary"]]


def section_header(text):
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)


def ticker_colors(tickers):
    return {t: TICKER_PALETTE[i % len(TICKER_PALETTE)] for i, t in enumerate(sorted(tickers))}


def style_fig(fig, height, y_title=""):
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=COLORS["text_primary"]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    font=dict(size=11, color=COLORS["text_secondary"])),
        xaxis=dict(showgrid=False, tickformat="d", dtick=1,
                   tickfont=dict(size=10, color=COLORS["text_secondary"], family="JetBrains Mono, monospace")),
        yaxis=dict(showgrid=True, gridcolor=COLORS["border"], zeroline=False,
                   title=dict(text=y_title, font=dict(size=11, color=COLORS["text_secondary"])),
                   tickfont=dict(size=10, color=COLORS["text_secondary"], family="JetBrains Mono, monospace")),
    )
    return fig


# Per-company detail rows: (label, key). Units are standardised so rows are
# comparable across companies — every share count is in millions (M) and every
# dollar figure is in billions ($bn). Share metrics arrive pre-scaled to millions
# from load_frame; the dollar rows below are normalised to $bn when assembled.
DISPLAY_ROWS = [
    ("Shares repurchased (M)",         "repurchase_shares"),
    ("Shares issued (M)",              "issuance_shares"),
    ("Shares outstanding, EOY (M)",    "shares_outstanding"),
    ("Avg basic shares (M)",           "basic_shares"),
    ("Avg diluted shares (M)",         "diluted_shares"),
    ("$ repurchased ($bn)",            "repurchase_value"),
    ("$ issued — stock plans ($bn)",   "issuance_value"),
    ("Capex: PP&E + intangibles ($bn)", "_capex_total"),
    ("Market cap, EOY ($bn)",          "_mc_eoy"),
    ("Avg market cap ($bn)",           "_mc_avg"),
]

# Dollar metrics pulled from load_frame arrive scaled to $M; divide by 1e3 → $bn.
DOLLAR_M_TO_BN = {"repurchase_value", "issuance_value"}


@st.cache_data(ttl=3600, show_spinner=False)
def load_fundamentals(tickers: tuple):
    return fp.load_frame(tickers=list(tickers) or None)


@st.cache_data(ttl=3600, show_spinner=False)
def price_history(ticker: str):
    """Daily split-adjusted closes (yfinance always split-adjusts OHLC)."""
    try:
        df = yf.Ticker(ticker).history(period="max", auto_adjust=False)
        if df is None or df.empty or "Close" not in df.columns:
            return None
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df[["Close"]].dropna()
    except Exception:
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def split_history(ticker: str):
    """(date, ratio) splits — puts as-reported shares on yfinance's split-adjusted basis."""
    try:
        s = yf.Ticker(ticker).splits
        if s is None or len(s) == 0:
            return []
        return [(pd.Timestamp(d).tz_localize(None), float(r)) for d, r in s.items()]
    except Exception:
        return []


def market_caps(hist, splits, period_end, shares_raw):
    """(EOY, avg-over-FY) market cap in USD. yfinance closes are split-adjusted but
    SEC shares are as-reported, so scale shares by the cumulative split factor for
    splits AFTER the period end; market cap is then split-invariant."""
    if hist is None or hist.empty or shares_raw is None or pd.isna(shares_raw):
        return (None, None)
    try:
        pe = pd.Timestamp(period_end)
    except (ValueError, TypeError):
        return (None, None)
    win = hist[(hist.index > pe - pd.Timedelta(days=365)) & (hist.index <= pe + pd.Timedelta(days=6))]
    if win.empty:
        return (None, None)
    factor = 1.0
    for d, r in splits:
        if d > pe:
            factor *= r
    shares_adj = shares_raw * factor
    close = win["Close"]
    return (float(close.iloc[-1]) * shares_adj, float(close.mean()) * shares_adj)


# ---------------------------------------------------------------------------
# Header + refresh
# ---------------------------------------------------------------------------
last = fp.get_last_refresh()
ts_text = (f"Last refresh: {pd.Timestamp(last['run_at']).strftime('%d %b %Y  %H:%M')} UTC "
           f"· {last.get('status')}" if last and last.get("run_at") else "No data yet")
st.markdown(
    f"""<div class="fd-header">
        <div><div class="fd-title">◼ AI Capex &amp; Fundamentals</div>
        <div class="fd-subtitle">Capital allocation &amp; fundamentals of the mega-cap AI cohort · SEC 10-K filings ·
        share counts in millions, all $ figures in billions</div></div>
        <div class="fd-timestamp">{ts_text}</div>
    </div>""",
    unsafe_allow_html=True,
)

c1, c2 = st.columns([1, 1])
with c1:
    if st.button("← Home", key="ai_home"):
        st.switch_page("app.py")
with c2:
    refresh = st.button("Refresh from SEC", type="primary", key="ai_refresh")

if refresh:
    with st.spinner("Pulling 10-K facts from SEC EDGAR for the AI cohort…"):
        try:
            ua = get_sec_user_agent() or "Secco Capital Dashboard mornay@seccocapital.com"
            result = fp.refresh_all(tickers=TICKERS, user_agent=ua)
            load_fundamentals.clear()
            st.success(f"Refreshed — {result['total_rows']} rows written.")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Refresh failed: {exc}")

df = load_fundamentals(tuple(sorted(TICKERS)))
if df.empty:
    st.info("No data yet — click **Refresh from SEC** to pull the AI cohort's 10-K history.")
    st.stop()

tk_colors = ticker_colors(df["ticker"].unique())

# ---------------------------------------------------------------------------
# Assemble tidy per-(ticker, fiscal_year) table across all display metrics
# ---------------------------------------------------------------------------
def metric_map(tkr, metric, col="value_scaled"):
    s = df[(df["ticker"] == tkr) & (df["metric"] == metric)]
    return dict(zip(s["fiscal_year"], s[col]))


records = []
for tk in TICKERS:
    years = sorted(df[df["ticker"] == tk]["fiscal_year"].unique())[-10:]
    if not years:
        continue
    pe = {**metric_map(tk, "diluted_shares", "period_end"),
          **metric_map(tk, "shares_outstanding", "period_end")}
    capex = metric_map(tk, "capex"); intan = metric_map(tk, "intangibles")
    shares_raw = metric_map(tk, "shares_outstanding", "value")
    diluted_raw = metric_map(tk, "diluted_shares", "value")
    hist = price_history(tk)
    splits = split_history(tk)
    base = {m: metric_map(tk, m) for m in
            ("repurchase_shares", "issuance_shares", "shares_outstanding",
             "basic_shares", "diluted_shares", "repurchase_value", "issuance_value")}
    for y in years:
        rec = {"ticker": tk, "fiscal_year": y}
        for m, mm in base.items():
            v = mm.get(y)
            rec[m] = (v / 1e3 if v is not None else None) if m in DOLLAR_M_TO_BN else v
        ct = capex.get(y)
        # capex + intangibles are in $M; normalise to $bn for the detail table.
        rec["_capex_total"] = (ct + (intan.get(y) or 0.0)) / 1e3 if ct is not None else None
        sh = shares_raw.get(y) if shares_raw.get(y) is not None else diluted_raw.get(y)
        mc_eoy, mc_avg = market_caps(hist, splits, pe.get(y), sh)
        rec["_mc_eoy"] = mc_eoy / 1e9 if mc_eoy is not None else None
        rec["_mc_avg"] = mc_avg / 1e9 if mc_avg is not None else None
        records.append(rec)

tidy = pd.DataFrame(records)

# ---------------------------------------------------------------------------
# Metric explorer — trend across the cohort + latest-year comparison
# ---------------------------------------------------------------------------
section_header("Metric explorer")
sel_metric = st.selectbox("Metric", options=list(METRICS.keys()),
                          format_func=lambda k: METRICS[k]["name"], index=0, key="ai_metric")
unit_label = "$M" if METRICS[sel_metric]["unit"] == "USD" else "shares (M)"
trend = df[df["metric"] == sel_metric].sort_values("fiscal_year")

left, right = st.columns([3, 2])
with left:
    section_header(f"{METRICS[sel_metric]['name']} — trend ({unit_label})")
    if trend.empty:
        st.caption("No data for this metric.")
    else:
        fig = go.Figure()
        for tk in sorted(trend["ticker"].unique()):
            sub = trend[trend["ticker"] == tk]
            fig.add_trace(go.Scatter(
                x=sub["fiscal_year"], y=sub["value_scaled"], name=tk, mode="lines+markers",
                line=dict(color=tk_colors[tk], width=2), marker=dict(size=6)))
        st.plotly_chart(style_fig(fig, 380, unit_label), use_container_width=True)
with right:
    section_header(f"Latest year — {METRICS[sel_metric]['name']}")
    if not trend.empty:
        latest_year = int(trend["fiscal_year"].max())
        snap = trend[trend["fiscal_year"] == latest_year].sort_values("value_scaled", ascending=False)
        bar = go.Figure(go.Bar(x=snap["ticker"], y=snap["value_scaled"],
                               marker_color=[tk_colors[t] for t in snap["ticker"]]))
        bar = style_fig(bar, 380, unit_label)
        bar.update_xaxes(tickformat=None, dtick=None, type="category",
                         tickfont=dict(family="DM Sans, sans-serif", size=11))
        st.plotly_chart(bar, use_container_width=True)
        st.caption(f"Fiscal year {latest_year} (per each filer's own year-end)")

# ---------------------------------------------------------------------------
# Capex (PP&E + intangibles) across the cohort
# ---------------------------------------------------------------------------
section_header("Capex (PP&E + intangibles) — AI cohort ($bn)")
fig = go.Figure()
for i, tk in enumerate(TICKERS):
    s = tidy[(tidy["ticker"] == tk) & tidy["_capex_total"].notna()].sort_values("fiscal_year")
    if s.empty:
        continue
    fig.add_trace(go.Scatter(
        x=[int(y) for y in s["fiscal_year"]], y=s["_capex_total"], name=tk,
        mode="lines+markers", line=dict(color=NAVY_PALETTE[i % len(NAVY_PALETTE)], width=2),
        marker=dict(size=6)))
st.plotly_chart(style_fig(fig, 420, "$bn"), use_container_width=True)

# ---------------------------------------------------------------------------
# Combined buybacks vs issuances
# ---------------------------------------------------------------------------
section_header("Combined buybacks vs issuances (shares, M)")
rep = fp.pivot_metric(df, "repurchase_shares")
iss = fp.pivot_metric(df, "issuance_shares")
if not rep.empty or not iss.empty:
    years = sorted(set(rep.index) | set(iss.index))
    rep_tot = rep.reindex(years).sum(axis=1) if not rep.empty else pd.Series(0, index=years)
    iss_tot = iss.reindex(years).sum(axis=1) if not iss.empty else pd.Series(0, index=years)
    comb = go.Figure()
    comb.add_trace(go.Scatter(x=years, y=rep_tot, name="Repurchases", mode="lines+markers",
                              line=dict(color=COLORS["accent"], width=2)))
    comb.add_trace(go.Scatter(x=years, y=iss_tot, name="Issuances", mode="lines+markers",
                              line=dict(color=COLORS["neutral"], width=2)))
    st.plotly_chart(style_fig(comb, 340, "shares (M)"), use_container_width=True)
    st.caption("Share counts are not split-normalized across filers; totals can be dominated "
               "by the largest-share-count company.")

# ---------------------------------------------------------------------------
# Per-company detail — metrics by fiscal year
# ---------------------------------------------------------------------------
section_header("Company detail — metrics by fiscal year")
sel = st.selectbox("Company", options=TICKERS, index=0, key="ai_company")
sub = tidy[tidy["ticker"] == sel].sort_values("fiscal_year")
if sub.empty:
    st.info("No rows for this company yet.")
else:
    years = [int(y) for y in sub["fiscal_year"]]
    table = {label: [sub[sub["fiscal_year"] == y][key].iloc[0] for y in years]
             for label, key in DISPLAY_ROWS}
    out = pd.DataFrame(table, index=[str(y) for y in years]).T
    out = out.apply(lambda r: r.map(lambda v: f"{v:,.1f}" if pd.notna(v) else "—"), axis=1)
    st.dataframe(out, use_container_width=True)
    st.caption(
        f"{sel} · per its own fiscal year-end. Blanks (—) are concepts the filer doesn't tag "
        "in its 10-K (e.g. Meta's dual-class shares-outstanding, Amazon/Alphabet stock-plan "
        "proceeds, intangible-asset purchases outside Apple). Market cap = SEC year-end shares × "
        "Yahoo price (split-adjusted)."
    )

# ---------------------------------------------------------------------------
# Full dataset download
# ---------------------------------------------------------------------------
csv = tidy.rename(columns={k: lbl for lbl, k in DISPLAY_ROWS}).to_csv(index=False).encode()
st.download_button("Download full dataset (CSV)", csv,
                   file_name="ai_capex_fundamentals.csv", mime="text/csv")
st.caption("Source: SEC EDGAR companyfacts (10-K / 10-K/A annual values) + Yahoo Finance prices for market cap.")
