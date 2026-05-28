"""
Alternative Asset Managers — Secco Capital.
Compares listed alt managers as STOCKS using Yahoo Finance data, plus a small
hand-maintained Total-AUM reference table (see src/alt_managers/reference_data.py).
Still not a full business comparison: no FRE / carry / perpetual-capital data.
"""

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.alt_managers.universe import TICKERS, CATEGORIES, GEOS, TILTS
from src.alt_managers import data as dl
from src.alt_managers import metrics
from src.alt_managers import reference_data as ref

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
    .stButton > button:hover { background: #F1F5F9; border-color: #4F7FD6; color: #1E293B; }

    /* ── Table styling — matches Market Dashboard / Stock Watchlist ── */
    .table-scroll { overflow-x: auto; }
    .data-table {
        width: 100%; border-collapse: collapse;
        font-family: 'JetBrains Mono', monospace; font-size: 0.76rem;
    }
    .data-table th {
        font-family: 'DM Sans', sans-serif; font-size: 0.65rem; font-weight: 600;
        color: #64748B; text-transform: uppercase; letter-spacing: 0.08em;
        padding: 0.5rem 0.6rem; border-bottom: 1px solid #E2E8F0; text-align: right;
        white-space: nowrap;
    }
    .data-table th:first-child, .data-table th.txt { text-align: left; }
    .data-table td {
        padding: 0.55rem 0.6rem; border-bottom: 1px solid #F1F5F9;
        text-align: right; color: #1E293B; white-space: nowrap;
    }
    .data-table td:first-child {
        text-align: left; color: #1E293B; font-weight: 500;
        font-family: 'DM Sans', sans-serif; font-size: 0.78rem;
    }
    .data-table td.txt { text-align: left; color: #475569; font-family: 'DM Sans', sans-serif; }
    .data-table tr:hover { background: #F1F5F9; }
    .chg-up { color: #16A34A; }
    .chg-down { color: #DC2626; }
    .chg-flat { color: #64748B; }
</style>
""", unsafe_allow_html=True)

GREEN, RED, ACCENT, BORDER, TEXT2 = "#16A34A", "#DC2626", "#4F7FD6", "#E2E8F0", "#64748B"


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


def _is_num(v):
    return isinstance(v, (int, float)) and not (isinstance(v, float) and pd.isna(v))


def render_html_table(df, fmts, text_cols, color_cols=frozenset()):
    """Render a DataFrame as a styled HTML table matching the .data-table look
    used on the Market Dashboard and Stock Watchlist pages. `text_cols` are
    left-aligned; `color_cols` are tinted green/red by sign. Missing values show
    as "—". Note: unlike st.dataframe, this static table is not sortable."""
    cols = list(df.columns)
    head = "".join(f'<th class="{"txt" if c in text_cols else ""}">{c}</th>' for c in cols)
    body = ""
    for _, row in df.iterrows():
        cells = ""
        for c in cols:
            v = row[c]
            disp = fmts[c].format(v) if (c in fmts and _is_num(v)) else ("—" if not _is_num(v) and (v is None or (isinstance(v, float) and pd.isna(v)) or v == "") else str(v))
            cls = "txt" if c in text_cols else ""
            if c in color_cols and _is_num(v):
                cls = (cls + " " + ("chg-up" if v > 0 else "chg-down" if v < 0 else "chg-flat")).strip()
            cells += f'<td class="{cls}">{disp}</td>'
        body += f"<tr>{cells}</tr>"
    return (f'<div class="table-scroll"><table class="data-table"><thead><tr>{head}</tr>'
            f'</thead><tbody>{body}</tbody></table></div>')


def range_bar(low, high, current, mean=None, ccy="", low_lbl="Low", high_lbl="High"):
    """Horizontal range bar: a track from low->high with a current-price marker
    (and optional mean marker). Returns None if inputs are insufficient."""
    if low is None or high is None or current is None or high <= low:
        return None
    xs = [low, high, current] + ([mean] if mean is not None else [])
    xmin, xmax = min(xs), max(xs)
    pad = (xmax - xmin) * 0.10 or 1
    fig = go.Figure()
    # range track
    fig.add_shape(type="rect", x0=low, x1=high, y0=0.40, y1=0.60,
                  fillcolor="#E2E8F0", line=dict(width=0))
    # optional analyst mean marker (dotted)
    annotations = []
    if mean is not None:
        fig.add_shape(type="line", x0=mean, x1=mean, y0=0.30, y1=0.70,
                      line=dict(color="#64748B", width=2, dash="dot"))
        annotations.append(dict(x=mean, y=0.78, text=f"mean {mean:,.2f}", showarrow=False,
                                xanchor="center", yanchor="bottom", font=dict(size=9, color="#64748B")))
    # current price marker (solid accent)
    fig.add_shape(type="line", x0=current, x1=current, y0=0.22, y1=0.78,
                  line=dict(color=ACCENT, width=3))
    annotations += [
        dict(x=current, y=0.95, text=f"now {current:,.2f}", showarrow=False,
             xanchor="center", yanchor="bottom", font=dict(size=11, color=ACCENT)),
        dict(x=low, y=0.10, text=f"{low_lbl} {low:,.2f}", showarrow=False,
             xanchor="left", yanchor="top", font=dict(size=10, color=TEXT2)),
        dict(x=high, y=0.10, text=f"{high_lbl} {high:,.2f}", showarrow=False,
             xanchor="right", yanchor="top", font=dict(size=10, color=TEXT2)),
    ]
    fig.update_layout(
        height=95, margin=dict(l=8, r=8, t=20, b=22),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False, range=[xmin - pad, xmax + pad]),
        yaxis=dict(visible=False, range=[0, 1]),
        annotations=annotations, showlegend=False,
    )
    return fig


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


with st.spinner(f"Fetching data for {len(TICKERS)} alternative managers (first load can take ~30s)..."):
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
    rd = ref.get(d["ticker"])
    aum = rd.get("total_aum_usd_bn")
    table_rows.append({
        "Ticker": d["ticker"],
        "Name": m["name"],
        "Category": m["category"],
        "Geo": m["geo"],
        "Tilt": m["tilt"],
        "Price": d.get("currentPrice"),
        "Ccy": m["ccy"],
        "AUM (USD bn)": aum,
        "AUM as of": rd.get("as_of"),
        "Fwd P/E": d.get("forwardPE"),
        "Trail P/E": d.get("trailingPE"),
        "P/B": d.get("priceToBook"),
        "EV/EBITDA": d.get("enterpriseToEbitda"),
        "EV/Sales": d.get("enterpriseToRevenue"),
        "Div Yield %": d.get("dividendYield"),
        "Payout %": _frac_to_pct(d.get("payoutRatio")),
        "Beta": d.get("beta"),
        "LTM %": d.get("ret_ltm"),
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
# Drop an OPTIONAL column only when it's empty for every shown ticker. Core columns
# (identity, price, size, returns) are always kept — otherwise a transient Yahoo
# rate-limit on the history endpoint would blank the return columns for all firms and
# make them disappear entirely.
always_keep = {
    "Ticker", "Name", "Category", "Geo", "Tilt", "Ccy",
    "Price", "AUM (USD bn)",
    "LTM %", "3Y % (ann)", "5Y % (ann)",
}
for col in list(df.columns):
    if col not in always_keep and df[col].isna().all():
        df = df.drop(columns=[col])
num_pct = ["Div Yield %", "Payout %", "LTM %", "3Y % (ann)", "5Y % (ann)",
           "ROE %", "Op Margin %", "Insider %", "Target Upside %"]
num_x = ["Fwd P/E", "Trail P/E", "P/B", "EV/EBITDA", "EV/Sales", "Beta"]
fmts = {
    "Price": "{:.2f}",
    "AUM (USD bn)": "{:.0f}",
    "# Analysts": "{:.0f}",
}
for c in num_pct:
    fmts[c] = "{:.1f}%"
for c in num_x:
    fmts[c] = "{:.1f}"
text_cols = {"Ticker", "Name", "Category", "Geo", "Tilt", "Ccy", "AUM as of", "Rec"}
# Signed performance columns get green/red tinting, like the other pages' change cols.
color_cols = {"LTM %", "3Y % (ann)", "5Y % (ann)", "Target Upside %"}

st.markdown(render_html_table(df, fmts, text_cols, color_cols), unsafe_allow_html=True)

with st.expander("Explain the columns / data-quality notes"):
    st.markdown("""
- **Price** — latest close in the firm's **native currency** (see Ccy column). Not FX-converted.
- **AUM (USD bn)** — Total assets under management. **Hand-maintained reference data — not from Yahoo** (Yahoo carries no AUM). Figures are approximate, refreshed manually each quarter; the **AUM as of** column shows the reporting date. *Verify against the firm's disclosure before relying on it.* Blank for BN (Brookfield AUM is reported at BAM — don't double-count) and any firm with no comparable Total-AUM figure.
- **Valuation multiples (Fwd P/E, Trail P/E, P/B, EV/EBITDA, EV/Sales)** — all GAAP-based, off Yahoo's `info` payload. Alt managers themselves guide on **Fee-Related Earnings (FRE)** and **Distributable Earnings (DE)** — these GAAP multiples are *not* what sell-side analysts use to value the firms and will look richer/cheaper than the FRE/DE-based multiples in research notes. Treat them as a rough cross-sectional read, not a price target. *Fwd P/E and EV/EBITDA are frequently missing for European listings; EV/Sales fills in some of those gaps.*
- **Div Yield %** — Yahoo reports this already in percent; shown as-is.
- **Payout %, ROE %, Op Margin %, Insider %** — Yahoo reports these as fractions; multiplied by 100 here.
- **LTM** — last-twelve-months total return (trailing ~365 days). **3Y / 5Y** — *annualized* (CAGR). Blank if the listing lacks that much history (e.g. CVC, EQT listed relatively recently).
- **Target Upside %** — analyst mean target / current price − 1.
- **Rec** — Yahoo's `recommendationKey` (strong_buy / buy / hold / underperform / sell).
- Missing values render as blank to keep columns sortable.
""")

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
    period = st.radio("Period", list(dl.PERIOD_MAP.keys()), index=2, horizontal=True)

if chart_tickers:
    fig = go.Figure()
    palette = ["#4F7FD6", "#16A34A", "#F59E0B", "#EC4899", "#14B8A6", "#6366F1", "#DC2626", "#0EA5E9"]
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
    sfmts = {c: "{:.1f}%" for c in ["Total Return %", "Annualized %", "Max Drawdown %", "Volatility %"]}
    st.markdown(
        render_html_table(sdf, sfmts, text_cols={"Ticker", "Name"},
                          color_cols={"Total Return %", "Annualized %", "Max Drawdown %"}),
        unsafe_allow_html=True)
    st.caption("Total Return = cumulative over the period · Annualized = CAGR · "
               "Max Drawdown = largest peak-to-trough drop · Volatility = annualized daily-return "
               "stdev × √252 (native currency; short periods are noisy).")
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
    mc_usd = dl.to_usd(dd.get("marketCap"), m["ccy"], FX)
    dd_ref = ref.get(dd_tk)
    dd_aum = dd_ref.get("total_aum_usd_bn")
    upside = dl.analyst_upside(dd.get("targetMeanPrice"), dd.get("currentPrice"))
    roe = dd.get("returnOnEquity")
    hi, lo = dd.get("fiftyTwoWeekHigh"), dd.get("fiftyTwoWeekLow")
    # (label, value) — value is None when the underlying field is missing; those lines are skipped.
    metric_pairs = [
        ("Price", None if dd.get("currentPrice") is None else f'{dd["currentPrice"]:.2f} {m["ccy"]}'),
        ("Market Cap (USD bn)", None if mc_usd is None else f'{mc_usd / 1e9:,.1f}'),
        ("Total AUM (USD bn)", None if dd_aum is None else f'{dd_aum:,.0f}  (as of {dd_ref.get("as_of") or "n/a"})'),
        ("Forward P/E", None if dd.get("forwardPE") is None else f'{dd["forwardPE"]:.1f}'),
        ("Trailing P/E", None if dd.get("trailingPE") is None else f'{dd["trailingPE"]:.1f}'),
        ("Price / Book", None if dd.get("priceToBook") is None else f'{dd["priceToBook"]:.1f}'),
        ("EV / EBITDA", None if dd.get("enterpriseToEbitda") is None else f'{dd["enterpriseToEbitda"]:.1f}'),
        ("Dividend Yield", None if dd.get("dividendYield") is None else f'{dd["dividendYield"]:.1f}%'),
        ("ROE", None if roe is None else f'{roe * 100:.1f}%'),
        ("Beta", None if dd.get("beta") is None else f'{dd["beta"]:.2f}'),
        ("52W High / Low", None if (hi is None or lo is None) else f'{hi:.2f} / {lo:.2f}'),
        ("Analyst Target Upside", None if upside is None else f'{upside:.1f}%'),
    ]
    shown_metrics = [(lbl, val) for lbl, val in metric_pairs if val is not None]
    for lbl, val in shown_metrics:
        st.markdown(f'<div class="metric-line"><span class="lbl">{lbl}</span><span class="val">{val}</span></div>', unsafe_allow_html=True)
    if not shown_metrics:
        st.caption("No valuation metrics available from Yahoo for this ticker.")

with right:
    cur = dd.get("currentPrice")

    # 52-week range bar
    bar52 = range_bar(dd.get("fiftyTwoWeekLow"), dd.get("fiftyTwoWeekHigh"), cur,
                      ccy=m["ccy"], low_lbl="52W Low", high_lbl="52W High")
    if bar52 is not None:
        st.markdown('<div class="dd-meta">52-week price range</div>', unsafe_allow_html=True)
        st.plotly_chart(bar52, use_container_width=True, key="bar52")

    # Analyst price-target gauge
    gauge = range_bar(dd.get("targetLowPrice"), dd.get("targetHighPrice"), cur,
                      mean=dd.get("targetMeanPrice"), ccy=m["ccy"],
                      low_lbl="Target Low", high_lbl="Target High")
    if gauge is not None:
        st.markdown('<div class="dd-meta">Analyst price targets vs current</div>', unsafe_allow_html=True)
        st.plotly_chart(gauge, use_container_width=True, key="target_gauge")
    else:
        st.caption("Analyst price-target range unavailable for this ticker.")

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

st.markdown("---")
st.markdown('<div style="text-align:center; font-size:0.65rem; color:#94A3B8; font-family:\'DM Sans\',sans-serif;">Alternative Asset Managers · Secco Capital · Compared as stocks · Not investment advice</div>', unsafe_allow_html=True)
