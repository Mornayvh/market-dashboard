"""
config.py — Asset universe and data source configuration.
Central registry for all tracked instruments. Add or remove assets here only.
"""

from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Asset definition
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Asset:
    name: str
    ticker: Optional[str]          # Yahoo Finance ticker (None if FRED-only)
    fred_id: Optional[str]         # FRED series ID (None if YF-only)
    category: str                  # Grouping key for dashboard layout
    is_rate: bool = False          # True for yields/rates (display as %, not % change)
    is_spread: bool = False        # True for credit spreads (display as bps)
    invert_color: bool = False     # True if "up = bad" (e.g. VIX, spreads)

# ---------------------------------------------------------------------------
# Asset universe — single source of truth
# ---------------------------------------------------------------------------

ASSETS: list[Asset] = [
    # Rates
    Asset("US 10Y Yield",       "^TNX",   "DGS10",          "Rates",   is_rate=True),
    Asset("US 5Y Yield",        "^FVX",   "DGS5",           "Rates",   is_rate=True),
    Asset("Fed Funds Rate",     None,     "DFF",             "Rates",   is_rate=True),

    # Credit Spreads (order: HY, EM, IG)
    Asset("HY Spread",          None,     "BAMLH0A0HYM2",    "Credit",  is_spread=True, invert_color=True),
    Asset("EM Spread",          None,     "BAMLEMCBPIOAS",    "Credit",  is_spread=True, invert_color=True),
    Asset("IG Spread",          None,     "BAMLC0A4CBBB",    "Credit",  is_spread=True, invert_color=True),

    # Equities
    Asset("S&P 500",            "^GSPC",  None,              "Equities"),
    Asset("Russell 2000",       "^RUT",   None,              "Equities"),
    Asset("Nasdaq 100",         "^NDX",   None,              "Equities"),
    Asset("JSE All Share",      "^J203.JO", None,            "Equities"),

    # Commodities
    Asset("Gold",               "GC=F",   None,              "Commodities"),
    Asset("Silver",             "SI=F",   None,              "Commodities"),
    Asset("Copper",             "HG=F",   None,              "Commodities"),
    Asset("Oil (WTI)",          "CL=F",   None,              "Commodities"),

    # Sentiment (Bitcoin only, renamed from Crypto)
    Asset("Bitcoin",            "BTC-USD", None,             "Sentiment"),

    # Volatility
    Asset("VIX",                "^VIX",   None,              "Volatility", invert_color=True),

    # Currency
    Asset("Dollar Index",       "DX-Y.NYB",  None,           "Currency"),
    Asset("EUR/USD",            "EURUSD=X",  None,            "Currency"),
    Asset("USD/GBP",            "USDGBP=X",  None,            "Currency"),
    Asset("USD/ZAR",            "USDZAR=X",  None,            "Currency"),
    Asset("USD/JPY",            "USDJPY=X",  None,            "Currency"),
    Asset("USD/CHF",            "USDCHF=X",  None,            "Currency"),
]

# Convenience lookups
CATEGORIES = ["Rates", "Credit", "Equities", "Commodities", "Sentiment", "Volatility", "Currency"]
ASSETS_BY_CATEGORY = {cat: [a for a in ASSETS if a.category == cat] for cat in CATEGORIES}

# ---------------------------------------------------------------------------
# Equity P/E multiples — ETF proxies for index-level trailing P/E
# These ETFs are used to fetch trailingPE from yfinance .info
# ---------------------------------------------------------------------------
EQUITY_PE_MAP = {
    "S&P 500": "SPY",
    "Russell 2000": "IWM",
    "Nasdaq 100": "QQQ",
    # JSE not available via yfinance ETF info
}

# ---------------------------------------------------------------------------
# FRED configuration
# ---------------------------------------------------------------------------
# Users must set FRED_API_KEY env var. Free key from https://fred.stlouisfed.org/docs/api/api_key.html
FRED_LOOKBACK_DAYS = 365  # How far back to pull FRED history
