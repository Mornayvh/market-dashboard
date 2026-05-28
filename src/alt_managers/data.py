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
    "longName", "sector", "industry", "country", "currency",
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


def trailing_pe_series(ticker: str, period: str = "5y") -> pd.Series | None:
    """Build a daily trailing P/E series for a ticker.

    `daily price ÷ rolling-4Q TTM EPS`, with TTM EPS held constant between
    quarterly report dates (step function). The series only starts once
    four quarters of EPS history are available, and any date where the
    rolling TTM EPS is ≤ 0 (loss years) is dropped — negative P/E values
    aren't meaningful to plot. Returns None if FMP data is missing.
    """
    eps_df = fetch_quarterly_eps(ticker)
    if eps_df is None or len(eps_df) < 4:
        return None
    ttm = eps_df["eps"].rolling(4).sum().dropna()
    if ttm.empty:
        return None
    price = fetch_history(ticker, period)
    if price is None or price.empty:
        return None
    # For each price date, use the most recent reported TTM EPS at-or-before
    # that date (step function across earnings-release dates).
    ttm_aligned = ttm.reindex(price.index.union(ttm.index)).sort_index().ffill().reindex(price.index)
    valid = ttm_aligned.notna() & (ttm_aligned > 0)
    if not valid.any():
        return None
    pe = price[valid] / ttm_aligned[valid]
    return pe if not pe.empty else None
