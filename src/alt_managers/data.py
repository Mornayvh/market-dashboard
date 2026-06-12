"""data.py — yfinance fetchers, caching, and FX normalization.

Every network call is wrapped in try/except. Missing fields return None and are
recorded in the per-ticker `_failed_fields` list so the UI can surface them.
yfinance is unofficial; fields disappear without warning.
"""

from __future__ import annotations

import logging
import os

import pandas as pd
import requests
import streamlit as st
import yfinance as yf

from src.alt_managers import metrics

logger = logging.getLogger(__name__)

# Financial Modeling Prep — used only for historical quarterly EPS (Yahoo
# doesn't publish a usable quarterly EPS series for these tickers, especially
# the European listings). Free tier: 250 requests/day, US tickers covered
# reliably; European tickers may return empty or 401 on the free tier.
FMP_BASE = "https://financialmodelingprep.com/api/v3"

# Scalar fields pulled from yf.Ticker(...).info
INFO_FIELDS = [
    "longName", "sector", "industry", "country", "currency", "financialCurrency",
    "marketCap", "enterpriseValue", "sharesOutstanding",
    "trailingPE", "forwardPE", "priceToBook", "priceToSalesTrailing12Months",
    "enterpriseToEbitda", "enterpriseToRevenue",
    "dividendYield", "payoutRatio", "fiveYearAvgDividendYield",
    "beta", "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "currentPrice", "previousClose",
    "totalRevenue", "ebitda", "profitMargins", "operatingMargins", "returnOnEquity", "debtToEquity",
    "targetMeanPrice", "targetLowPrice", "targetHighPrice",
    "recommendationMean", "numberOfAnalystOpinions", "recommendationKey",
    "heldPercentInsiders", "heldPercentInstitutions",
    "longBusinessSummary",
]

# FX pairs — value is USD per 1 unit of the foreign currency.
FX_PAIRS = {"EUR": "EURUSD=X", "GBP": "GBPUSD=X", "CHF": "CHFUSD=X", "SEK": "SEKUSD=X"}

PERIOD_MAP = {"1M": "1mo", "6M": "6mo", "LTM": "1y", "3Y": "3y", "5Y": "5y"}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fx() -> dict:
    """Return {currency: USD_per_unit}. USD is 1.0; failed pulls are None."""
    rates = {"USD": 1.0}
    for ccy, pair in FX_PAIRS.items():
        try:
            h = yf.Ticker(pair).history(period="5d")
            rates[ccy] = float(h["Close"].dropna().iloc[-1]) if not h.empty else None
        except Exception as e:
            logger.warning(f"FX fetch failed for {pair}: {e}")
            rates[ccy] = None
    return rates


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_history(ticker: str, period: str = "5y") -> pd.Series | None:
    """Return the auto-adjusted Close series for a ticker, or None on failure."""
    try:
        h = yf.Ticker(ticker).history(period=period, auto_adjust=True)
        if h is None or h.empty or "Close" not in h.columns:
            return None
        s = h["Close"].dropna()
        s.index = pd.to_datetime(s.index).tz_localize(None)
        return s if not s.empty else None
    except Exception as e:
        logger.warning(f"History fetch failed for {ticker} ({period}): {e}")
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ticker_data(ticker: str) -> dict:
    """Fetch all per-ticker fields. Never raises; missing fields are None."""
    result: dict = {"ticker": ticker, "_failed_fields": []}

    info = {}
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception as e:
        logger.warning(f"info fetch failed for {ticker}: {e}")

    for field in INFO_FIELDS:
        val = info.get(field)
        # Treat NaN / empty string as missing
        if val is None or (isinstance(val, float) and pd.isna(val)) or val == "":
            result[field] = None
            result["_failed_fields"].append(field)
        else:
            result[field] = val

    # Price history & return metrics
    close = fetch_history(ticker, "5y")
    if close is None:
        result["_failed_fields"].append("priceHistory")
        result.update({"ret_ltm": None, "ret_3y": None, "ret_5y": None})
    else:
        result["ret_ltm"] = metrics.trailing_total_return(close, 1)
        result["ret_3y"] = metrics.annualized_return(close, 3)
        result["ret_5y"] = metrics.annualized_return(close, 5)
        # Fall back to last close if currentPrice missing
        if result.get("currentPrice") is None:
            result["currentPrice"] = float(close.iloc[-1])

    return result


