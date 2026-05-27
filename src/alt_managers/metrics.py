"""metrics.py — Pure return / risk calculations on a price (Close) Series.

All functions accept a pandas Series indexed by datetime and return a float or
None. None means "not enough data" — never a fabricated value.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _clean(close: pd.Series | None) -> pd.Series | None:
    if close is None or len(close) == 0:
        return None
    s = close.dropna()
    if s.empty:
        return None
    if s.index.tz is not None:
        s = s.tz_localize(None)
    return s.sort_index()


def total_return(close: pd.Series | None) -> float | None:
    """Simple total return over the full series, in percent."""
    s = _clean(close)
    if s is None or len(s) < 2:
        return None
    first, last = float(s.iloc[0]), float(s.iloc[-1])
    if first == 0:
        return None
    return (last / first - 1) * 100


def _value_on_or_before(s: pd.Series, target: pd.Timestamp) -> float | None:
    mask = s.index <= target
    if not mask.any():
        return None
    return float(s[mask].iloc[-1])


def trailing_total_return(close: pd.Series | None, years: float) -> float | None:
    """Total (cumulative) return over the trailing `years`, in percent."""
    s = _clean(close)
    if s is None or len(s) < 2:
        return None
    target = s.index[-1] - pd.DateOffset(years=int(years)) if float(years).is_integer() \
        else s.index[-1] - pd.Timedelta(days=int(years * 365))
    base = _value_on_or_before(s, target)
    if base is None:
        # No point on/before target. If the series starts only a few days after
        # the target (Yahoo's "Ny" window can fall just short), use the first
        # value — the window is effectively covered. Otherwise history is genuinely
        # too short, so return None rather than overstate.
        if s.index[0] - target <= pd.Timedelta(days=10):
            base = float(s.iloc[0])
        else:
            return None
    last = float(s.iloc[-1])
    if base == 0:
        return None
    return (last / base - 1) * 100


def annualized_return(close: pd.Series | None, years: float) -> float | None:
    """CAGR over the trailing `years`, in percent. None if window not covered."""
    tot = trailing_total_return(close, years)
    if tot is None:
        return None
    growth = 1 + tot / 100
    if growth <= 0:
        return None
    return (growth ** (1 / years) - 1) * 100


def max_drawdown(close: pd.Series | None) -> float | None:
    """Maximum peak-to-trough drawdown over the series, in percent (negative)."""
    s = _clean(close)
    if s is None or len(s) < 2:
        return None
    running_max = s.cummax()
    drawdown = s / running_max - 1
    return float(drawdown.min()) * 100


def annualized_vol(close: pd.Series | None) -> float | None:
    """Annualized stdev of daily returns, in percent (assumes 252 trading days)."""
    s = _clean(close)
    if s is None or len(s) < 3:
        return None
    daily = s.pct_change().dropna()
    if daily.empty:
        return None
    return float(daily.std() * np.sqrt(252)) * 100


def rebase_to_100(close: pd.Series | None) -> pd.Series | None:
    """Rebase a Close series to 100 at its first value."""
    s = _clean(close)
    if s is None or len(s) < 1:
        return None
    first = float(s.iloc[0])
    if first == 0:
        return None
    return (s / first) * 100
