"""
Stock Watchlist — Secco Capital Holdings Tracker
Live price data for core, connected, and global holdings.
"""

import html

import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

from src.theme import apply_theme, page_css, palette
from src.watchlist import CURRENCY_SYMBOLS, FULL_YEAR_MIN_DAYS, WATCHLIST

st.set_page_config(
    page_title="Stock Watchlist | Secco Capital",
    page_icon="◼",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Publishes the --tk-* palette the stylesheet below reads from. Must run before
# any chart is built.
apply_theme()

# ---------------------------------------------------------------------------
# CSS — house style, driven by the active theme's --tk-* variables
# ---------------------------------------------------------------------------

st.markdown("<style>" + page_css("1400px") + """
    .stock-table {
        width: 100%; border-collapse: collapse;
        font-family: 'JetBrains Mono', monospace; font-size: 0.76rem;
    }
    .stock-table th {
        font-family: 'DM Sans', sans-serif; font-size: 0.63rem; font-weight: 600;
        color: var(--tk-text-muted); text-transform: uppercase; letter-spacing: 0.08em;
        padding: 0.5rem 0.6rem; border-bottom: 1px solid var(--tk-border); text-align: right;
    }
    .stock-table th:first-child { text-align: left; }
    .stock-table td {
        padding: 0.5rem 0.6rem; border-bottom: 1px solid var(--tk-border-soft);
        color: var(--tk-text); text-align: right;
    }
    .stock-table td:first-child {
        text-align: left; font-family: 'DM Sans', sans-serif;
        font-weight: 500; font-size: 0.78rem;
    }
    .stock-table tr:hover { background: var(--tk-surface-alt); }

    /* Hoverable listing note on tickers with an ambiguous / multi-listing story */
    .ticker-note { position: relative; cursor: help; border-bottom: 1px dotted var(--tk-text-faint); }
    .ticker-note::after {
        content: 'ⓘ'; font-size: 0.6rem; color: var(--tk-text-faint);
        margin-left: 0.2rem; vertical-align: 0.1em;
    }
    .ticker-tip {
        visibility: hidden; opacity: 0; transition: opacity 0.12s ease;
        position: absolute; top: 130%; left: 0; z-index: 50;
        width: 260px; padding: 0.55rem 0.65rem;
        background: var(--tk-tooltip-bg); color: var(--tk-tooltip-text); border-radius: 4px;
        box-shadow: 0 4px 14px var(--tk-shadow-lg);
        font-family: 'DM Sans', sans-serif; font-size: 0.68rem;
        font-weight: 400; line-height: 1.45; letter-spacing: 0;
        text-align: left; white-space: normal; text-transform: none;
    }
    .ticker-note:hover .ticker-tip { visibility: visible; opacity: 1; }
    .ticker-tip b { font-weight: 600; color: var(--tk-tooltip-strong); }
    /* "—" in Mkt Cap where no public market cap exists; reason on hover */
    .mcap-na { cursor: help; border-bottom: 1px dotted var(--tk-border-strong); color: var(--tk-text-faint); }

    @media (max-width: 768px) {
        .stock-table { font-size: 0.65rem; }
        .stock-table th { font-size: 0.55rem; padding: 0.3rem; }
        .stock-table td { padding: 0.3rem; }
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Stock definitions
# ---------------------------------------------------------------------------

# Tickers that carry no meaningful public market capitalisation — proxy vehicles,
# funds, or pre-listing entities. Yahoo may still return a figure, so these show
# "—" with the reason on hover rather than a number that invites comparison.
# Currently empty: every name on the watchlist is a listed equity. SPCX was
# briefly listed here in error — SpaceX IPO'd on Nasdaq on 12 June 2026.
MARKET_CAP_INELIGIBLE: dict[str, str] = {}

# Tickers where the listing venue isn't obvious from the symbol — shown as a
# hover box on the ticker in the table.
LISTING_NOTES = {
    "REINA.AS": (
        "<b>Euronext Amsterdam</b> &mdash; primary listing, quoted in EUR. "
        "Reinet Investments S.C.A. is Luxembourg-domiciled but has no LuxSE "
        "equity line. Secondary listing on the JSE (REI, ZAR); no reliable "
        "Yahoo feed for that line."
    ),
}

# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)  # 1h — a market cap doesn't need the 5-min price cadence
def fetch_market_cap(ticker: str):
    """
    Market capitalisation as reported by Yahoo, or None when unavailable.

    Reported in the listing's *major* unit even where the price is quoted in a
    minor one: for BATS.L and the JSE lines, price x shares / marketCap comes to
    exactly 100, i.e. price is in pence/cents while the cap is in GBP/ZAR. So
    the cap is labelled with the declared currency, not the price's unit.
    """
    try:
        mc = (yf.Ticker(ticker).info or {}).get("marketCap")
        return float(mc) if mc else None
    except Exception:
        return None


@st.cache_data(ttl=300)
def fetch_watchlist_data():
    """Fetch price data for all watchlist stocks."""
    all_tickers = []
    ticker_map = {}  # ticker -> (name, currency, group)
    for group, stocks in WATCHLIST.items():
        for name, ticker, currency in stocks:
            all_tickers.append(ticker)
            ticker_map[ticker] = (name, currency, group)

    results = []
    histories = {}  # ticker -> close series for sparklines
    for ticker in all_tickers:
        name, currency, group = ticker_map[ticker]
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="1y", auto_adjust=True)
            if hist is None or hist.empty or "Close" not in hist.columns:
                results.append({
                    "group": group, "name": name, "ticker": ticker, "currency": currency,
                    "price": None, "chg_1d": None, "chg_1m": None, "chg_ltm": None,
                    "high_52w": None, "low_52w": None, "market_cap": None,
                })
                continue

            hist.index = pd.to_datetime(hist.index).tz_localize(None)
            close = hist["Close"].dropna()
            if close.empty:
                results.append({
                    "group": group, "name": name, "ticker": ticker, "currency": currency,
                    "price": None, "chg_1d": None, "chg_1m": None, "chg_ltm": None,
                    "high_52w": None, "low_52w": None, "market_cap": None,
                })
                continue
            last = float(close.iloc[-1])

            # Store history for sparklines
            histories[ticker] = close

            # 1D change
            chg_1d = None
            if len(close) >= 2:
                chg_1d = (last / float(close.iloc[-2]) - 1) * 100

            # 1M change
            chg_1m = None
            month_ago = datetime.now() - timedelta(days=30)
            month_data = close[close.index <= month_ago]
            if not month_data.empty:
                chg_1m = (last / float(month_data.iloc[-1]) - 1) * 100

            # LTM and 52-week figures are only meaningful once there is roughly a
            # year of history. A recent listing (e.g. CXMT, listed 27 Jul 2026)
            # otherwise reports its first few days as a 12-month move and a
            # 52-week range, which the data does not support — show "—" instead.
            span_days = (close.index[-1] - close.index[0]).days if len(close) >= 2 else 0
            has_full_year = span_days >= FULL_YEAR_MIN_DAYS

            chg_ltm = None
            if len(close) >= 2 and has_full_year:
                chg_ltm = (last / float(close.iloc[0]) - 1) * 100

            high_52w = float(close.max()) if has_full_year else None
            low_52w = float(close.min()) if has_full_year else None

            results.append({
                "group": group, "name": name, "ticker": ticker, "currency": currency,
                "price": last, "chg_1d": chg_1d, "chg_1m": chg_1m, "chg_ltm": chg_ltm,
                "high_52w": high_52w, "low_52w": low_52w,
                "market_cap": fetch_market_cap(ticker),
            })
        except Exception:
            results.append({
                "group": group, "name": name, "ticker": ticker, "currency": currency,
                "price": None, "chg_1d": None, "chg_1m": None, "chg_ltm": None,
                "high_52w": None, "low_52w": None, "market_cap": None,
            })

    return pd.DataFrame(results), histories, datetime.now()

# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def fmt_price(val, currency):
    if val is None or pd.isna(val):
        return "\u2014"
    sym = CURRENCY_SYMBOLS.get(currency, "")
    if val >= 10000:
        return f"{sym}{val:,.0f}"
    elif val >= 100:
        return f"{sym}{val:,.1f}"
    return f"{sym}{val:,.2f}"

def fmt_market_cap(val, currency, ticker):
    """
    Market cap as "ISO 1.23T/B/M". ISO codes rather than the price column's
    symbols because six currencies appear here and the cap sits in the major
    unit while some prices sit in the minor one — a bare symbol would conflate
    the two. Ineligible tickers render "—" with the reason on hover.
    """
    reason = MARKET_CAP_INELIGIBLE.get(ticker)
    if reason:
        esc = html.escape(reason, quote=True)
        return f'<span class="mcap-na" title="{esc}">—</span>'
    if val is None or pd.isna(val) or val == 0:
        return "—"
    cur = f"{currency} " if currency else ""
    if val >= 1e12:
        return f"{cur}{val/1e12:.2f}T"
    if val >= 1e9:
        return f"{cur}{val/1e9:.1f}B"
    return f"{cur}{val/1e6:.0f}M"

def fmt_chg(val):
    if val is None or pd.isna(val):
        return '<span class="chg-flat">\u2014</span>'
    sign = "+" if val >= 0 else ""
    css_class = "chg-up" if val > 0 else "chg-down" if val < 0 else "chg-flat"
    return f'<span class="{css_class}">{sign}{val:.1f}%</span>'

def section_header(text):
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)

def make_mini_sparkline(close_series, height=120):
    """Create a minimal LTM line sparkline from a close price series."""
    import plotly.graph_objects as go

    if close_series is None or len(close_series) < 2:
        fig = go.Figure()
        fig.update_layout(height=height, margin=dict(l=0,r=0,t=14,b=0),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          xaxis=dict(visible=False), yaxis=dict(visible=False))
        return fig

    first_val = float(close_series.iloc[0])
    last_val = float(close_series.iloc[-1])
    pal = palette()
    up = last_val >= first_val
    color = pal["pos"] if up else pal["neg"]
    r, g, b = (int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=close_series.index, y=close_series.values,
        mode="lines", line=dict(color=color, width=1.5),
        fill="tozeroy",
        fillcolor=f"rgba({r},{g},{b},0.06)",
        hoverinfo="skip",
    ))

    y_min = float(close_series.min())
    y_max = float(close_series.max())
    y_pad = (y_max - y_min) * 0.08 if y_max > y_min else 1
    y_range = [y_min - y_pad, y_max + y_pad]

    # Date annotations
    start_date = close_series.index[0].strftime("%b %y")
    end_date = close_series.index[-1].strftime("%b %y")

    fig.update_layout(
        height=height, margin=dict(l=0, r=0, t=14, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, range=y_range),
        showlegend=False,
        annotations=[
            dict(
                x=close_series.index[0], y=y_range[1],
                text=start_date, showarrow=False, xanchor="left", yanchor="bottom",
                font=dict(size=9, color=pal["text-faint"], family="JetBrains Mono, monospace"),
            ),
            dict(
                x=close_series.index[-1], y=y_range[1],
                text=end_date, showarrow=False, xanchor="right", yanchor="bottom",
                font=dict(size=9, color=pal["text-faint"], family="JetBrains Mono, monospace"),
            ),
        ],
    )
    return fig

# ---------------------------------------------------------------------------
# Render table
# ---------------------------------------------------------------------------

def render_stock_table(df):
    """Render a stock group table as HTML."""
    rows = ""
    for _, row in df.iterrows():
        price = fmt_price(row["price"], row["currency"])
        d1 = fmt_chg(row["chg_1d"])
        m1 = fmt_chg(row["chg_1m"])
        ltm = fmt_chg(row["chg_ltm"])
        hi = fmt_price(row["high_52w"], row["currency"])
        lo = fmt_price(row["low_52w"], row["currency"])
        mcap = fmt_market_cap(row.get("market_cap"), row["currency"], row["ticker"])

        # Name and ticker together are the hover target, so pointing at either
        # the company name or the symbol opens the listing note.
        cell = f'{row["name"]}<span class="stock-ticker">{row["ticker"]}</span>'
        note = LISTING_NOTES.get(row["ticker"])
        if note:
            cell = (
                f'<span class="ticker-note">{cell}'
                f'<span class="ticker-tip">{note}</span></span>'
            )

        rows += f"""<tr>
            <td>{cell}</td>
            <td>{price}</td>
            <td>{d1}</td>
            <td>{m1}</td>
            <td>{ltm}</td>
            <td>{hi}</td>
            <td>{lo}</td>
            <td>{mcap}</td>
        </tr>"""

    st.markdown(f"""<table class="stock-table">
        <thead><tr>
            <th>Stock</th><th>Price</th><th>1D</th><th>1M</th><th>LTM</th><th>52W High</th><th>52W Low</th><th>Mkt Cap</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

st.markdown("""<div class="page-header"><div><div class="page-title">\u25FC Stock Watchlist</div><div class="page-subtitle">Core, Connected & Global Holdings by Sector</div></div></div>""", unsafe_allow_html=True)

if st.button("\u2190 Home", key="home_btn"):
    st.switch_page("app.py")

with st.spinner("Fetching stock data..."):
    data, histories, timestamp = fetch_watchlist_data()

st.caption(f"Last refresh: {timestamp.strftime('%d %b %Y, %H:%M')}")

SPARKLINE_GROUPS = {"Core Holdings", "Connected Holdings"}

for group_name in WATCHLIST.keys():
    section_header(group_name)
    group_df = data[data["group"] == group_name]
    render_stock_table(group_df)

    # Sparklines for Core and Connected holdings
    if group_name in SPARKLINE_GROUPS:
        stocks_in_group = [s for s in WATCHLIST[group_name]]
        cols = st.columns(len(stocks_in_group))
        for col, (name, ticker, currency) in zip(cols, stocks_in_group):
            with col:
                st.caption(name)
                if ticker in histories:
                    fig = make_mini_sparkline(histories[ticker])
                    st.plotly_chart(fig, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown('<div style="text-align:center; font-size:0.65rem; color:var(--tk-text-faint); font-family:\'DM Sans\',sans-serif;">Stock Watchlist \u00b7 Secco Capital \u00b7 Confidential \u00b7 Not investment advice</div>', unsafe_allow_html=True)
