"""
config.py — Asset universe and data source configuration.
Central registry for all tracked instruments. Add or remove assets here only.
Also holds the SEC EDGAR fundamentals settings (companies, metrics, API,
database) used by src/fundamentals_*.py and pages/6_Fundamentals.py.
"""

import os
from dataclasses import dataclass
from pathlib import Path
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
    Asset("Oil (Brent)",          "BZ=F",   "DCOILBRENTEU",    "Commodities"),

    # Sentiment
    Asset("Bitcoin",            "BTC-USD", None,             "Sentiment"),
    Asset("GameStop",           "GME",     None,             "Sentiment"),
    Asset("Mag 7",              "MAGS",    None,             "Sentiment"),
    Asset("10Y-2Y Spread",      None,     "T10Y2Y",          "Sentiment",  is_rate=True, invert_color=True),

    # Volatility
    Asset("VIX",                "^VIX",   None,              "Volatility", invert_color=True),

    # Currency
    Asset("Dollar Index",       "DX-Y.NYB",  None,           "Currency"),
    Asset("EUR/USD",            "EURUSD=X",  None,            "Currency"),
    Asset("GBP/USD",            "GBPUSD=X",  None,            "Currency"),
    Asset("USD/ZAR",            "USDZAR=X",  None,            "Currency"),
    Asset("USD/JPY",            "USDJPY=X",  None,            "Currency"),
    Asset("CHF/USD",            "CHFUSD=X",  None,            "Currency"),
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
}

# ---------------------------------------------------------------------------
# FRED configuration
# ---------------------------------------------------------------------------
# Users must set FRED_API_KEY env var. Free key from https://fred.stlouisfed.org/docs/api/api_key.html
FRED_LOOKBACK_DAYS = 365  # How far back to pull FRED history

# ===========================================================================
# SEC EDGAR fundamentals
# Settings for the Fundamentals page (pages/6_Fundamentals.py) and the
# src/fundamentals_* modules. Edit FUNDAMENTALS_TICKERS / FUNDAMENTALS_METRICS
# to change what's tracked — tickers only; CIKs resolve automatically.
# ===========================================================================

def get_sec_user_agent() -> Optional[str]:
    """Read the SEC User-Agent from env var or Streamlit Cloud secrets.

    The SEC requires a descriptive User-Agent (name + email) on every request
    and blocks requests without one, so there is deliberately no fallback —
    set SEC_USER_AGENT, e.g. "Secco Capital mornay@seccocapital.com".
    """
    ua = os.environ.get("SEC_USER_AGENT")
    if not ua:
        try:
            import streamlit as st
            ua = st.secrets.get("general", {}).get("SEC_USER_AGENT")
        except Exception:
            pass
    return ua


SEC_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
# Single-concept endpoint — tiny payload (one XBRL tag for one company), good for live use.
SEC_COMPANYCONCEPT_URL = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{tag}.json"

# SEC asks for < 10 requests/second. Sleep between calls keeps us safe.
SEC_RATE_LIMIT_SECONDS = 0.15

# SQLite file under data/ (gitignored). Swap for a Postgres URL later
# (e.g. "postgresql+psycopg://user:pass@host/db") and the SQLAlchemy layer
# keeps working with minimal changes.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
FUNDAMENTALS_DB_PATH = PROJECT_ROOT / "data" / "fundamentals.db"
FUNDAMENTALS_DB_URL = f"sqlite:///{FUNDAMENTALS_DB_PATH}"

# Companies to track — EDIT FREELY. Just tickers; CIK is resolved automatically.
FUNDAMENTALS_TICKERS = ["NVDA", "META", "AAPL", "MSFT", "GOOGL", "AMZN"]

