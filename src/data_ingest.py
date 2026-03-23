"""
data_ingest.py — Data ingestion layer.
Fetches raw price/level data from Yahoo Finance and FRED.
All network calls live here. Returns clean DataFrames.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf

from src.config import Asset, ASSETS, FRED_LOOKBACK_DAYS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Yahoo Finance
# ---------------------------------------------------------------------------

def fetch_yf_history(ticker: str, period: str = "ytd") -> Optional[pd.DataFrame]:
    """
    Pull OHLCV history from Yahoo Finance.
    Returns DataFrame with DatetimeIndex and 'Close' column, or None on failure.
    """
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="1y", auto_adjust=True)
        if df is None or df.empty:
            logger.warning(f"YF returned empty data for {ticker}")
            return None
        if "Close" not in df.columns:
            logger.warning(f"YF data for {ticker} missing 'Close' column")
            return None
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df[["Close"]].dropna()
    except Exception as e:
        logger.error(f"YF fetch failed for {ticker}: {e}")
        return None


def fetch_all_yf(assets: list[Asset] = ASSETS) -> dict[str, pd.DataFrame]:
    """Fetch Yahoo Finance data for all assets that have a ticker."""
    results = {}
    tickers = [a for a in assets if a.ticker]
    for asset in tickers:
        df = fetch_yf_history(asset.ticker)
        if df is not None:
            results[asset.name] = df
    return results

# ---------------------------------------------------------------------------
# FRED
# ---------------------------------------------------------------------------

def _get_fred_api_key() -> Optional[str]:
    """Read FRED API key from env var or Streamlit Cloud secrets."""
    key = os.environ.get("FRED_API_KEY")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("general", {}).get("FRED_API_KEY")
        except Exception:
            pass
    if not key:
        logger.warning("FRED_API_KEY not set — FRED data will be unavailable.")
    return key


def fetch_fred_series(series_id: str, api_key: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Pull a single FRED series via direct HTTP (no fredapi package needed).
    Returns DataFrame with DatetimeIndex and 'Close' column.
    """
    import requests

    if api_key is None:
        api_key = _get_fred_api_key()
    if api_key is None:
        return None
    try:
        end = datetime.today()
        start = end - timedelta(days=FRED_LOOKBACK_DAYS)
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "observation_start": start.strftime("%Y-%m-%d"),
            "observation_end": end.strftime("%Y-%m-%d"),
        }
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        observations = data.get("observations", [])
        if not observations:
            logger.warning(f"FRED returned no observations for {series_id}")
            return None

        # Parse into DataFrame — FRED returns value as string, "." means missing
        rows = []
        for obs in observations:
            val = obs.get("value", ".")
            if val == ".":
                continue
            rows.append({"date": obs["date"], "Close": float(val)})

        if not rows:
            logger.warning(f"FRED returned all-missing data for {series_id}")
            return None

        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        return df
    except Exception as e:
        logger.error(f"FRED fetch failed for {series_id}: {e}")
        return None


def fetch_all_fred(assets: list[Asset] = ASSETS) -> dict[str, pd.DataFrame]:
    """Fetch FRED data for all assets that have a fred_id."""
    api_key = _get_fred_api_key()
    results = {}
    fred_assets = [a for a in assets if a.fred_id]
    for asset in fred_assets:
        df = fetch_fred_series(asset.fred_id, api_key)
        if df is not None:
            results[asset.name] = df
    return results

# ---------------------------------------------------------------------------
# Unified fetch
# ---------------------------------------------------------------------------

def fetch_all_data(assets: list[Asset] = ASSETS) -> dict[str, pd.DataFrame]:
    """
    Master fetch: pulls from YF and FRED, merging where both exist.
    YF takes priority for assets available on both sources.
    Returns {asset_name: DataFrame} with 'Close' column.
    """
    yf_data = fetch_all_yf(assets)
    fred_data = fetch_all_fred(assets)

    combined = {}
    for asset in assets:
        # Prefer YF data; fall back to FRED
        if asset.name in yf_data:
            combined[asset.name] = yf_data[asset.name]
        elif asset.name in fred_data:
            combined[asset.name] = fred_data[asset.name]
        else:
            logger.warning(f"No data available for {asset.name}")

    logger.info(f"Fetched data for {len(combined)}/{len(assets)} assets")
    return combined
