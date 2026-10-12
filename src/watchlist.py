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


def fetch_closes(tickers: list[str], period: str = "1y") -> dict[str, "pd.Series | None"]:
    """Close history for every ticker, as one batch request plus retries.

    yf.download takes the whole list in a single call. Anything it returns
    empty for is retried individually, which covers the occasional delisting
    or bad symbol without putting the request count back where it started.
    """
    frames = {}
    try:
        raw = yf.download(
            tickers, period=period, auto_adjust=True, group_by="ticker",
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

    closes, retried = {}, []
    for t in tickers:
        close = _close_series(frames.get(t))
        if close is None:
            retried.append(t)
            try:
                close = _close_series(yf.Ticker(t).history(period=period, auto_adjust=True))
            except Exception as exc:
                logger.warning("Fetch failed for %s: %s", t, exc)
                close = None
        closes[t] = close

    if retried:
        logger.info("Retried %d ticker(s) individually: %s", len(retried), ", ".join(retried))
    missing = [t for t, c in closes.items() if c is None]
    if missing:
        logger.warning("No history for %d ticker(s): %s", len(missing), ", ".join(missing))
    return closes


def fetch_watchlist(
    tickers: list[str], period: str = "1y",
) -> tuple[dict[str, tuple], dict[str, "pd.Series | None"]]:
    """Metrics and close history for every ticker.

    Returns (metrics, closes). The close series are kept rather than discarded
    after the metrics are computed, because the HTML brief charts them.

    `period` lengthens the history returned without disturbing the numbers:
    the metrics are always computed on the trailing year, so asking for "max"
    gives a decade of chart data and the same 1D/1M/LTM figures as before.
    """
    closes = fetch_closes(tickers, period)

    results = {}
    for t, close in closes.items():
        window = close
        if close is not None and len(close):
            window = close[close.index >= close.index[-1] - pd.Timedelta(days=365)]
        results[t] = _metrics_from_close(window)

    missing = [t for t, m in results.items() if m[0] is None]
    if missing:
        logger.warning("No price for %d ticker(s): %s", len(missing), ", ".join(missing))
    return results, closes


# Yahoo's earnings history for non-US listings can return records many years
# old instead of nothing — FirstRand came back with August 2007 and a 3,365%
# surprise. Any issuer reports at least annually, so a "most recent report"
# beyond this is a gap in the data, not a fact about the company.
MAX_EARNINGS_AGE_DAYS = 400

# Longer than any normal quarterly or semi-annual cycle plus reporting lag,
# so this flags a genuine gap rather than every semi-annual reporter.
EARNINGS_STALE_DAYS = 200


def _usable_surprise(eps: float, est, surp) -> bool:
    """Whether an estimate and surprise are worth showing beside the actual.

    Yahoo's estimate is not always on the same basis as the reported figure,
    which produces nonsense: Amazon and Alphabet both came back near +215%,
    Alibaba at -89%. A surprise of that size is a basis mismatch, not a result.
    Estimates at or below zero are excluded too — "beating" a forecast loss is
    arithmetically true and tells a reader nothing.
    """
    if est is None or surp is None or est <= 0.25:
        return False
    if abs(surp) > 100:
        return False
    ratio = eps / est
    return 0.25 <= ratio <= 4


def fetch_earnings(tickers: list[str]) -> dict[str, dict]:
    """Most recent reported quarter and next expected date, per ticker.

    Pulled fresh on every build, so the brief reflects whatever a company has
    most recently reported without anyone editing a file. Rows carrying a
    reported EPS are history; rows without one are scheduled.

    One request per ticker, unlike the batched price fetch — there is no bulk
    endpoint for this. A ticker that fails or has no history is simply absent
    from the result; earnings are an addition to the brief, never a reason to
    fail the build.
    """
    out, failed, stale, unusable = {}, [], [], []
    today = pd.Timestamp.today().normalize()

    for t in tickers:
        try:
            df = yf.Ticker(t).get_earnings_dates(limit=16)
        except Exception as exc:
            failed.append(t)
            logger.debug("Earnings fetch failed for %s: %s", t, exc)
            continue
        if df is None or df.empty or "Reported EPS" not in df:
            continue

        df = df.copy()
        df.index = pd.to_datetime(df.index).tz_localize(None)

        reported = df[df["Reported EPS"].notna()].sort_index()
        upcoming = df[df["Reported EPS"].isna() & (df.index >= today)].sort_index()

        entry = {}
        if not reported.empty:
            row = reported.iloc[-1]
            when = reported.index[-1]
            age = int((today - when.normalize()).days)
            if age > MAX_EARNINGS_AGE_DAYS:
                stale.append(f"{t} ({when:%Y-%m-%d})")
            else:
                entry["on"] = when.strftime("%d %B %Y")
                entry["age"] = age
                eps = round(float(row["Reported EPS"]), 2)
                entry["eps"] = eps
                est = round(float(row["EPS Estimate"]), 2) if pd.notna(row.get("EPS Estimate")) else None
                surp = round(float(row["Surprise(%)"]), 1) if pd.notna(row.get("Surprise(%)")) else None
                if _usable_surprise(eps, est, surp):
                    entry["est"], entry["surp"] = est, surp
                elif est is not None:
                    unusable.append(t)
        if not upcoming.empty:
            entry["next"] = upcoming.index[0].strftime("%d %B %Y")

        if entry:
            out[t] = entry

    if failed:
        logger.warning("Earnings fetch failed for %d ticker(s): %s",
                       len(failed), ", ".join(failed))
    if stale:
        logger.warning("Discarded earnings older than %d days for: %s",
                       MAX_EARNINGS_AGE_DAYS, ", ".join(stale))
    if unusable:
        logger.info("Estimate not on a comparable basis, showing actual only: %s",
                    ", ".join(unusable))
    logger.info("Earnings data for %d/%d tickers", len(out), len(tickers))
    return out
