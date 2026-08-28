"""
app.py — Secco Capital Market Dashboard
Institutional-quality daily macro and market snapshot.
Run: streamlit run app.py
"""

import logging
from datetime import datetime

import streamlit as st
import pandas as pd

from src.config import ASSETS
from src.data_ingest import fetch_all_data
from src.data_process import process_all, get_category_df, compute_vix_average, fetch_equity_pe
from src.theme import apply_theme, page_css
from src.viz_helpers import (
    fmt_value, fmt_change, change_color,
    make_sparkline, make_vix_sparkline, make_ltm_bar_chart,
)

logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Market Dashboard | Secco Capital",
    page_icon="◼",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Publishes the --tk-* palette the stylesheet below reads from, and points
# viz_helpers.COLORS at the same palette so the charts follow. Must run before
# any chart is built.
apply_theme()

# ---------------------------------------------------------------------------
# Custom CSS — house style, driven by the active theme's --tk-* variables
# ---------------------------------------------------------------------------

st.markdown("<style>" + page_css("1400px") + """
    /* ── Metric card ── */
    .metric-card {
        background: var(--tk-surface);
        border: 1px solid var(--tk-border);
        border-radius: 6px;
        padding: 0.75rem 0.9rem;
        margin-bottom: 0.5rem;
        box-shadow: 0 1px 2px var(--tk-shadow-sm);
    }
    .metric-name {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.72rem;
        font-weight: 500;
        color: var(--tk-text-muted);
        margin-bottom: 0.25rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .metric-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.3rem;
        font-weight: 700;
        color: var(--tk-text);
        line-height: 1.2;
    }
    .metric-changes {
        display: flex;
        gap: 0.9rem;
        margin-top: 0.4rem;
    }
    .metric-change-item {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem;
    }
    .metric-change-label {
        color: var(--tk-text-muted);
        margin-right: 0.25rem;
    }

    /* ── Table styling ── */
    .data-table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.76rem;
    }
    .data-table th {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.65rem;
        font-weight: 600;
        color: var(--tk-text-muted);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 0.5rem 0.6rem;
        border-bottom: 1px solid var(--tk-border);
        text-align: right;
    }
    .data-table th:first-child { text-align: left; }
    .data-table td {
        padding: 0.55rem 0.6rem;
        border-bottom: 1px solid var(--tk-border-soft);
        text-align: right;
        color: var(--tk-text);
    }
    .data-table td:first-child {
        text-align: left;
        color: var(--tk-text);
        font-weight: 500;
        font-family: 'DM Sans', sans-serif;
        font-size: 0.78rem;
    }
    .data-table tr:hover { background: var(--tk-surface-alt); }

    /* Status indicator */
    .status-dot {
        display: inline-block;
        width: 6px;
        height: 6px;
        border-radius: 50%;
        margin-right: 6px;
        position: relative;
        top: -1px;
    }
    .status-live { background: var(--tk-pos); }
    .status-stale { background: var(--tk-warn); }
    .status-error { background: var(--tk-neg); }

    /* ── Mobile responsive ── */
    @media (max-width: 768px) {
        .page-header-left { gap: 0.5rem; }
        .metric-card { padding: 0.5rem 0.6rem; }
        .metric-value { font-size: 1rem; }
        .metric-change-item { font-size: 0.6rem; }
        .data-table { font-size: 0.65rem; }
        .data-table th { font-size: 0.55rem; padding: 0.3rem; }
        .data-table td { padding: 0.3rem; }
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300, show_spinner=False)
def load_data():
    """Fetch and process all market data. Cached for 5 min."""
    raw = fetch_all_data()
    metrics = process_all(raw)
    vix_avg = compute_vix_average(raw)
    equity_pe = fetch_equity_pe()
    return raw, metrics, vix_avg, equity_pe, datetime.now()

# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def render_header(timestamp: datetime):
    """Dashboard header with logo, title and timestamp."""
    import base64
    from pathlib import Path

    ts_str = timestamp.strftime("%d %b %Y  %H:%M")

    # Look for logo file in project root (supports png, svg, jpg)
    logo_html = ""
    for ext in ["png", "svg", "jpg", "jpeg", "webp"]:
        logo_path = Path(__file__).parent / f"logo.{ext}"
        if logo_path.exists():
            if ext == "svg":
                svg_content = logo_path.read_text()
                logo_html = f'<div class="page-logo">{svg_content}</div>'
            else:
                b64 = base64.b64encode(logo_path.read_bytes()).decode()
                mime = "image/png" if ext == "png" else f"image/{ext}"
                logo_html = f'<img class="page-logo" src="data:{mime};base64,{b64}" />'
            break

    html = f"""<div class="page-header"><div class="page-header-left">{logo_html}<div><div class="page-title">Market Dashboard</div><div class="page-subtitle">Daily Macro & Market Snapshot</div></div></div><div class="page-timestamp"><span class="status-dot status-live"></span>Last refresh: {ts_str}</div></div>"""
    st.markdown(html, unsafe_allow_html=True)
    if st.button("\u2190 Home", key="home_btn"):
        st.switch_page("app.py")


def render_metric_card(row: pd.Series):
    """Render a single metric card."""
    is_rate = row.get("is_rate", False)
    is_spread = row.get("is_spread", False)
    invert = row.get("invert_color", False)

    value_str = fmt_value(row["latest"], is_rate, is_spread)

    # Build change chips — 1W and LTM only (keeps cards compact)
    changes_html = ""
    for label, key in [("1W", "weekly_chg"), ("LTM", "ltm_chg")]:
        val = row.get(key)
        color = change_color(val, invert)
        formatted = fmt_change(val, is_rate, is_spread)
        changes_html += f'<span class="metric-change-item"><span class="metric-change-label">{label}</span><span style="color:{color}">{formatted}</span></span>'

    name = row.name if isinstance(row.name, str) else row.get("name", "")
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-name">{name}</div>
        <div class="metric-value">{value_str}</div>
        <div class="metric-changes">{changes_html}</div>
    </div>
    """, unsafe_allow_html=True)