# Ratios Yahoo builds as (listing-currency price or EV) ÷ (reporting-currency
# statement figure). When a firm lists in one currency but reports in another
# (EQT.ST: SEK price, EUR financials) Yahoo skips the conversion, inflating the
# ratio by the cross rate (~11x for SEK/EUR). P/E fields are NOT affected —
# Yahoo converts the EPS quote fields to the listing currency.
CROSS_CCY_RATIO_FIELDS = [
    "priceToBook", "enterpriseToEbitda", "enterpriseToRevenue",
    "priceToSalesTrailing12Months",
]


def fix_cross_currency_ratios(d: dict, fx: dict) -> None:
    """Correct Yahoo's currency-mismatched valuation ratios in place.

    Multiplies each affected ratio by (USD-per-listing-ccy / USD-per-reporting-
    ccy), i.e. divides out the listing-per-reporting cross rate. EV-based ratios
    keep a small residual error (Yahoo mixes reporting-currency debt/cash into
    the listing-currency market cap when building EV) — a few percent, versus
    the ~11x raw error. If the needed FX rates are missing the raw values are
    known-wrong, so they are blanked rather than shown.
    """
    listing, reporting = d.get("currency"), d.get("financialCurrency")
    if not listing or not reporting or listing == reporting:
        return
    rate_listing, rate_reporting = fx.get(listing), fx.get(reporting)
    if rate_listing is None or rate_reporting is None or rate_reporting == 0:
        for f in CROSS_CCY_RATIO_FIELDS:
            if d.get(f) is not None:
                d[f] = None
                d["_failed_fields"].append(f)
        return
    factor = rate_listing / rate_reporting
    for f in CROSS_CCY_RATIO_FIELDS:
        if d.get(f) is not None:
            d[f] = d[f] * factor


def to_usd(value: float | None, ccy: str, fx: dict) -> float | None:
    """Convert a value in `ccy` to USD using the FX table. None if not convertible."""
    if value is None:
        return None
    rate = fx.get(ccy)
    if rate is None:
        return None
    return value * rate


def analyst_upside(target: float | None, current: float | None) -> float | None:
    """Analyst mean-target upside in percent."""
    if target is None or current is None or current == 0:
        return None
    return (target / current - 1) * 100


# ---------------------------------------------------------------------------
# Historical trailing P/E — Financial Modeling Prep + yfinance daily price
# ---------------------------------------------------------------------------

def fmp_api_key() -> str | None:
    """Return the FMP API key from env or Streamlit secrets, or None.
    Mirrors the FRED / Anthropic key lookup used elsewhere in the repo."""
    key = os.environ.get("FMP_API_KEY")
    if key:
        return key
    try:
        return st.secrets.get("general", {}).get("FMP_API_KEY")
    except Exception:
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_quarterly_eps(ticker: str) -> pd.DataFrame | None:
    """Fetch up to ~6 years of quarterly diluted EPS from FMP for a ticker.

    Returns a DataFrame indexed by fiscal-quarter-end date with a single
    `eps` column (float), sorted ascending. Returns None when no API key
    is configured, when FMP returns an error (e.g. 401 on the free tier
    for some non-US listings), or when no rows are usable.
    """
    key = fmp_api_key()
    if not key:
        return None
    try:
        r = requests.get(f"{FMP_BASE}/income-statement/{ticker}",
                         params={"period": "quarter", "limit": 24, "apikey": key},
                         timeout=10)
        if r.status_code != 200:
            logger.warning(f"FMP {ticker} returned HTTP {r.status_code}")
            return None
        payload = r.json()
        if not isinstance(payload, list) or not payload:
            return None
        rows = []
        for d in payload:
            eps = d.get("eps")
            dt = d.get("date")
            if eps is None or dt is None:
                continue
            try:
                rows.append({"date": pd.to_datetime(dt), "eps": float(eps)})
            except (TypeError, ValueError):
                continue
        if not rows:
            return None
        return pd.DataFrame(rows).set_index("date").sort_index()
    except Exception as e:
        logger.warning(f"FMP fetch failed for {ticker}: {e}")
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def _eps_from_yf_quarterly(ticker: str) -> pd.DataFrame | None:
    """Quarterly diluted (or basic) EPS from yfinance's quarterly_income_stmt.
    ~5-7 quarters of history for most US tickers, often empty for European."""
    try:
        q = yf.Ticker(ticker).quarterly_income_stmt
    except Exception as e:
        logger.warning(f"yfinance quarterly EPS fetch failed for {ticker}: {e}")
        return None
    if q is None or q.empty:
        return None
    for row_name in ("Diluted EPS", "Basic EPS"):
        if row_name in q.index:
            s = q.loc[row_name].dropna()
            rows = [(pd.to_datetime(d), float(v)) for d, v in s.items()
                    if v is not None and not (isinstance(v, float) and pd.isna(v))]
            if rows:
                return pd.DataFrame(rows, columns=["date", "eps"]).set_index("date").sort_index()
    return None


