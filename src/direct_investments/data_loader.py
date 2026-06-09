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
# Fund / ETF top holdings (used to show index constituents via a tracking ETF)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=86400, show_spinner=False)  # 24 h — holdings change slowly
def fetch_top_holdings(ticker: str) -> list[tuple[str, str, float]]:
    """
    Top-10 holdings of a fund/ETF as [(symbol, name, weight_pct), ...].
    Only works for funds (indices have no holdings feed). Returns [] on failure.
    """
    try:
        th = yf.Ticker(ticker).funds_data.top_holdings
        if th is None or th.empty:
            return []
        out: list[tuple[str, str, float]] = []
        for sym, row in th.head(10).iterrows():
            name = str(row.get("Name", "") or "")
            try:
                weight = float(row.get("Holding Percent")) * 100
            except (TypeError, ValueError):
                continue
            out.append((str(sym), name, weight))
        return out
    except Exception as e:
        logger.warning(f"Top-holdings fetch failed for {ticker}: {e}")
        return []


# ---------------------------------------------------------------------------
# SEC EDGAR — annual advertising expense (actual marketing spend, US filers)
# ---------------------------------------------------------------------------

import requests
from datetime import date as _date
from src.config import (
    get_sec_user_agent, SEC_TICKER_MAP_URL, SEC_COMPANYCONCEPT_URL,
)

# SEC requires a descriptive User-Agent; fall back to a contact string if unset.
_DEFAULT_SEC_UA = "Secco Capital Dashboard mornay@seccocapital.com"


def _sec_headers() -> dict:
    return {"User-Agent": get_sec_user_agent() or _DEFAULT_SEC_UA,
            "Accept-Encoding": "gzip, deflate"}


@st.cache_data(ttl=86400, show_spinner=False)  # 24 h — ticker->CIK map is stable
def _sec_ticker_to_cik() -> dict[str, str]:
    """Map upper-case ticker -> zero-padded CIK from SEC's company_tickers.json."""
    try:
        r = requests.get(SEC_TICKER_MAP_URL, headers=_sec_headers(), timeout=30)
        r.raise_for_status()
        return {row["ticker"].upper(): f'{row["cik_str"]:010d}' for row in r.json().values()}
    except Exception as e:
        logger.warning(f"SEC ticker map fetch failed: {e}")
        return {}


@st.cache_data(ttl=86400, show_spinner=False)  # 24 h — annual data, refreshed at most daily
def fetch_advertising_usd(ticker: str) -> dict[int, float]:
    """
    Annual advertising expense (us-gaap:AdvertisingExpense) per fiscal year, in USD,
    pulled from SEC EDGAR's companyconcept endpoint. Keys are the period-end fiscal
    year. Returns {} if the company doesn't file/disclose it (e.g. foreign IFRS filers).
    """
    cik = _sec_ticker_to_cik().get(ticker.upper())
    if not cik:
        return {}
    try:
        url = SEC_COMPANYCONCEPT_URL.format(cik=cik, tag="AdvertisingExpense")
        r = requests.get(url, headers=_sec_headers(), timeout=30)
        if r.status_code != 200:
            return {}
        usd = r.json().get("units", {}).get("USD", [])
    except Exception as e:
        logger.warning(f"EDGAR advertising fetch failed for {ticker}: {e}")
        return {}

    # Keep only annual 10-K facts, aligned to the filing's own fiscal year (period-end
    # year == fy filters out the prior-year comparatives carried in each filing); the
    # latest-filed value wins per year so restatements supersede.
    by_fy: dict[int, dict] = {}
    for it in usd:
        if it.get("form") not in ("10-K", "10-K/A") or it.get("fp") != "FY":
            continue
        start, end, fy = it.get("start"), it.get("end"), it.get("fy")
        if not start or not end or fy is None or int(end[:4]) != fy:
            continue
        try:
            days = (_date.fromisoformat(end) - _date.fromisoformat(start)).days
        except ValueError:
            continue
        if not 330 <= days <= 400:
            continue
        prev = by_fy.get(fy)
        if prev is None or it.get("filed", "") > prev.get("filed", ""):
            by_fy[fy] = it
    return {fy: float(it["val"]) for fy, it in by_fy.items() if it.get("val") is not None}


# ---------------------------------------------------------------------------
# SEC EDGAR — quarterly capex by calendar quarter (cash-flow YTD differencing)
# ---------------------------------------------------------------------------

# Filers tag capex differently (Amazon uses ProductiveAssets, others PP&E); try in order.
_CAPEX_TAGS = ("PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets")


def _calendar_quarter(end_iso: str) -> str:
    """Map a period-end date to a calendar quarter label, e.g. '2025-09-30' -> '2025Q3'."""
    return f"{int(end_iso[:4])}Q{(int(end_iso[5:7]) - 1)//3 + 1}"


def _derive_quarterly_capex(usd_facts: list) -> dict[str, float]:
    """
    Cash-flow capex is reported year-to-date in 10-Qs, so derive standalone quarters by
    differencing the YTD chain within each fiscal year. The fiscal-year start is anchored
    on the 10-K boundary (period-end year == fy) so prior-year comparatives are excluded;
    YTD facts are those sharing that start date. Q = YTD(this) - YTD(prev); each maps to a
    calendar quarter by its period-end. Latest-filed fact wins per period.
    """
    fy_start, annual = {}, {}
    for it in usd_facts:
        s, e, fy, v, f = it.get("start"), it.get("end"), it.get("fy"), it.get("val"), it.get("filed", "")
        if not (s and e and v is not None and fy is not None):
            continue
        try:
            d = (_date.fromisoformat(e) - _date.fromisoformat(s)).days
        except ValueError:
            continue
        if it.get("form", "").startswith("10-K") and 330 <= d <= 400 and int(e[:4]) == fy:
            if fy not in annual or f > annual[fy][1]:
                annual[fy] = (float(v), f)
                fy_start[fy] = s
    out: dict[str, float] = {}
    for fy, fstart in fy_start.items():
        pts: dict[str, tuple] = {}
        for it in usd_facts:
            s, e, v, f = it.get("start"), it.get("end"), it.get("val"), it.get("filed", "")
            if s != fstart or not e or v is None:
                continue
            if e not in pts or f > pts[e][1]:
                pts[e] = (float(v), f)
        prev = 0.0
        for end, (v, _) in sorted(pts.items()):
            out[_calendar_quarter(end)] = v - prev
            prev = v
    return out


@st.cache_data(ttl=86400, show_spinner=False)  # 24 h
def fetch_quarterly_capex(ticker: str) -> dict[str, float]:
    """
    Standalone quarterly capex (USD) keyed by calendar quarter, derived from SEC EDGAR
    cash-flow filings. Picks the capex tag with the most recent coverage. Returns {} for
    non-US filers (e.g. foreign 20-F issuers don't file 10-Qs).
    """
    cik = _sec_ticker_to_cik().get(ticker.upper())
    if not cik:
        return {}
    best: dict[str, float] = {}
    _recent = lambda d: sum(1 for q in d if int(q[:4]) >= 2022)
    for tag in _CAPEX_TAGS:
        try:
            r = requests.get(SEC_COMPANYCONCEPT_URL.format(cik=cik, tag=tag), headers=_sec_headers(), timeout=30)
            if r.status_code != 200:
                continue
            usd = r.json().get("units", {}).get("USD", [])
        except Exception as e:
            logger.warning(f"EDGAR capex fetch failed for {ticker}/{tag}: {e}")
            continue
        series = _derive_quarterly_capex(usd)
        if _recent(series) > _recent(best):
            best = series
    return best


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
