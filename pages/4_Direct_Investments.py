"""
Direct Investments — Secco Capital private holdings tracker.
Public-market proxies for Novolex, Kelvion, and Real Chemistry.
"""

from datetime import datetime

import streamlit as st

from src.direct_investments.config import HOLDING_ORDER, get_holding
from src.theme import apply_theme
from src.direct_investments.views import (
    render_holding_header, render_comps, render_sparkline_grid,
    render_fred_indicators, render_trends, render_static_block,
    render_ad_groups, render_capex_chart, section_header,
)

st.set_page_config(
    page_title="Direct Investments | Secco Capital",
    page_icon="◼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Publishes the --tk-* palette the stylesheet below reads from. Must run before
# any chart is built.
apply_theme()

# ---------------------------------------------------------------------------
# CSS — match existing dashboards, driven by the active theme's --tk-* variables
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=DM+Sans:wght@400;500;600;700&display=swap');

    .stApp { background-color: var(--tk-app-bg); color: var(--tk-text); }
    .block-container { padding-top: 2rem; padding-bottom: 1rem; max-width: 1400px; }

    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stDeployButton { display: none; }
    header[data-testid="stHeader"] { background: var(--tk-app-bg); }

    .di-header {
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.75rem 0 1.25rem 0; border-bottom: 1px solid var(--tk-border); margin-bottom: 1.5rem;
    }
    .di-title {
        font-family: 'DM Sans', sans-serif; font-size: 1.4rem;
        font-weight: 700; color: var(--tk-text); letter-spacing: -0.02em;
    }
    .di-subtitle {
        font-family: 'DM Sans', sans-serif; font-size: 0.8rem; color: var(--tk-text-muted); margin-top: 2px;
    }
    .di-timestamp {
        font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: var(--tk-text-muted); text-align: right;
    }

    .section-header {
        font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 600;
        color: var(--tk-text-muted); text-transform: uppercase; letter-spacing: 0.12em;
        padding: 1.1rem 0 0.5rem 0; border-bottom: 1px solid var(--tk-border); margin-bottom: 0.8rem;
    }

    .holding-header {
        background: var(--tk-surface); border: 1px solid var(--tk-border); border-radius: 6px;
        padding: 1rem 1.25rem; margin-bottom: 1rem;
    }
    .holding-name {
        font-family: 'DM Sans', sans-serif; font-size: 1.2rem; font-weight: 700;
        color: var(--tk-text); letter-spacing: -0.01em;
    }
    .holding-desc {
        font-family: 'DM Sans', sans-serif; font-size: 0.85rem; color: var(--tk-text-soft);
        margin-top: 0.25rem;
    }
    .holding-callouts {
        display: flex; gap: 1rem; margin-top: 0.85rem; flex-wrap: wrap;
    }
    .callout-thesis, .callout-risk {
        font-family: 'DM Sans', sans-serif; font-size: 0.78rem;
        padding: 0.5rem 0.75rem; border-radius: 4px; flex: 1; min-width: 240px;
        border: 1px solid var(--tk-border);
    }
    .callout-thesis { background: var(--tk-callout-pos-bg); }
    .callout-risk   { background: var(--tk-callout-neg-bg); }
    .callout-label {
        display: block; font-family: 'JetBrains Mono', monospace; font-size: 0.62rem;
        font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em;
        color: var(--tk-text-muted); margin-bottom: 0.25rem;
    }

    .data-table {
        width: 100%; border-collapse: collapse; margin-bottom: 0.5rem;
        font-family: 'JetBrains Mono', monospace; font-size: 0.78rem;
    }
    .data-table th {
        font-family: 'DM Sans', sans-serif; font-size: 0.63rem; font-weight: 600;
        color: var(--tk-text-muted); text-transform: uppercase; letter-spacing: 0.08em;
        padding: 0.5rem 0.6rem; border-bottom: 1px solid var(--tk-border); text-align: right;
    }
    .data-table th:first-child { text-align: left; }
    .data-table td {
        padding: 0.5rem 0.6rem; border-bottom: 1px solid var(--tk-border-soft);
        color: var(--tk-text); text-align: right;
    }
    .data-table td:first-child {
        text-align: left; font-family: 'DM Sans', sans-serif;
        font-weight: 500; font-size: 0.82rem;
    }
    .data-table tr:hover { background: var(--tk-surface-alt); }

    .stock-ticker {
        font-family: 'JetBrains Mono', monospace; font-size: 0.65rem;
        color: var(--tk-text-faint); margin-left: 0.4rem;
    }
    .comp-name-primary { font-weight: 700; }
    /* HQ country flag; sits before the company name, place name on hover */
    .comp-flag {
        margin-right: 0.4rem; font-size: 0.95rem; cursor: help;
        vertical-align: -0.06em; line-height: 1;
    }
    .primary-chip {
        display: inline-block; font-family: 'JetBrains Mono', monospace;
        font-size: 0.55rem; font-weight: 700; padding: 1px 6px;
        background: var(--tk-accent); color: var(--tk-on-accent); border-radius: 3px; margin-left: 6px;
        letter-spacing: 0.05em;
    }
    .comp-link { color: inherit; text-decoration: none; }
    .comp-link:hover { color: var(--tk-accent); text-decoration: underline; }

    /* Hoverable tooltip on indicator/comp names */
    .has-tooltip {
        position: relative;
        cursor: help;
        border-bottom: 1px dotted var(--tk-text-faint);
    }
    .has-tooltip::after {
        content: attr(data-tooltip);
        position: absolute;
        bottom: calc(100% + 6px); left: 0;
        background: var(--tk-tooltip-bg); color: var(--tk-tooltip-text);
        padding: 0.55rem 0.75rem; border-radius: 4px;
        font-family: 'DM Sans', sans-serif; font-size: 0.72rem; font-weight: 400;
        line-height: 1.4; letter-spacing: normal; text-transform: none;
        white-space: normal; width: 340px;
        z-index: 1000; box-shadow: 0 4px 12px var(--tk-shadow-md);
        opacity: 0; visibility: hidden; transform: translateY(4px);
        transition: opacity 0.12s ease, transform 0.12s ease, visibility 0.12s;
        pointer-events: none;
    }
    .has-tooltip:hover::after {
        opacity: 1; visibility: visible; transform: translateY(0);
    }
    /* Chip strip used for Trends queries — each chip is a hoverable label */
    .tooltip-chip-row {
        display: flex; flex-wrap: wrap; gap: 0.4rem;
        margin: 0.25rem 0 0.75rem 0;
    }
    .tooltip-chip {
        font-family: 'DM Sans', sans-serif; font-size: 0.72rem; font-weight: 500;
        color: var(--tk-text); background: var(--tk-surface-alt); border: 1px solid var(--tk-border);
        padding: 0.25rem 0.6rem; border-radius: 999px;
    }
    /* (i) info icon explaining the search-interest chart — reuses .has-tooltip */
    .info-icon {
        display: inline-flex; align-items: center; justify-content: center;
        width: 17px; height: 17px; border-radius: 50%;
        background: var(--tk-accent); color: var(--tk-on-accent);
        font-family: 'DM Sans', sans-serif; font-size: 0.66rem; font-weight: 700;
        font-style: italic; line-height: 1; cursor: help;
        border: none; border-bottom: none; flex: 0 0 auto;
    }
    .info-icon::after { width: 320px; }   /* wider tooltip for the longer explainer */

    .spark-label {
        display: flex; justify-content: space-between; align-items: baseline;
        font-family: 'DM Sans', sans-serif;
    }
    .spark-name { font-size: 0.82rem; font-weight: 600; color: var(--tk-text); }
    .spark-ticker { font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; color: var(--tk-text-faint); }
    .spark-metric {
        font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;
        color: var(--tk-text-soft); margin-top: 2px;
    }
    .spark-price { color: var(--tk-text); font-weight: 600; }

    .stButton > button {
        background: var(--tk-surface); color: var(--tk-text); border: 1px solid var(--tk-border-strong);
        font-family: 'DM Sans', sans-serif; font-size: 0.78rem; font-weight: 600;
        border-radius: 4px; padding: 0.4rem 1.2rem;
    }
    .stButton > button:hover { background: var(--tk-surface-alt); border-color: var(--tk-accent); color: var(--tk-text); }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar — holding selector
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### Direct Investments")
    holding_name = st.radio(
        "Select holding",
        options=HOLDING_ORDER,
        index=0,
        key="di_holding_radio",
    )
    st.markdown("---")
    if st.button("Refresh data", use_container_width=True, key="di_refresh"):
        st.cache_data.clear()
        st.rerun()
    st.caption("Data: Yahoo Finance, FRED, Google Trends.")
    st.caption("Set `FRED_API_KEY` env var for macro series.")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

ts_str = datetime.now().strftime("%d %b %Y  %H:%M")
st.markdown(
    f"""<div class="di-header">
        <div><div class="di-title">◼ Direct Investments</div>
        <div class="di-subtitle">Private holdings — public-market proxy tracker</div></div>
        <div class="di-timestamp">Last refresh: {ts_str}</div>
    </div>""",
    unsafe_allow_html=True,
)

if st.button("← Home", key="di_home_btn"):
    st.switch_page("app.py")

# ---------------------------------------------------------------------------
# Render selected holding
# ---------------------------------------------------------------------------

holding = get_holding(holding_name)

render_holding_header(holding)

# 1. Public comparables
render_comps(holding)

# 2. Sector benchmark sparklines (indices where available, ETFs otherwise)
render_sparkline_grid("Sector Benchmarks", list(holding.sparklines))

# 3. Extra YF tickers (industry/sentiment — e.g. NVDA, CRWV, NBIS, XBI, or QSR bellwethers)
if holding.extra_tickers:
    extra_title = getattr(holding, "extra_tickers_title", "Industry & Sentiment")
    render_sparkline_grid(extra_title, list(holding.extra_tickers))

# 3b. Supply-side names (e.g. DC power producers for Kelvion)
supplier_tickers = getattr(holding, "supplier_tickers", ()) or ()
if supplier_tickers:
    render_sparkline_grid("Data Center Power", list(supplier_tickers))

# 4. Input-cost FRED PPI series (e.g. resin / recycled materials for Novolex).
# Sits above the macro block: input costs hit the P&L directly, so they read
# first, with the broader supply-chain backdrop underneath.
fred_inputs = getattr(holding, "fred_inputs", ()) or ()
if fred_inputs:
    render_fred_indicators("Input Costs", list(fred_inputs))

# 4b. Macro — commodities (yfinance) + macro FRED indicators, one consolidated section
if holding.commodities or holding.fred_series:
    section_header(getattr(holding, "macro_title", "Macro"))
    if holding.commodities:
        render_sparkline_grid(None, list(holding.commodities))
    if holding.fred_series:
        render_fred_indicators(None, list(holding.fred_series))

# 6. Google Trends sentiment
if holding.trends_queries:
    trends_note = ""
    if holding.key == "kelvion":
        trends_note = "Rising values may indicate increasing community resistance to DC buildout."
    render_trends("Search-Interest", list(holding.trends_queries), note=trends_note)

# 6c. Live quarterly capex charts (EDGAR) — e.g. hyperscaler & neocloud for Kelvion
for chart in getattr(holding, "capex_charts", ()) or ():
    render_capex_chart(chart)

# 7. Static reference data
for block in holding.static_blocks:
    render_static_block(block)

# 7b. Live advertising-spend peer charts (EDGAR) — actual marketing spend for Real Chemistry
ad_groups = getattr(holding, "ad_groups", ()) or ()
if ad_groups:
    render_ad_groups(list(ad_groups))

# 8. Per-holding caveats
if holding.static_caption:
    st.caption(holding.static_caption)

# Footer
st.markdown("---")
st.markdown(
    '<div style="text-align:center; font-size:0.65rem; color:var(--tk-text-faint); '
    'font-family:\'DM Sans\',sans-serif;">'
    'Direct Investments · Secco Capital · Confidential · Not investment advice'
    '</div>',
    unsafe_allow_html=True,
)