@st.cache_data(ttl=86400, show_spinner=False)
def _eps_from_yf_annual(ticker: str) -> pd.DataFrame | None:
    """Annual diluted (or basic) EPS from yfinance's income_stmt. 3-5 yearly
    rows; annual EPS is already a TTM figure so no rolling sum needed.
    Last-resort fallback that works for European tickers too."""
    try:
        a = yf.Ticker(ticker).income_stmt
    except Exception as e:
        logger.warning(f"yfinance annual EPS fetch failed for {ticker}: {e}")
        return None
    if a is None or a.empty:
        return None
    for row_name in ("Diluted EPS", "Basic EPS"):
        if row_name in a.index:
            s = a.loc[row_name].dropna()
            rows = [(pd.to_datetime(d), float(v)) for d, v in s.items()
                    if v is not None and not (isinstance(v, float) and pd.isna(v))]
            if rows:
                return pd.DataFrame(rows, columns=["date", "eps"]).set_index("date").sort_index()
    return None


def _pe_from_ttm(price: pd.Series, ttm: pd.Series) -> pd.Series | None:
    """Align a TTM EPS series to daily prices as a step function, drop dates
    where TTM ≤ 0 (loss periods produce negative P/E which isn't meaningful to
    plot), and return the resulting P/E series. None if nothing survives."""
    ttm_aligned = (ttm.reindex(price.index.union(ttm.index))
                      .sort_index().ffill().reindex(price.index))
    valid = ttm_aligned.notna() & (ttm_aligned > 0)
    if not valid.any():
        return None
    pe = price[valid] / ttm_aligned[valid]
    return pe if not pe.empty else None


def trailing_pe_series(ticker: str, period: str = "5y") -> tuple[pd.Series | None, str | None]:
    """Build a daily trailing-P/E series with a three-tier fallback chain:

      1. FMP quarterly EPS  → rolling 4Q TTM, ~5y history (best, needs key)
      2. yfinance quarterly → rolling 4Q TTM, ~1-1.5y history (US tickers)
      3. yfinance annual    → annual EPS as step function, ~3-5y sparse line

    Returns (series, source_label) so callers can show provenance. Returns
    (None, None) when every source fails (rare — usually only when even the
    daily price history is missing).
    """
    price = fetch_history(ticker, period)
    if price is None or price.empty:
        return None, None

    # Tier 1: FMP (best quarterly history when available)
    eps_df = fetch_quarterly_eps(ticker)
    if eps_df is not None and len(eps_df) >= 4:
        ttm = eps_df["eps"].rolling(4).sum().dropna()
        pe = _pe_from_ttm(price, ttm) if not ttm.empty else None
        if pe is not None and not pe.empty:
            return pe, "FMP quarterly (rolling-4Q TTM)"

    # Tier 2: yfinance quarterly (short but real TTM)
    eps_df = _eps_from_yf_quarterly(ticker)
    if eps_df is not None and len(eps_df) >= 4:
        ttm = eps_df["eps"].rolling(4).sum().dropna()
        pe = _pe_from_ttm(price, ttm) if not ttm.empty else None
        if pe is not None and not pe.empty:
            return pe, "Yahoo quarterly (rolling-4Q TTM, ~1.5y)"

    # Tier 3: yfinance annual (sparse step function — covers European tickers)
    eps_df = _eps_from_yf_annual(ticker)
    if eps_df is not None and not eps_df.empty:
        pe = _pe_from_ttm(price, eps_df["eps"])
        if pe is not None and not pe.empty:
            return pe, "Yahoo annual EPS (sparse step function)"

    return None, None
