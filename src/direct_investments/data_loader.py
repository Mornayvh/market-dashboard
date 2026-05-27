"""
data_loader.py — Live data fetchers for Direct Investments.
Wraps yfinance + FRED + pytrends with Streamlit caching and graceful failure.
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
import streamlit as st
import yfinance as yf

from src.data_ingest import _get_fred_api_key, fetch_fred_series

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Yahoo Finance
# ---------------------------------------------------------------------------

@st.cache_data(ttl=900, show_spinner=False)  # 15 min
def fetch_history(ticker: str, period: str = "1y") -> Optional[pd.DataFrame]:
    """Fetch single-ticker history with auto-adjusted Close. Returns None on failure."""
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, auto_adjust=True)
        if df is None or df.empty or "Close" not in df.columns:
            return None
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df[["Close"]].dropna()
    except Exception as e:
        logger.warning(f"YF history failed for {ticker}: {e}")
        return None


@st.cache_data(ttl=900, show_spinner=False)
def fetch_quote(ticker: str) -> dict:
    """
    Fetch latest price, percentage changes, and market cap for a comp.
    Returns {} if all fetches fail.
    """
    out = {"ticker": ticker, "price": None, "chg_1d": None,
           "chg_1w": None, "chg_1m": None, "chg_ltm": None, "market_cap": None}

    hist = fetch_history(ticker, period="1y")
    if hist is not None and not hist.empty:
        close = hist["Close"]
        last = float(close.iloc[-1])
        out["price"] = last

        def _pct_since(days: int) -> Optional[float]:
            target = close.index[-1] - pd.Timedelta(days=days)
            mask = close.index <= target
            if mask.any():
                prev = float(close[mask].iloc[-1])
                if prev:
                    return (last / prev - 1) * 100
            return None

        out["chg_1d"] = _pct_since(1)
        out["chg_1w"] = _pct_since(7)
        out["chg_1m"] = _pct_since(30)

        # LTM: trailing ~12 months, anchored to the earliest close in the 1y window.
        ltm_base = float(close.iloc[0])
        if ltm_base:
            out["chg_ltm"] = (last / ltm_base - 1) * 100

    try:
        info = yf.Ticker(ticker).info or {}
        mc = info.get("marketCap")
        if mc:
            out["market_cap"] = float(mc)
    except Exception:
        pass

    return out


@st.cache_data(ttl=900, show_spinner=False)
def fetch_30d_avg_volume(ticker: str) -> Optional[float]:
    """Return 30-day average dollar volume (price * volume). Used for ETF liquidity ranking."""
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="3mo", auto_adjust=True)
        if df is None or df.empty:
            return None
        recent = df.tail(30)
        if recent.empty or "Volume" not in recent.columns:
            return None
        return float((recent["Close"] * recent["Volume"]).mean())
    except Exception as e:
        logger.warning(f"Volume fetch failed for {ticker}: {e}")
        return None


def pick_most_liquid(candidates: list[str]) -> tuple[str, dict[str, Optional[float]]]:
    """
    Return (chosen_ticker, all_volumes) — the ETF with the highest 30-day avg dollar
    volume from the candidate list. Falls back to candidates[0] if all fetches fail.
    """
    volumes = {tk: fetch_30d_avg_volume(tk) for tk in candidates}
    ranked = [tk for tk, v in volumes.items() if v is not None]
    if not ranked:
        return candidates[0], volumes
    chosen = max(ranked, key=lambda tk: volumes[tk] or 0)
    return chosen, volumes


# ---------------------------------------------------------------------------
# FRED
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)  # 1 hour
def fetch_fred(series_id: str) -> Optional[pd.DataFrame]:
    """Wrapped fetch with Streamlit caching."""
    api_key = _get_fred_api_key()
    if not api_key:
        return None
    return fetch_fred_series(series_id, api_key)


# ---------------------------------------------------------------------------
# Google Trends (pytrends) — optional dependency, graceful fallback
# ---------------------------------------------------------------------------

@st.cache_data(ttl=21600, show_spinner=False)  # 6 hours
def fetch_trends(keywords: tuple, geo: str = "US", timeframe: str = "today 12-m") -> Optional[pd.DataFrame]:
    """
    Pull Google Trends interest-over-time. Returns DataFrame with one column per
    keyword, or None if pytrends is missing / rate-limited / fails.
    """
    try:
        from pytrends.request import TrendReq
    except ImportError:
        logger.info("pytrends not installed — Trends section will be unavailable.")
        return None

    try:
        py = TrendReq(hl="en-US", tz=360, timeout=(5, 15))
        py.build_payload(list(keywords), geo=geo, timeframe=timeframe)
        df = py.interest_over_time()
        if df is None or df.empty:
            return None
        if "isPartial" in df.columns:
            df = df.drop(columns=["isPartial"])
        return df
    except Exception as e:
        logger.warning(f"Google Trends fetch failed for {keywords}: {e}")
        return None


# ---------------------------------------------------------------------------
# LTM-rebased multi-line comp chart helper (pure data prep)
# ---------------------------------------------------------------------------

def rebased_history(tickers: list[str], period: str = "1y") -> pd.DataFrame:
    """
    Return a DataFrame of rebased-to-100 closes for the given tickers.
    Missing tickers are silently skipped.
    """
    series = {}
    for tk in tickers:
        df = fetch_history(tk, period=period)
        if df is None or df.empty:
            continue
        s = df["Close"]
        first = float(s.iloc[0])
        if first == 0:
            continue
        series[tk] = (s / first) * 100.0
    if not series:
        return pd.DataFrame()
    # No ffill — if a comp stops trading (e.g., taken private), the line should
    # truncate at the last real close rather than plateau forward.
    return pd.DataFrame(series).sort_index()
