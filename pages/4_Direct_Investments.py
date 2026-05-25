"""
Direct Investments — Secco Capital private holdings tracker.
Public-market proxies for Novolex, Kelvion, and Real Chemistry.
"""

from datetime import datetime

import streamlit as st

from src.direct_investments.config import HOLDINGS, HOLDING_ORDER, get_holding
from src.direct_investments.views import (
    render_holding_header, render_comps, render_sparkline_grid,
    render_fred_indicators, render_trends, render_static_block,
    resolve_real_chemistry_sparklines,
)

st.set_page_config(
    page_title="Direct Investments | Secco Capital",
    page_icon="◼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS — match existing dashboards
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=DM+Sans:wght@400;500;600;700&display=swap');

    .stApp { background-color: #F8FAFC; color: #1E293B; }
    .block-container { padding-top: 2rem; padding-bottom: 1rem; max-width: 1400px; }

    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stDeployButton { display: none; }
    header[data-testid="stHeader"] { background: #F8FAFC; }

    .di-header {
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.75rem 0 1.25rem 0; border-bottom: 1px solid #E2E8F0; margin-bottom: 1.5rem;
    }
    .di-title {
        font-family: 'DM Sans', sans-serif; font-size: 1.4rem;
        font-weight: 700; color: #1E293B; letter-spacing: -0.02em;
    }
    .di-subtitle {
        font-family: 'DM Sans', sans-serif; font-size: 0.8rem; color: #64748B; margin-top: 2px;
    }
    .di-timestamp {
        font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #64748B; text-align: right;
    }

    .section-header {
        font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 600;
        color: #64748B; text-transform: uppercase; letter-spacing: 0.12em;
        padding: 1.1rem 0 0.5rem 0; border-bottom: 1px solid #E2E8F0; margin-bottom: 0.8rem;
    }

    .holding-header {
        background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px;
        padding: 1rem 1.25rem; margin-bottom: 1rem;
    }
    .holding-name {
        font-family: 'DM Sans', sans-serif; font-size: 1.2rem; font-weight: 700;
        color: #1E293B; letter-spacing: -0.01em;
    }
    .holding-desc {
        font-family: 'DM Sans', sans-serif; font-size: 0.85rem; color: #475569;
        margin-top: 0.25rem;
    }
    .holding-callouts {
        display: flex; gap: 1rem; margin-top: 0.85rem; flex-wrap: wrap;
    }
    .callout-thesis, .callout-risk {
        font-family: 'DM Sans', sans-serif; font-size: 0.78rem;
        padding: 0.5rem 0.75rem; border-radius: 4px; flex: 1; min-width: 240px;
        border: 1px solid #E2E8F0;
    }
    .callout-thesis { background: rgba(22,163,74,0.05); }
    .callout-risk   { background: rgba(220,38,38,0.04); }
    .callout-label {
        display: block; font-family: 'JetBrains Mono', monospace; font-size: 0.62rem;
        font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em;
        color: #64748B; margin-bottom: 0.25rem;
    }

    .data-table {
        width: 100%; border-collapse: collapse; margin-bottom: 0.5rem;
        font-family: 'JetBrains Mono', monospace; font-size: 0.78rem;
    }
    .data-table th {
        font-family: 'DM Sans', sans-serif; font-size: 0.63rem; font-weight: 600;
        color: #64748B; text-transform: uppercase; letter-spacing: 0.08em;
        padding: 0.5rem 0.6rem; border-bottom: 1px solid #E2E8F0; text-align: right;
    }
    .data-table th:first-child { text-align: left; }
    .data-table td {
        padding: 0.5rem 0.6rem; border-bottom: 1px solid #F1F5F9;
        color: #1E293B; text-align: right;
    }
    .data-table td:first-child {
        text-align: left; font-family: 'DM Sans', sans-serif;
        font-weight: 500; font-size: 0.82rem;
    }
    .data-table tr:hover { background: #F1F5F9; }

    .stock-ticker {
        font-family: 'JetBrains Mono', monospace; font-size: 0.65rem;
        color: #94A3B8; margin-left: 0.4rem;
    }
    .comp-name-primary { font-weight: 700; }
    .primary-chip {
        display: inline-block; font-family: 'JetBrains Mono', monospace;
        font-size: 0.55rem; font-weight: 700; padding: 1px 6px;
        background: #2563EB; color: white; border-radius: 3px; margin-left: 6px;
        letter-spacing: 0.05em;
    }

    /* Hoverable tooltip on indicator/comp names */
    .has-tooltip {
        position: relative;
        cursor: help;
        border-bottom: 1px dotted #94A3B8;
    }
    .has-tooltip::after {
        content: attr(data-tooltip);
        position: absolute;
        bottom: calc(100% + 6px); left: 0;
        background: #1E293B; color: #F8FAFC;
        padding: 0.55rem 0.75rem; border-radius: 4px;
        font-family: 'DM Sans', sans-serif; font-size: 0.72rem; font-weight: 400;
        line-height: 1.4; letter-spacing: normal; text-transform: none;
        white-space: normal; width: 280px;
        z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.18);
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
        color: #1E293B; background: #F1F5F9; border: 1px solid #E2E8F0;
        padding: 0.25rem 0.6rem; border-radius: 999px;
    }

    .spark-label {
        display: flex; justify-content: space-between; align-items: baseline;
        font-family: 'DM Sans', sans-serif;
    }
    .spark-name { font-size: 0.82rem; font-weight: 600; color: #1E293B; }
    .spark-ticker { font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; color: #94A3B8; }
    .spark-metric {
        font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;
        color: #475569; margin-top: 2px;
    }
    .spark-price { color: #1E293B; font-weight: 600; }

    .stButton > button {
        background: #FFFFFF; color: #1E293B; border: 1px solid #CBD5E1;
        font-family: 'DM Sans', sans-serif; font-size: 0.78rem; font-weight: 600;
        border-radius: 4px; padding: 0.4rem 1.2rem;
    }
    .stButton > button:hover { background: #F1F5F9; border-color: #2563EB; color: #1E293B; }
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

# 2. Sector ETF sparklines (with runtime ETF selection for Real Chemistry)
sparks = (
    resolve_real_chemistry_sparklines(holding)
    if holding.key == "real_chemistry"
    else list(holding.sparklines)
)
render_sparkline_grid("Sector ETFs", sparks)

# 3. Extra YF tickers (industry/sentiment — e.g. NVDA, CRWV, NBIS, XBI)
if holding.extra_tickers:
    render_sparkline_grid("Industry & Sentiment", list(holding.extra_tickers))

# 4. Commodities / macro (yfinance)
if holding.commodities:
    render_sparkline_grid("Commodities & Macro", list(holding.commodities))

# 5. FRED indicators
if holding.fred_series:
    render_fred_indicators("Macro Indicators", list(holding.fred_series))

# 6. Google Trends sentiment
if holding.trends_queries:
    trends_note = ""
    if holding.key == "kelvion":
        trends_note = "Rising values may indicate increasing community resistance to DC buildout."
    render_trends("Search-Interest Sentiment", list(holding.trends_queries), note=trends_note)

# 7. Static reference data
for block in holding.static_blocks:
    render_static_block(block)

# 8. Per-holding caveats
if holding.static_caption:
    st.caption(holding.static_caption)

# Footer
st.markdown("---")
st.markdown(
    '<div style="text-align:center; font-size:0.65rem; color:#94A3B8; '
    'font-family:\'DM Sans\',sans-serif;">'
    'Direct Investments · Secco Capital · Confidential · Not investment advice'
    '</div>',
    unsafe_allow_html=True,
)
