"""
Alternative Asset Managers — Secco Capital.
Compares listed alt managers as STOCKS using Yahoo Finance data only.
Not a business comparison: no AUM / FRE / carry / perpetual-capital data.
"""

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.alt_managers.universe import TICKERS, CATEGORIES, GEOS, TILTS
from src.alt_managers import data as dl
from src.alt_managers import metrics

st.set_page_config(
    page_title="Alt Managers | Secco Capital",
    page_icon="◼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS — Secco house style
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=DM+Sans:wght@400;500;600;700&display=swap');
    .stApp { background-color: #F8FAFC; color: #1E293B; }
    .block-container { padding-top: 2rem; padding-bottom: 1rem; max-width: 1500px; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stDeployButton { display: none; }
    header[data-testid="stHeader"] { background: #F8FAFC; }

    .am-header {
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.75rem 0 1.25rem 0; border-bottom: 1px solid #E2E8F0; margin-bottom: 1.25rem;
    }
    .am-title { font-family: 'DM Sans', sans-serif; font-size: 1.4rem; font-weight: 700; color: #1E293B; letter-spacing: -0.02em; }
    .am-subtitle { font-family: 'DM Sans', sans-serif; font-size: 0.8rem; color: #64748B; margin-top: 2px; }
    .am-timestamp { font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #64748B; text-align: right; }

    .section-header {
        font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 600;
        color: #64748B; text-transform: uppercase; letter-spacing: 0.12em;
        padding: 1.1rem 0 0.5rem 0; border-bottom: 1px solid #E2E8F0; margin-bottom: 0.8rem;
    }

    .kpi-card {
        background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px;
        padding: 0.9rem 1.1rem;
    }
    .kpi-label {
        font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; font-weight: 600;
        color: #94A3B8; text-transform: uppercase; letter-spacing: 0.1em;
    }
    .kpi-value { font-family: 'DM Sans', sans-serif; font-size: 1.5rem; font-weight: 700; color: #1E293B; margin-top: 0.2rem; }

    .dd-summary { font-family: 'DM Sans', sans-serif; font-size: 0.85rem; color: #475569; line-height: 1.55; }
    .dd-meta { font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #64748B; margin: 0.4rem 0; }
    .metric-line { display: flex; justify-content: space-between; padding: 0.35rem 0; border-bottom: 1px solid #F1F5F9; font-family: 'DM Sans', sans-serif; font-size: 0.82rem; }
    .metric-line .lbl { color: #64748B; }
    .metric-line .val { color: #1E293B; font-weight: 600; font-family: 'JetBrains Mono', monospace; }

    .stButton > button {
        background: #FFFFFF; color: #1E293B; border: 1px solid #CBD5E1;
        font-family: 'DM Sans', sans-serif; font-size: 0.78rem; font-weight: 600;
        border-radius: 4px; padding: 0.4rem 1.2rem;
    }
    .stButton > button:hover { background: #F1F5F9; border-color: #2563EB; color: #1E293B; }
</style>
""", unsafe_allow_html=True)

GREEN, RED, ACCENT, BORDER, TEXT2 = "#16A34A", "#DC2626", "#2563EB", "#E2E8F0", "#64748B"


def section_header(text):
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Formatting helpers (None -> "—")
# ---------------------------------------------------------------------------
def _frac_to_pct(v):
    return v * 100 if v is not None else None

def fmt_dash(v, fmt="{:.1f}"):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    return fmt.format(v)


# ---------------------------------------------------------------------------
# Load all data
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def load_all():
    fx = dl.fetch_fx()
    rows = []
    failures = {}  # ticker -> [fields]
    for tk, meta in TICKERS.items():
        d = dl.fetch_ticker_data(tk)
        d["_meta"] = meta
        rows.append(d)
        if d["_failed_fields"]:
            failures[tk] = d["_failed_fields"]
    return rows, fx, failures, datetime.now()


with st.spinner("Fetching data for 19 alternative managers (first load can take ~30s)..."):
    ROWS, FX, FAILURES, TS = load_all()

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Alt Managers")
    sel_cat = st.multiselect("Category", CATEGORIES, default=CATEGORIES)
    sel_geo = st.multiselect("Geography", GEOS, default=GEOS)
    sel_tilt = st.multiselect("Tilt", TILTS, default=TILTS)
    st.markdown("---")
    if st.button("Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption("Data: Yahoo Finance (unofficial). Cached 1h.")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    f"""<div class="am-header">
        <div><div class="am-title">◼ Alternative Asset Managers</div>
        <div class="am-subtitle">Listed alt managers compared as stocks · Yahoo Finance only</div></div>
        <div class="am-timestamp">Last refresh: {TS.strftime('%d %b %Y  %H:%M')}</div>
    </div>""",
    unsafe_allow_html=True,
)
if st.button("← Home", key="am_home"):
    st.switch_page("app.py")

# Apply filters
def _shown(d):
    m = d["_meta"]
    return m["category"] in sel_cat and m["geo"] in sel_geo and m["tilt"] in sel_tilt

shown = [d for d in ROWS if _shown(d)]

# ---------------------------------------------------------------------------
# Section 1 — KPI strip
# ---------------------------------------------------------------------------
section_header("Overview")
n_firms = len(shown)
mktcaps_usd = [dl.to_usd(d.get("marketCap"), d["_meta"]["ccy"], FX) for d in shown]
total_mc = sum(v for v in mktcaps_usd if v is not None)
fwd_pes = [d.get("forwardPE") for d in shown if d.get("forwardPE") is not None]
div_ylds = [d.get("dividendYield") for d in shown if d.get("dividendYield") is not None]
med_pe = pd.Series(fwd_pes).median() if fwd_pes else None
med_dy = pd.Series(div_ylds).median() if div_ylds else None

k1, k2, k3, k4 = st.columns(4)
for col, label, val in [
    (k1, "Firms shown", str(n_firms)),
    (k2, "Total Mkt Cap (USD bn)", fmt_dash(total_mc / 1e9 if total_mc else None, "{:,.0f}")),
    (k3, "Median Fwd P/E", fmt_dash(med_pe)),
    (k4, "Median Div Yield", fmt_dash(med_dy) + ("%" if med_dy is not None else "")),
]:
    with col:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">{label}</div><div class="kpi-value">{val}</div></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Section 2 — Comparison table
# ---------------------------------------------------------------------------
section_header("Comparison Table")

table_rows = []
for d in shown:
    m = d["_meta"]
    mc_usd = dl.to_usd(d.get("marketCap"), m["ccy"], FX)
    table_rows.append({
        "Ticker": d["ticker"],
        "Name": m["name"],
        "Category": m["category"],
        "Geo": m["geo"],
        "Tilt": m["tilt"],
        "Price": d.get("currentPrice"),
        "Ccy": m["ccy"],
        "Mkt Cap (USD bn)": mc_usd / 1e9 if mc_usd is not None else None,
        "Fwd P/E": d.get("forwardPE"),
        "P/B": d.get("priceToBook"),
        "EV/EBITDA": d.get("enterpriseToEbitda"),
        "Div Yield %": d.get("dividendYield"),
        "Payout %": _frac_to_pct(d.get("payoutRatio")),
        "Beta": d.get("beta"),
        "YTD %": d.get("ret_ytd"),
        "1Y %": d.get("ret_1y"),
        "3Y % (ann)": d.get("ret_3y"),
        "5Y % (ann)": d.get("ret_5y"),
        "ROE %": _frac_to_pct(d.get("returnOnEquity")),
        "Op Margin %": _frac_to_pct(d.get("operatingMargins")),
        "Insider %": _frac_to_pct(d.get("heldPercentInsiders")),
        "Target Upside %": dl.analyst_upside(d.get("targetMeanPrice"), d.get("currentPrice")),
        "# Analysts": d.get("numberOfAnalystOpinions"),
        "Rec": d.get("recommendationKey"),
    })

df = pd.DataFrame(table_rows)
num_pct = ["Div Yield %", "Payout %", "YTD %", "1Y %", "3Y % (ann)", "5Y % (ann)",
           "ROE %", "Op Margin %", "Insider %", "Target Upside %"]
num_x = ["Fwd P/E", "P/B", "EV/EBITDA", "Beta"]
colcfg = {
    "Price": st.column_config.NumberColumn(format="%.2f"),
    "Mkt Cap (USD bn)": st.column_config.NumberColumn(format="%.1f"),
    "# Analysts": st.column_config.NumberColumn(format="%d"),
}
for c in num_pct:
    colcfg[c] = st.column_config.NumberColumn(format="%.1f%%")
for c in num_x:
    colcfg[c] = st.column_config.NumberColumn(format="%.1f")

st.dataframe(df, column_config=colcfg, hide_index=True, use_container_width=True, height=460)

with st.expander("Explain the columns / data-quality notes"):
    st.markdown("""
- **Price** — latest close in the firm's **native currency** (see Ccy column). Not FX-converted.
- **Mkt Cap (USD bn)** — native market cap converted to USD at the latest spot FX. The only cross-comparable size column.
- **Fwd P/E** — Yahoo's forward P/E off **GAAP EPS estimates**, not FRE/DE. Unreliable for alt managers and *often missing for European listings*.
- **P/B / EV/EBITDA** — `EV/EBITDA` is frequently missing for non-US listings (Yahoo returns no `enterpriseValue`/`ebitda`).
- **Div Yield %** — Yahoo reports this already in percent; shown as-is.
- **Payout %, ROE %, Op Margin %, Insider %** — Yahoo reports these as fractions; multiplied by 100 here.
- **YTD / 1Y** — total return. **3Y / 5Y** — *annualized* (CAGR). Blank if the listing lacks that much history (e.g. CVC, Bridgepoint, Patria IPO'd recently).
- **Target Upside %** — analyst mean target / current price − 1.
- **Rec** — Yahoo's `recommendationKey` (strong_buy / buy / hold / underperform / sell).
- Missing values render as blank to keep columns sortable; the **Data quality** panel below lists exactly which fields failed per ticker.
""")

# Data quality panel
with st.expander(f"Data quality — {len(FAILURES)} ticker(s) with missing fields"):
    if not FAILURES:
        st.write("All fields present for all shown tickers.")
    else:
        for tk, fields in FAILURES.items():
            st.markdown(f"**{tk}** ({TICKERS[tk]['name']}): {', '.join(fields)}")

# ---------------------------------------------------------------------------
# Section 3 — Price chart panel
# ---------------------------------------------------------------------------
section_header("Price Comparison")
default_chart = [t for t in ["BX", "APO", "KKR", "BAM"] if t in TICKERS]
csel1, csel2 = st.columns([3, 1])
with csel1:
    chart_tickers = st.multiselect("Tickers", list(TICKERS.keys()), default=default_chart,
                                   format_func=lambda t: f"{t} · {TICKERS[t]['name']}")
with csel2:
    period = st.radio("Period", list(dl.PERIOD_MAP.keys()), index=4, horizontal=True)

if chart_tickers:
    fig = go.Figure()
    palette = ["#2563EB", "#16A34A", "#F59E0B", "#EC4899", "#14B8A6", "#6366F1", "#DC2626", "#0EA5E9"]
    stat_rows = []
    for i, tk in enumerate(chart_tickers):
        close = dl.fetch_history(tk, dl.PERIOD_MAP[period])
        if close is None or close.empty:
            stat_rows.append({"Ticker": tk, "Name": TICKERS[tk]["name"], "Total Return %": None,
                              "Annualized %": None, "Max Drawdown %": None, "Volatility %": None})
            continue
        rb = metrics.rebase_to_100(close)
        fig.add_trace(go.Scatter(x=rb.index, y=rb.values, mode="lines",
                                 name=f"{TICKERS[tk]['name']} ({tk})",
                                 line=dict(color=palette[i % len(palette)], width=1.8)))
        tot = metrics.total_return(close)
        yrs = max((close.index[-1] - close.index[0]).days / 365.25, 1e-9)
        ann = ((1 + tot / 100) ** (1 / yrs) - 1) * 100 if (tot is not None and (1 + tot / 100) > 0) else None
        stat_rows.append({
            "Ticker": tk,
            "Name": TICKERS[tk]["name"],
            "Total Return %": tot,
            "Annualized %": ann,
            "Max Drawdown %": metrics.max_drawdown(close),
            "Volatility %": metrics.annualized_vol(close),
        })
    fig.update_layout(
        height=380, margin=dict(l=10, r=20, t=20, b=40),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, tickfont=dict(color=TEXT2, size=10)),
        yaxis=dict(showgrid=True, gridcolor=BORDER, tickfont=dict(color=TEXT2, size=10),
                   title=dict(text="Rebased to 100", font=dict(size=10, color=TEXT2))),
        legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="center", x=0.5, font=dict(size=11)),
    )
    st.plotly_chart(fig, use_container_width=True)

    sdf = pd.DataFrame(stat_rows)
    st.dataframe(
        sdf, hide_index=True, use_container_width=True,
        column_config={c: st.column_config.NumberColumn(format="%.1f%%")
                       for c in ["Total Return %", "Annualized %", "Max Drawdown %", "Volatility %"]},
    )
else:
    st.caption("Select at least one ticker to chart.")

# ---------------------------------------------------------------------------
# Section 4 — Single-ticker deep dive
# ---------------------------------------------------------------------------
section_header("Deep Dive")
dd_tk = st.selectbox("Ticker", list(TICKERS.keys()),
                     format_func=lambda t: f"{t} · {TICKERS[t]['name']}")
dd = next((d for d in ROWS if d["ticker"] == dd_tk), None)
left, right = st.columns([1, 1])

with left:
    m = TICKERS[dd_tk]
    st.markdown(f"**{m['name']}** ({dd_tk}) · {m['category']} · {m['tilt']}")
    st.markdown(
        f'<div class="dd-meta">{dd.get("sector") or "—"} · {dd.get("industry") or "—"} · {dd.get("country") or "—"}</div>',
        unsafe_allow_html=True)
    summ = dd.get("longBusinessSummary") or "Business summary unavailable from Yahoo Finance."
    st.markdown(f'<div class="dd-summary">{summ}</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    metric_pairs = [
        ("Price", fmt_dash(dd.get("currentPrice"), "{:.2f}") + f" {m['ccy']}"),
        ("Market Cap (USD bn)", fmt_dash((dl.to_usd(dd.get("marketCap"), m["ccy"], FX) or 0) / 1e9 if dd.get("marketCap") else None, "{:,.1f}")),
        ("Forward P/E", fmt_dash(dd.get("forwardPE"))),
        ("Trailing P/E", fmt_dash(dd.get("trailingPE"))),
        ("Price / Book", fmt_dash(dd.get("priceToBook"))),
        ("EV / EBITDA", fmt_dash(dd.get("enterpriseToEbitda"))),
        ("Dividend Yield", fmt_dash(dd.get("dividendYield")) + ("%" if dd.get("dividendYield") is not None else "")),
        ("ROE", fmt_dash(_frac_to_pct(dd.get("returnOnEquity"))) + ("%" if dd.get("returnOnEquity") is not None else "")),
        ("Beta", fmt_dash(dd.get("beta"), "{:.2f}")),
        ("52W High / Low", f'{fmt_dash(dd.get("fiftyTwoWeekHigh"),"{:.2f}")} / {fmt_dash(dd.get("fiftyTwoWeekLow"),"{:.2f}")}'),
        ("Analyst Target Upside", fmt_dash(dl.analyst_upside(dd.get("targetMeanPrice"), dd.get("currentPrice"))) + ("%" if dd.get("targetMeanPrice") and dd.get("currentPrice") else "")),
    ]
    for lbl, val in metric_pairs:
        st.markdown(f'<div class="metric-line"><span class="lbl">{lbl}</span><span class="val">{val}</span></div>', unsafe_allow_html=True)

with right:
    close5 = dl.fetch_history(dd_tk, "5y")
    if close5 is None or close5.empty:
        st.caption("Price history unavailable.")
    else:
        ma50 = close5.rolling(50).mean()
        ma200 = close5.rolling(200).mean()
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=close5.index, y=close5.values, mode="lines", name="Price",
                                  line=dict(color=ACCENT, width=1.6)))
        fig2.add_trace(go.Scatter(x=ma50.index, y=ma50.values, mode="lines", name="50d MA",
                                  line=dict(color="#F59E0B", width=1.1)))
        fig2.add_trace(go.Scatter(x=ma200.index, y=ma200.values, mode="lines", name="200d MA",
                                  line=dict(color="#94A3B8", width=1.1)))
        fig2.update_layout(
            height=420, margin=dict(l=10, r=20, t=20, b=40),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, tickfont=dict(color=TEXT2, size=10)),
            yaxis=dict(showgrid=True, gridcolor=BORDER, tickfont=dict(color=TEXT2, size=10),
                       title=dict(text=f"Price ({m['ccy']})", font=dict(size=10, color=TEXT2))),
            legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="center", x=0.5, font=dict(size=11)),
        )
        st.plotly_chart(fig2, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 5 — Caveats
# ---------------------------------------------------------------------------
with st.expander("Caveats — read before drawing conclusions"):
    st.markdown("""
- **Yahoo Finance data is unofficial.** Fields may be stale, delayed, or missing without warning. This dashboard never fabricates — missing values show as blank and are listed in the Data quality panel.
- **"Forward P/E" is unreliable for alt managers.** It is based on GAAP EPS, not the Fee-Related Earnings (FRE) or Distributable Earnings (DE) the firms actually guide on. Treat valuation multiples here as rough, not decision-grade.
- **This compares the firms as _stocks_, not as alt-manager businesses.** There is **no AUM, FRE, perpetual capital, fundraising, or accrued-carry data** here — those are the metrics that actually drive these businesses, and none are available free via Yahoo.
- **BN and BAM are two tickers for one franchise** (Brookfield Corp holds a large stake in Brookfield Asset Management). **Do not sum their market caps** — it double-counts.
- **Currency:** market caps are converted to USD at the latest spot FX for comparison; prices stay in native currency.
- **Returns:** YTD and 1Y are total returns; 3Y and 5Y are annualized (CAGR). Recently-listed names (CVC, Bridgepoint, Patria, EQT) will be blank for longer windows.
""")

st.markdown("---")
st.markdown('<div style="text-align:center; font-size:0.65rem; color:#94A3B8; font-family:\'DM Sans\',sans-serif;">Alternative Asset Managers · Secco Capital · Compared as stocks · Not investment advice</div>', unsafe_allow_html=True)
