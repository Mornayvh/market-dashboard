"""
Stock Watchlist — Secco Capital Holdings Tracker
Live price data for core, connected, and global holdings.
"""

import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Stock Watchlist | Secco Capital",
    page_icon="◼",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# CSS
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

    .watch-header {
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.75rem 0 1.25rem 0; border-bottom: 1px solid #E2E8F0; margin-bottom: 1.5rem;
    }
    .watch-title {
        font-family: 'DM Sans', sans-serif; font-size: 1.4rem;
        font-weight: 700; color: #1E293B; letter-spacing: -0.02em;
    }
    .watch-subtitle {
        font-family: 'DM Sans', sans-serif; font-size: 0.8rem; color: #64748B; margin-top: 2px;
    }

    .section-header {
        font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 600;
        color: #64748B; text-transform: uppercase; letter-spacing: 0.12em;
        padding: 0.6rem 0 0.4rem 0; border-bottom: 1px solid #E2E8F0; margin-bottom: 0.6rem;
    }

    .stock-table {
        width: 100%; border-collapse: collapse;
        font-family: 'JetBrains Mono', monospace; font-size: 0.76rem;
    }
    .stock-table th {
        font-family: 'DM Sans', sans-serif; font-size: 0.63rem; font-weight: 600;
        color: #64748B; text-transform: uppercase; letter-spacing: 0.08em;
        padding: 0.5rem 0.6rem; border-bottom: 1px solid #E2E8F0; text-align: right;
    }
    .stock-table th:first-child { text-align: left; }
    .stock-table td {
        padding: 0.5rem 0.6rem; border-bottom: 1px solid #F1F5F9;
        color: #1E293B; text-align: right;
    }
    .stock-table td:first-child {
        text-align: left; font-family: 'DM Sans', sans-serif;
        font-weight: 500; font-size: 0.78rem;
    }
    .stock-table tr:hover { background: #F1F5F9; }
    .stock-ticker {
        font-family: 'JetBrains Mono', monospace; font-size: 0.65rem;
        color: #94A3B8; margin-left: 0.4rem;
    }
    .chg-up { color: #16A34A; }
    .chg-down { color: #DC2626; }
    .chg-flat { color: #64748B; }

    @media (max-width: 768px) {
        .block-container { padding-left: 0.5rem; padding-right: 0.5rem; max-width: 100%; }
        .watch-header { flex-direction: column; gap: 0.5rem; }
        .watch-title { font-size: 1.1rem; }
        .stock-table { font-size: 0.65rem; }
        .stock-table th { font-size: 0.55rem; padding: 0.3rem; }
        .stock-table td { padding: 0.3rem; }
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Stock definitions
# ---------------------------------------------------------------------------

WATCHLIST = {
    "Core Holdings": [
        ("Richemont", "CFR.SW", "CHF"),
        ("Remgro", "REM.JO", "ZAR"),
        ("Reinet", "REINA.AS", "EUR"),
    ],
    "Connected Holdings": [
        ("BAT (LSE)", "BATS.L", "GBP"),
        ("BAT (JSE)", "BTI.JO", "ZAR"),
        ("FirstRand", "FSR.JO", "ZAR"),
        ("OUTsurance", "OUT.JO", "ZAR"),
        ("Discovery", "DSY.JO", "ZAR"),
    ],
    "Global": [
        ("Berkshire Hathaway", "BRK-B", "USD"),
        ("Apple", "AAPL", "USD"),
        ("Alphabet", "GOOGL", "USD"),
        ("Amazon", "AMZN", "USD"),
        ("Meta", "META", "USD"),
        ("Microsoft", "MSFT", "USD"),
        ("Nvidia", "NVDA", "USD"),
        ("Tesla", "TSLA", "USD"),
        ("Alibaba", "BABA", "USD"),
        ("BYD", "BYDDY", "USD"),
        ("Tencent", "TCEHY", "USD"),
        ("Apollo", "APO", "USD"),
        ("KKR", "KKR", "USD"),
        ("Dell", "DELL", "USD"),
        ("Palo Alto", "PANW", "USD"),
        ("Deere & Co", "DE", "USD"),
        ("Teledyne", "TDY", "USD"),
        ("Waste Management", "WM", "USD"),
    ],
}

CURRENCY_SYMBOLS = {"USD": "$", "GBP": "£", "EUR": "€", "CHF": "CHF ", "ZAR": "R"}

# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

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
    for ticker in all_tickers:
        name, currency, group = ticker_map[ticker]
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="1y", auto_adjust=True)
            if hist is None or hist.empty or "Close" not in hist.columns:
                results.append({
                    "group": group, "name": name, "ticker": ticker, "currency": currency,
                    "price": None, "chg_1d": None, "chg_1w": None, "chg_ltm": None,
                    "high_52w": None, "low_52w": None,
                })
                continue

            hist.index = pd.to_datetime(hist.index).tz_localize(None)
            close = hist["Close"]
            last = float(close.iloc[-1])

            # 1D change
            chg_1d = None
            if len(close) >= 2:
                chg_1d = (last / float(close.iloc[-2]) - 1) * 100

            # 1W change
            chg_1w = None
            week_ago = datetime.now() - timedelta(days=7)
            week_data = close[close.index <= week_ago]
            if not week_data.empty:
                chg_1w = (last / float(week_data.iloc[-1]) - 1) * 100

            # LTM change
            chg_ltm = None
            if len(close) >= 2:
                chg_ltm = (last / float(close.iloc[0]) - 1) * 100

            # 52-week high/low
            high_52w = float(close.max())
            low_52w = float(close.min())

            results.append({
                "group": group, "name": name, "ticker": ticker, "currency": currency,
                "price": last, "chg_1d": chg_1d, "chg_1w": chg_1w, "chg_ltm": chg_ltm,
                "high_52w": high_52w, "low_52w": low_52w,
            })
        except Exception:
            results.append({
                "group": group, "name": name, "ticker": ticker, "currency": currency,
                "price": None, "chg_1d": None, "chg_1w": None, "chg_ltm": None,
                "high_52w": None, "low_52w": None,
            })

    return pd.DataFrame(results), datetime.now()

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

def fmt_chg(val):
    if val is None or pd.isna(val):
        return '<span class="chg-flat">\u2014</span>'
    sign = "+" if val >= 0 else ""
    css_class = "chg-up" if val > 0 else "chg-down" if val < 0 else "chg-flat"
    return f'<span class="{css_class}">{sign}{val:.1f}%</span>'

def section_header(text):
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Render table
# ---------------------------------------------------------------------------

def render_stock_table(df):
    """Render a stock group table as HTML."""
    rows = ""
    for _, row in df.iterrows():
        price = fmt_price(row["price"], row["currency"])
        d1 = fmt_chg(row["chg_1d"])
        w1 = fmt_chg(row["chg_1w"])
        ltm = fmt_chg(row["chg_ltm"])
        hi = fmt_price(row["high_52w"], row["currency"])
        lo = fmt_price(row["low_52w"], row["currency"])

        rows += f"""<tr>
            <td>{row["name"]}<span class="stock-ticker">{row["ticker"]}</span></td>
            <td>{price}</td>
            <td>{d1}</td>
            <td>{w1}</td>
            <td>{ltm}</td>
            <td>{hi}</td>
            <td>{lo}</td>
        </tr>"""

    st.markdown(f"""<table class="stock-table">
        <thead><tr>
            <th>Stock</th><th>Price</th><th>1D</th><th>1W</th><th>LTM</th><th>52W High</th><th>52W Low</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

st.markdown("""<div class="watch-header"><div><div class="watch-title">\u25FC Stock Watchlist</div><div class="watch-subtitle">Core, Connected & Global Holdings</div></div></div>""", unsafe_allow_html=True)

if st.button("\u2190 Home", key="home_btn"):
    st.switch_page("app.py")

with st.spinner("Fetching stock data..."):
    data, timestamp = fetch_watchlist_data()

st.caption(f"Last refresh: {timestamp.strftime('%d %b %Y, %H:%M')}")

for group_name in WATCHLIST.keys():
    section_header(group_name)
    group_df = data[data["group"] == group_name]
    render_stock_table(group_df)
    st.markdown("<br>", unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown('<div style="text-align:center; font-size:0.65rem; color:#94A3B8; font-family:\'DM Sans\',sans-serif;">Stock Watchlist \u00b7 Secco Capital \u00b7 Confidential \u00b7 Not investment advice</div>', unsafe_allow_html=True)