def render_data_table(metrics_df: pd.DataFrame, category: str):
    """Render a category as an HTML table."""
    cat_df = get_category_df(metrics_df, category)
    if cat_df.empty:
        st.caption("No data available")
        return

    # Determine appropriate column headers
    is_rate_cat = cat_df["is_rate"].any()
    is_spread_cat = cat_df["is_spread"].any()
    if is_rate_cat:
        chg_suffix = " (abs)"
    elif is_spread_cat:
        chg_suffix = " (bps)"
    else:
        chg_suffix = " (%)"

    rows_html = ""
    for idx, row in cat_df.iterrows():
        is_rate = row["is_rate"]
        is_spread = row["is_spread"]
        invert = row["invert_color"]

        val_str = fmt_value(row["latest"], is_rate, is_spread)

        cells = ""
        for key in ["daily_chg", "weekly_chg", "ltm_chg"]:
            v = row[key]
            color = change_color(v, invert)
            cells += f'<td style="color:{color}">{fmt_change(v, is_rate, is_spread)}</td>'

        rows_html += f"<tr><td>{idx}</td><td>{val_str}</td>{cells}</tr>"

    html = f"""
    <table class="data-table">
        <thead>
            <tr>
                <th>Asset</th>
                <th>Last</th>
                <th>1D{chg_suffix}</th>
                <th>1W{chg_suffix}</th>
                <th>LTM{chg_suffix}</th>
            </tr>
        </thead>
        <tbody>{rows_html}</tbody>
    </table>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_section_header(text: str):
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)


def render_volatility_table(metrics_df: pd.DataFrame, vix_avg: float | None):
    """Render the Volatility table with a 1Y Average VIX row appended."""
    cat_df = get_category_df(metrics_df, "Volatility")
    if cat_df.empty:
        st.caption("No data available")
        return

    rows_html = ""
    for idx, row in cat_df.iterrows():
        invert = row["invert_color"]
        val_str = fmt_value(row["latest"], False, False)
        cells = ""
        for key in ["daily_chg", "weekly_chg", "ltm_chg"]:
            v = row[key]
            color = change_color(v, invert)
            cells += f'<td style="color:{color}">{fmt_change(v, False, False)}</td>'
        rows_html += f"<tr><td>{idx}</td><td>{val_str}</td>{cells}</tr>"

    # Add 1Y Average row
    if vix_avg is not None:
        rows_html += f'<tr><td>1Y Average</td><td>{vix_avg:.1f}</td><td>\u2014</td><td>\u2014</td><td>\u2014</td></tr>'

    html = f"""<table class="data-table"><thead><tr><th style="padding:0.5rem 0.6rem; border-bottom:1px solid var(--tk-border); text-align:left; font-family:'DM Sans',sans-serif; font-size:0.65rem; font-weight:600; color:var(--tk-text-muted); text-transform:uppercase; letter-spacing:0.08em;">Asset</th><th style="padding:0.5rem 0.6rem; border-bottom:1px solid var(--tk-border); text-align:right; font-family:'DM Sans',sans-serif; font-size:0.65rem; font-weight:600; color:var(--tk-text-muted); text-transform:uppercase; letter-spacing:0.08em;">Last</th><th style="padding:0.5rem 0.6rem; border-bottom:1px solid var(--tk-border); text-align:right; font-family:'DM Sans',sans-serif; font-size:0.65rem; font-weight:600; color:var(--tk-text-muted); text-transform:uppercase; letter-spacing:0.08em;">1D (%)</th><th style="padding:0.5rem 0.6rem; border-bottom:1px solid var(--tk-border); text-align:right; font-family:'DM Sans',sans-serif; font-size:0.65rem; font-weight:600; color:var(--tk-text-muted); text-transform:uppercase; letter-spacing:0.08em;">1W (%)</th><th style="padding:0.5rem 0.6rem; border-bottom:1px solid var(--tk-border); text-align:right; font-family:'DM Sans',sans-serif; font-size:0.65rem; font-weight:600; color:var(--tk-text-muted); text-transform:uppercase; letter-spacing:0.08em;">LTM (%)</th></tr></thead><tbody>{rows_html}</tbody></table>"""
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------

def main():
    # Refresh button in sidebar
    with st.sidebar:
        st.markdown("### Settings")
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.markdown("---")
        st.caption("Data: Yahoo Finance, FRED")
        st.caption("Set `FRED_API_KEY` env var for rates & spreads from FRED.")

    # Load data
    with st.spinner("Fetching market data..."):
        raw_data, metrics_df, vix_avg, equity_pe, timestamp = load_data()

    # Header
    render_header(timestamp)

    # Refresh button (top right of main area)
    col_spacer, col_btn = st.columns([6, 1])
    with col_btn:
        if st.button("Refresh", key="refresh_main"):
            st.cache_data.clear()
            st.rerun()

    # ── TOP ROW: Key metrics as cards with sparklines ──
    st.markdown("")
    render_section_header("Key Indicators")
    key_assets = ["S&P 500", "US 10Y Yield", "VIX", "Bitcoin", "Gold", "Oil (Brent)"]
    cols = st.columns(len(key_assets))
    for col, name in zip(cols, key_assets):
        with col:
            if name in metrics_df.index:
                render_metric_card(metrics_df.loc[name])
                # Sparkline below the card
                if name in raw_data:
                    asset_obj = next((a for a in ASSETS if a.name == name), None)
                    if name == "VIX":
                        fig = make_vix_sparkline(
                            raw_data[name], vix_avg=vix_avg,
                            days=252, height=100,
                        )
                    else:
                        fig = make_sparkline(
                            raw_data[name], name,
                            days=252, height=100,
                            invert_color=asset_obj.invert_color if asset_obj else False,
                        )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.caption(f"{name}: No data")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── MAIN GRID: Two columns ──
    data_left, data_right = st.columns([1, 1], gap="large")

    with data_left:
        # Equities
        render_section_header("Equities")
        render_data_table(metrics_df, "Equities")

        # Equity P/E multiples as a table
        if equity_pe and any(v.get("current") is not None for v in equity_pe.values()):
            pe_rows = ""
            for name, data in equity_pe.items():
                cur = f"{data['current']:.1f}x" if data.get("current") is not None else "\u2014"
                avg = f"{data['avg_5y']:.1f}x" if data.get("avg_5y") is not None else "\u2014"
                pe_rows += f'<tr><td style="padding:0.55rem 0.6rem; border-bottom:1px solid var(--tk-border-soft); text-align:left; color:var(--tk-text); font-weight:500; font-family:\'DM Sans\',sans-serif; font-size:0.78rem;">{name}</td><td style="padding:0.55rem 0.6rem; border-bottom:1px solid var(--tk-border-soft); text-align:right; font-family:\'JetBrains Mono\',monospace; font-size:0.76rem; color:var(--tk-text);">{cur}</td><td style="padding:0.55rem 0.6rem; border-bottom:1px solid var(--tk-border-soft); text-align:right; font-family:\'JetBrains Mono\',monospace; font-size:0.76rem; color:var(--tk-text-muted);">{avg}</td></tr>'
            st.markdown(f'<div class="section-header" style="margin-top:12px;">Equity Multiples</div><table class="data-table"><thead><tr><th style="padding:0.5rem 0.6rem; border-bottom:1px solid var(--tk-border); text-align:left; font-family:\'DM Sans\',sans-serif; font-size:0.65rem; font-weight:600; color:var(--tk-text-muted); text-transform:uppercase; letter-spacing:0.08em;">Index</th><th style="padding:0.5rem 0.6rem; border-bottom:1px solid var(--tk-border); text-align:right; font-family:\'DM Sans\',sans-serif; font-size:0.65rem; font-weight:600; color:var(--tk-text-muted); text-transform:uppercase; letter-spacing:0.08em;">Trailing P/E</th><th style="padding:0.5rem 0.6rem; border-bottom:1px solid var(--tk-border); text-align:right; font-family:\'DM Sans\',sans-serif; font-size:0.65rem; font-weight:600; color:var(--tk-text-muted); text-transform:uppercase; letter-spacing:0.08em;">5Y Avg</th></tr></thead><tbody>{pe_rows}</tbody></table>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Rates
        render_section_header("Rates")
        render_data_table(metrics_df, "Rates")

        st.markdown("<br>", unsafe_allow_html=True)

        # Currency
        render_section_header("Currency")
        render_data_table(metrics_df, "Currency")

    with data_right:
        # Credit Spreads
        render_section_header("Credit Spreads")
        render_data_table(metrics_df, "Credit")

        st.markdown("<br>", unsafe_allow_html=True)

        # Commodities
        render_section_header("Commodities")
        render_data_table(metrics_df, "Commodities")

        st.markdown("<br>", unsafe_allow_html=True)

        # Sentiment (Bitcoin only, no sparklines)
        render_section_header("Sentiment")
        render_data_table(metrics_df, "Sentiment")

        st.markdown("<br>", unsafe_allow_html=True)

        # Volatility with 1Y average as a table row
        render_section_header("Volatility")
        render_volatility_table(metrics_df, vix_avg)

    # ── BOTTOM: LTM Performance Charts ──
    st.markdown("<br>", unsafe_allow_html=True)
    render_section_header("LTM Performance")

    chart_cols = st.columns(3)
    chart_categories = ["Equities", "Commodities", "Sentiment"]
    for col, cat in zip(chart_cols, chart_categories):
        with col:
            st.caption(cat)
            fig = make_ltm_bar_chart(metrics_df, cat)
            st.plotly_chart(fig, use_container_width=True)

    # ── Footer ──
    st.markdown("---")
    st.markdown(
        '<div style="text-align:center; font-size:0.65rem; color:var(--tk-text-faint); font-family: \'DM Sans\', sans-serif;">'
        'Market Dashboard v1.0 — Data from Yahoo Finance & FRED — Not investment advice'
        '</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