# Metrics. Each metric has:
#   - a friendly name (shown in the UI)
#   - a unit ("USD" or "shares")
#   - an ordered list of candidate XBRL (taxonomy, tag) pairs. The ingester
#     tries them in priority order PER FISCAL YEAR (a later tag only fills
#     years earlier tags didn't cover), because filers tag the same concept
#     differently — and rename tags across eras.
#   - scale: divide raw values by this for display (1e6 = millions)
FUNDAMENTALS_METRICS = {
    "capex": {
        "name": "Capital Expenditure",
        "unit": "USD",
        "scale": 1e6,
        # Cash-flow-statement "purchases of property & equipment" — NOT the MD&A
        # "capital expenditures" figure (they differ). Apply consistently.
        "tags": [
            ("us-gaap", "PaymentsToAcquirePropertyPlantAndEquipment"),
            ("us-gaap", "PaymentsToAcquireProductiveAssets"),
            ("us-gaap", "PaymentsForCapitalImprovements"),
        ],
    },
    "diluted_shares": {
        "name": "Weighted Avg. Diluted Shares",
        "unit": "shares",
        "scale": 1e6,
        "tags": [
            ("us-gaap", "WeightedAverageNumberOfDilutedSharesOutstanding"),
            ("us-gaap", "WeightedAverageNumberOfShareOutstandingBasicAndDiluted"),
        ],
    },
    "repurchase_shares": {
        "name": "Share Repurchases (shares)",
        "unit": "shares",
        "scale": 1e6,
        "tags": [
            ("us-gaap", "StockRepurchasedDuringPeriodShares"),
            ("us-gaap", "StockRepurchasedAndRetiredDuringPeriodShares"),
            ("us-gaap", "TreasuryStockSharesAcquired"),
        ],
    },
    "issuance_shares": {
        "name": "Share Issuances (shares)",
        "unit": "shares",
        "scale": 1e6,
        "tags": [
            ("us-gaap", "StockIssuedDuringPeriodSharesNewIssues"),
            ("us-gaap", "StockIssuedDuringPeriodSharesShareBasedCompensation"),
            ("us-gaap", "StockIssuedDuringPeriodSharesStockOptionsExercised"),
            # AMZN tags its (benefit-plan) issuances this way; appended last so
            # it only fills years the tags above don't cover.
            ("us-gaap", "StockIssuedDuringPeriodSharesEmployeeBenefitPlan"),
        ],
    },
    "repurchase_value": {
        "name": "Repurchase Value ($)",
        "unit": "USD",
        "scale": 1e6,
        "tags": [
            ("us-gaap", "PaymentsForRepurchaseOfCommonStock"),
        ],
    },
    "issuance_value": {
        "name": "Stock Issued — Proceeds ($)",
        "unit": "USD",
        "scale": 1e6,
        # Proceeds from share issuance under stock/option plans. Sparsely tagged —
        # Amazon and Alphabet don't report it, so expect gaps.
        "tags": [
            ("us-gaap", "ProceedsFromIssuanceOfCommonStock"),
            ("us-gaap", "ProceedsFromStockOptionsExercised"),
            ("us-gaap", "ProceedsFromIssuanceOfSharesUnderIncentiveAndShareBasedCompensationPlans"),
        ],
    },
    "shares_outstanding": {
        "name": "Shares Outstanding (year-end)",
        "unit": "shares",
        "scale": 1e6,
        # Balance-sheet shares at period end. Meta's dual-class structure isn't
        # captured by the single us-gaap tag, so Meta may be blank.
        "tags": [
            ("us-gaap", "CommonStockSharesOutstanding"),
            ("dei", "EntityCommonStockSharesOutstanding"),
        ],
    },
    "basic_shares": {
        "name": "Weighted Avg. Basic Shares",
        "unit": "shares",
        "scale": 1e6,
        "tags": [
            ("us-gaap", "WeightedAverageNumberOfSharesOutstandingBasic"),
            ("us-gaap", "WeightedAverageNumberOfShareOutstandingBasicAndDiluted"),
        ],
    },
    "intangibles": {
        "name": "Intangible Asset Purchases",
        "unit": "USD",
        "scale": 1e6,
        # Most of the set bundles intangibles into PP&E / "other"; typically only
        # Apple reports this line, so capex (PP&E)+intangibles ≈ PP&E elsewhere.
        "tags": [
            ("us-gaap", "PaymentsToAcquireIntangibleAssets"),
        ],
    },
}
