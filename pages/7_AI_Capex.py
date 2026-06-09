"""
AI Capex — Secco Capital.
Capital-allocation dashboard for the mega-cap AI buildout cohort (NVDA, META,
AAPL, MSFT, GOOGL, AMZN). All fundamentals are 10-K annual values from SEC
EDGAR (via src/fundamentals_*); market cap is derived from SEC year-end share
counts × Yahoo Finance prices (split-adjusted). Reads the shared SQLite DB
(data/fundamentals.db); use "Refresh from SEC" to (re)ingest.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

from src import fundamentals_process as fp
from src.config import FUNDAMENTALS_TICKERS as TICKERS, get_sec_user_agent
from src.viz_helpers import COLORS

st.set_page_config(
    page_title="AI Capex | Secco Capital",
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


def section_header(text):
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Display rows: (label, builder). Builder returns {fiscal_year: display_value}.
# Fundamentals come pre-scaled to millions (value_scaled); market cap in $bn.
# ---------------------------------------------------------------------------
DISPLAY_ROWS = [
    ("Shares repurchased (M)",       "repurchase_shares"),
    ("Shares issued (M)",            "issuance_shares"),
    ("Shares outstanding, EOY (M)",  "shares_outstanding"),
    ("Avg basic shares (M)",         "basic_shares"),
    ("Avg diluted shares (M)",       "diluted_shares"),
    ("$ repurchased ($M)",           "repurchase_value"),
    ("$ issued — stock plans ($M)",  "issuance_value"),
    ("Capex: PP&E + intangibles ($M)", "_capex_total"),
    ("Market cap, EOY ($bn)",        "_mc_eoy"),
    ("Avg market cap ($bn)",         "_mc_avg"),
]


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
    """List of (date, ratio) stock splits, used to put as-reported shares on the
    same split basis as yfinance's split-adjusted prices."""
    try:
        s = yf.Ticker(ticker).splits
        if s is None or len(s) == 0:
            return []
        return [(pd.Timestamp(d).tz_localize(None), float(r)) for d, r in s.items()]
    except Exception:
        return []


def market_caps(hist, splits, period_end, shares_raw):
    """(EOY, avg-over-FY) market cap in USD.

    yfinance closes are split-adjusted but SEC shares are as-reported at the time,
    so scale shares by the cumulative split factor for splits AFTER the period end.
    Then market cap = split-adjusted close × split-adjusted shares (split-invariant).
    """
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
# Header + controls
# ---------------------------------------------------------------------------
last = fp.get_last_refresh()
ts_text = (f"Last refresh: {pd.Timestamp(last['run_at']).strftime('%d %b %Y  %H:%M')} UTC "
           f"· {last.get('status')}" if last and last.get("run_at") else "No data yet")
st.markdown(
    f"""<div class="fd-header">
        <div><div class="fd-title">◼ AI Capex</div>
        <div class="fd-subtitle">Capital allocation of the mega-cap AI cohort · SEC 10-K filings ·
        share counts in millions, $ in millions, market cap in $bn</div></div>
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

# ---------------------------------------------------------------------------
# Assemble a tidy per-(ticker, fiscal_year) table across all display metrics
# ---------------------------------------------------------------------------
def metric_map(tkr, metric, col="value_scaled"):
    s = df[(df["ticker"] == tkr) & (df["metric"] == metric)]
    return dict(zip(s["fiscal_year"], s[col]))


records = []
for tk in TICKERS:
    years = sorted(df[df["ticker"] == tk]["fiscal_year"].unique())
    years = years[-10:]                      # last 10 fiscal years
    if not years:
        continue
    pe = metric_map(tk, "shares_outstanding", "period_end")
    pe = {**metric_map(tk, "diluted_shares", "period_end"), **pe}  # fallback period_end
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
            rec[m] = mm.get(y)
        # capex PP&E + intangibles (intangibles often absent → treat as 0 only if PP&E present)
        ct = capex.get(y)
        if ct is not None:
            rec["_capex_total"] = ct + (intan.get(y) or 0.0)
        else:
            rec["_capex_total"] = None
        sh = shares_raw.get(y) if shares_raw.get(y) is not None else diluted_raw.get(y)
        mc_eoy, mc_avg = market_caps(hist, splits, pe.get(y), sh)
        rec["_mc_eoy"] = mc_eoy / 1e9 if mc_eoy is not None else None
        rec["_mc_avg"] = mc_avg / 1e9 if mc_avg is not None else None
        records.append(rec)

tidy = pd.DataFrame(records)

# ---------------------------------------------------------------------------
# Per-company metric table (metrics × fiscal years)
# ---------------------------------------------------------------------------
section_header("Company detail — metrics by fiscal year")
sel = st.selectbox("Company", options=TICKERS, index=0, key="ai_company")
sub = tidy[tidy["ticker"] == sel].sort_values("fiscal_year")
if sub.empty:
    st.info("No rows for this company yet.")
else:
    years = [int(y) for y in sub["fiscal_year"]]
    table = {}
    for label, key in DISPLAY_ROWS:
        table[label] = [sub[sub["fiscal_year"] == y][key].iloc[0] for y in years]
    out = pd.DataFrame(table, index=[str(y) for y in years]).T
    out = out.apply(lambda r: r.map(lambda v: f"{v:,.1f}" if pd.notna(v) else "—"), axis=1)
    st.dataframe(out, use_container_width=True)
    st.caption(
        f"{sel} · per its own fiscal year-end. Blanks (—) are concepts the filer doesn't "
        "tag in its 10-K (e.g. Meta's dual-class shares-outstanding, Amazon/Alphabet stock-plan "
        "proceeds, intangible-asset purchases outside Apple). Market cap = SEC year-end shares × "
        "Yahoo price (split-adjusted)."
    )

# ---------------------------------------------------------------------------
# Capex comparison across the cohort
# ---------------------------------------------------------------------------
section_header("Capex (PP&E + intangibles) — AI cohort ($bn)")
fig = go.Figure()
for i, tk in enumerate(TICKERS):
    s = tidy[(tidy["ticker"] == tk) & tidy["_capex_total"].notna()].sort_values("fiscal_year")
    if s.empty:
        continue
    fig.add_trace(go.Scatter(
        x=[int(y) for y in s["fiscal_year"]], y=s["_capex_total"] / 1e3,  # $M -> $bn
        name=tk, mode="lines+markers",
        line=dict(color=NAVY_PALETTE[i % len(NAVY_PALETTE)], width=2),
        marker=dict(size=6),
    ))
fig.update_layout(
    height=420, margin=dict(l=10, r=10, t=10, b=10),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=11)),
    xaxis=dict(showgrid=False, tickformat="d", dtick=1,
               tickfont=dict(size=10, color=COLORS["text_secondary"], family="JetBrains Mono, monospace")),
    yaxis=dict(showgrid=True, gridcolor=COLORS["border"], zeroline=False,
               title=dict(text="$bn", font=dict(size=11, color=COLORS["text_secondary"])),
               tickfont=dict(size=10, color=COLORS["text_secondary"], family="JetBrains Mono, monospace")),
)
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Full dataset download
# ---------------------------------------------------------------------------
csv = tidy.rename(columns={k: lbl for lbl, k in DISPLAY_ROWS}).to_csv(index=False).encode()
st.download_button("Download full dataset (CSV)", csv,
                   file_name="ai_capex_fundamentals.csv", mime="text/csv")
st.caption("Source: SEC EDGAR companyfacts (10-K / 10-K/A annual values) + Yahoo Finance prices for market cap.")
