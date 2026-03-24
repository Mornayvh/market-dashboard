"""
data_process.py — Data processing layer.
Computes dashboard metrics (latest value, daily/weekly/LTM changes)
from raw price history. Pure functions — no side effects.
"""

import logging
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from src.config import Asset, ASSETS, ASSETS_BY_CATEGORY, CATEGORIES, EQUITY_PE_MAP

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Metric computation for a single asset
# ---------------------------------------------------------------------------

def _pct_change(current: float, previous: float) -> float | None:
    """Percentage change from previous to current. Returns None if invalid."""
    if previous is None or previous == 0 or current is None:
        return None
    return ((current - previous) / abs(previous)) * 100


def _abs_change(current: float, previous: float) -> float | None:
    """Absolute change (for rates/spreads). Returns None if invalid."""
    if previous is None or current is None:
        return None
    return current - previous


def _get_value_at(df: pd.DataFrame, target_date: pd.Timestamp) -> float | None:
    """
    Get the 'Close' value at or just before target_date.
    Handles weekends/holidays by looking back up to 5 days.
    """
    if df is None or df.empty:
        return None
    mask = df.index <= target_date
    subset = df.loc[mask]
    if subset.empty:
        return None
    return float(subset["Close"].iloc[-1])


def compute_metrics(asset: Asset, df: pd.DataFrame) -> dict:
    """
    Compute all dashboard metrics for a single asset.
    Uses Last Twelve Months (LTM) instead of YTD.
    """
    today = pd.Timestamp(datetime.today().date())
    one_day_ago = today - timedelta(days=1)
    one_week_ago = today - timedelta(days=7)
    # LTM: 12 months ago
    ltm_start = today - timedelta(days=365)

    latest = _get_value_at(df, today)
    prev_day = _get_value_at(df, one_day_ago)
    prev_week = _get_value_at(df, one_week_ago)
    ltm_base = _get_value_at(df, ltm_start)

    # For rates and spreads, show absolute change (in bps or %)
    if asset.is_rate or asset.is_spread:
        multiplier = 100 if asset.is_spread else 1
        daily_chg = _abs_change(latest, prev_day)
        weekly_chg = _abs_change(latest, prev_week)
        ltm_chg = _abs_change(latest, ltm_base)
        if asset.is_spread and daily_chg is not None:
            daily_chg *= multiplier
        if asset.is_spread and weekly_chg is not None:
            weekly_chg *= multiplier
        if asset.is_spread and ltm_chg is not None:
            ltm_chg *= multiplier
    else:
        daily_chg = _pct_change(latest, prev_day)
        weekly_chg = _pct_change(latest, prev_week)
        ltm_chg = _pct_change(latest, ltm_base)

    return {
        "name": asset.name,
        "category": asset.category,
        "latest": latest,
        "daily_chg": daily_chg,
        "weekly_chg": weekly_chg,
        "ltm_chg": ltm_chg,
        "is_rate": asset.is_rate,
        "is_spread": asset.is_spread,
        "invert_color": asset.invert_color,
    }

# ---------------------------------------------------------------------------
# VIX average (1-year rolling mean)
# ---------------------------------------------------------------------------

def compute_vix_average(data: dict[str, pd.DataFrame]) -> float | None:
    """Compute the 1-year average VIX from historical data."""
    df = data.get("VIX")
    if df is None or df.empty:
        return None
    one_year_ago = pd.Timestamp(datetime.today().date()) - timedelta(days=365)
    recent = df[df.index >= one_year_ago]
    if recent.empty:
        return None
    return float(recent["Close"].mean())

# ---------------------------------------------------------------------------
# Equity P/E multiples via ETF proxies
# ---------------------------------------------------------------------------

def fetch_equity_pe() -> dict[str, float | None]:
    """
    Fetch trailing P/E ratios for equity indices using ETF proxies.
    Returns {asset_name: trailing_pe}.
    """
    result = {}
    for name, etf_ticker in EQUITY_PE_MAP.items():
        try:
            t = yf.Ticker(etf_ticker)
            info = t.info or {}
            pe = info.get("trailingPE") or info.get("forwardPE")
            result[name] = round(pe, 1) if pe else None
        except Exception as e:
            logger.warning(f"Failed to fetch P/E for {name} ({etf_ticker}): {e}")
            result[name] = None
    return result

# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

def process_all(
    data: dict[str, pd.DataFrame],
    assets: list[Asset] = ASSETS,
) -> pd.DataFrame:
    """
    Compute metrics for all assets. Returns a DataFrame indexed by asset name.
    """
    rows = []
    for asset in assets:
        df = data.get(asset.name)
        if df is not None and not df.empty:
            rows.append(compute_metrics(asset, df))
        else:
            rows.append({
                "name": asset.name,
                "category": asset.category,
                "latest": None,
                "daily_chg": None,
                "weekly_chg": None,
                "ltm_chg": None,
                "is_rate": asset.is_rate,
                "is_spread": asset.is_spread,
                "invert_color": asset.invert_color,
            })

    result = pd.DataFrame(rows).set_index("name")
    return result


def get_category_df(metrics_df: pd.DataFrame, category: str) -> pd.DataFrame:
    """Filter metrics to a single category."""
    return metrics_df[metrics_df["category"] == category]
