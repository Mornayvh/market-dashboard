"""data.py — yfinance fetchers, caching, and FX normalization.

Every network call is wrapped in try/except. Missing fields return None and are
recorded in the per-ticker `_failed_fields` list so the UI can surface them.
yfinance is unofficial; fields disappear without warning.
"""

from __future__ import annotations

import logging

import pandas as pd
import streamlit as st
import yfinance as yf

from src.alt_managers import metrics

logger = logging.getLogger(__name__)

# Scalar fields pulled from yf.Ticker(...).info
INFO_FIELDS = [
    "longName", "sector", "industry", "country", "currency",
    "marketCap", "enterpriseValue", "sharesOutstanding",
    "trailingPE", "forwardPE", "priceToBook", "priceToSalesTrailing12Months", "enterpriseToEbitda",
    "dividendYield", "payoutRatio", "fiveYearAvgDividendYield",
    "beta", "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "currentPrice", "previousClose",
    "totalRevenue", "ebitda", "profitMargins", "operatingMargins", "returnOnEquity", "debtToEquity",
    "targetMeanPrice", "recommendationMean", "numberOfAnalystOpinions", "recommendationKey",
    "heldPercentInsiders", "heldPercentInstitutions",
    "longBusinessSummary",
]

# FX pairs — value is USD per 1 unit of the foreign currency.
FX_PAIRS = {"EUR": "EURUSD=X", "GBP": "GBPUSD=X", "CHF": "CHFUSD=X", "SEK": "SEKUSD=X"}

PERIOD_MAP = {"1M": "1mo", "6M": "6mo", "YTD": "ytd", "1Y": "1y", "3Y": "3y", "5Y": "5y"}


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
        result.update({"ret_ytd": None, "ret_1y": None, "ret_3y": None, "ret_5y": None})
    else:
        result["ret_ytd"] = metrics.ytd_return(close)
        result["ret_1y"] = metrics.trailing_total_return(close, 1)
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
