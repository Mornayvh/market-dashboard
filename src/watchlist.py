"""
watchlist.py — The stock watchlist universe.

Single source of truth for the tracked holdings, shared by the Streamlit page
(pages/3_Stock_Watchlist.py) and the PDF exporter (export_watchlist_pdf.py).
Both used to carry their own copy of this dict; add or remove names here only.

Entries are (display name, Yahoo Finance ticker, listing currency). Group order
is the display order on both surfaces, and the order within a group is the row
order, so keep each group alphabetical unless there is a reason not to.
"""

WATCHLIST: dict[str, list[tuple[str, str, str]]] = {
    "Core Holdings": [
        ("Richemont", "CFR.SW", "CHF"),
        ("Remgro", "REM.JO", "ZAR"),
        ("Reinet", "REINA.AS", "EUR"),
    ],
    "Connected Holdings": [
        ("BAT (LSE)", "BATS.L", "GBP"),
        ("BAT (JSE)", "BTI.JO", "ZAR"),
        ("FirstRand", "FSR.JO", "ZAR"),
        ("OUTsurance", "OUT.JO", "ZAR"),
        ("Discovery", "DSY.JO", "ZAR"),
    ],
    "Tiger Global IPO's": [
        ("Cerebras", "CBRS", "USD"),
    ],
    "USA Tech": [
        ("Alphabet", "GOOGL", "USD"),
        ("Amazon", "AMZN", "USD"),
        ("Apple", "AAPL", "USD"),
        ("Dell", "DELL", "USD"),
        ("Meta", "META", "USD"),
        ("Microsoft", "MSFT", "USD"),
        ("Nvidia", "NVDA", "USD"),
        ("SpaceX", "SPCX", "USD"),
        ("Tesla", "TSLA", "USD"),
        ("Palo Alto", "PANW", "USD"),
        ("Uber", "UBER", "USD"),
    ],
    "China Tech": [
        ("Alibaba", "BABA", "USD"),
        ("BYD", "002594.SZ", "CNY"),
        ("CXMT", "688825.SS", "CNY"),
        ("Tencent", "TCEHY", "USD"),
        ("Unitree", "688836.SS", "CNY"),
    ],
    "Financials": [
        ("JP Morgan", "JPM", "USD"),
        ("Goldman Sachs", "GS", "USD"),
        ("BofA", "BAC", "USD"),
        ("Morgan Stanley", "MS", "USD"),
        ("Berkshire Hathaway", "BRK-B", "USD"),
        ("Markel", "MKL", "USD"),
        ("Apollo", "APO", "USD"),
        ("KKR", "KKR", "USD"),
    ],
    "Real World": [
        ("Deere & Co", "DE", "USD"),
        ("Teledyne", "TDY", "USD"),
        ("Waste Management", "WM", "USD"),
    ],
}

CURRENCY_SYMBOLS = {"USD": "$", "GBP": "£", "EUR": "€", "CHF": "CHF ", "ZAR": "R", "CNY": "¥"}

# Calendar-day span a 1y fetch must cover before LTM and 52-week figures are
# reported. Below this the series is a recent listing, not a year of trading.
# 300 rather than 365 so exchange holidays and short weeks don't trip it.
FULL_YEAR_MIN_DAYS = 300


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------
# One ticker per request gets the caller rate-limited by Yahoo once the list is
# this long — reliably so from a datacentre IP, which is why it showed up in
# GitHub Actions and never locally. Everything below exists to keep the request
# count near one.

import logging
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def _metrics_from_close(close: "pd.Series"):
    """(price, chg_1d, chg_1m, chg_ltm, high_52w, low_52w) from a close series."""
    if close is None or close.empty:
        return (None,) * 6

    last = float(close.iloc[-1])
    chg_1d = (last / float(close.iloc[-2]) - 1) * 100 if len(close) >= 2 else None

    chg_1m = None
    month_data = close[close.index <= datetime.now() - timedelta(days=30)]
    if not month_data.empty:
        chg_1m = (last / float(month_data.iloc[-1]) - 1) * 100

    # LTM and 52-week figures need roughly a year of history; a recent listing
    # would otherwise report its first days as a 12-month move.
    span_days = (close.index[-1] - close.index[0]).days if len(close) >= 2 else 0
    has_full_year = span_days >= FULL_YEAR_MIN_DAYS

    chg_ltm = (last / float(close.iloc[0]) - 1) * 100 if len(close) >= 2 and has_full_year else None
    hi = float(close.max()) if has_full_year else None
    lo = float(close.min()) if has_full_year else None

    return last, chg_1d, chg_1m, chg_ltm, hi, lo


def _close_series(frame) -> "pd.Series | None":
    """Pull a clean, tz-naive Close series out of a yfinance frame."""
    if frame is None or getattr(frame, "empty", True) or "Close" not in frame:
        return None
    close = frame["Close"].dropna()
    if close.empty:
        return None
    close.index = pd.to_datetime(close.index).tz_localize(None)
    return close


def fetch_watchlist(tickers: list[str]) -> dict[str, tuple]:
    """Metrics for every ticker, as one batch request plus retries.

    yf.download takes the whole list in a single call. Anything it returns
    empty for is retried individually, which covers the occasional delisting
    or bad symbol without putting the request count back where it started.
    """
    frames = {}
    try:
        raw = yf.download(
            tickers, period="1y", auto_adjust=True, group_by="ticker",
            threads=False, progress=False,
        )
        if raw is not None and not raw.empty:
            for t in tickers:
                try:
                    frames[t] = raw[t] if len(tickers) > 1 else raw
                except (KeyError, IndexError):
                    frames[t] = None
    except Exception as exc:
        logger.warning("Batch download failed (%s); falling back per ticker.", exc)

    results, retried = {}, []
    for t in tickers:
        close = _close_series(frames.get(t))
        if close is None:
            retried.append(t)
            try:
                close = _close_series(yf.Ticker(t).history(period="1y", auto_adjust=True))
            except Exception as exc:
                logger.warning("Fetch failed for %s: %s", t, exc)
                close = None
        results[t] = _metrics_from_close(close)

    if retried:
        logger.info("Retried %d ticker(s) individually: %s", len(retried), ", ".join(retried))
    missing = [t for t, m in results.items() if m[0] is None]
    if missing:
        logger.warning("No price for %d ticker(s): %s", len(missing), ", ".join(missing))
    return results
