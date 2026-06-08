"""
fundamentals_process.py
Orchestration + processing layer. Mirrors data_process.py.

  refresh_all()  : pull from EDGAR for all configured tickers and write to DB.
                   Call this from the dashboard's refresh button or a cron job.
  load_frame()   : read from DB into a tidy pandas DataFrame for charts.
  pivot_metric() : wide table (year x ticker) for one metric, scaled for display.
"""

import pandas as pd

from src.config import (
    FUNDAMENTALS_TICKERS as TICKERS,
    FUNDAMENTALS_METRICS as METRICS,
)
from src.fundamentals_ingest import SecClient, fetch_company_rows
from src import fundamentals_db as db


def refresh_all(tickers=None, user_agent=None):
    """Fetch fresh data for `tickers` (default: configured TICKERS) and store it.

    Returns a dict summary {ticker: coverage, ...} plus totals.
    """
    tickers = tickers or TICKERS
    engine = db.init_db()
    client = SecClient(user_agent) if user_agent else SecClient()

    summary = {}
    total_rows = 0
    try:
        cik_map = client.resolve_ciks(tickers)
        for ticker in tickers:
            info = cik_map.get(ticker.upper())
            if not info:
                summary[ticker] = {"error": "ticker not found in SEC map"}
                continue
            cik, name = info["cik"], info["name"]
            db.upsert_company(engine, cik, ticker.upper(), name)
            rows, coverage = fetch_company_rows(client, cik, ticker.upper())
            db.replace_fundamentals(engine, cik, ticker.upper(), rows)
            summary[ticker] = coverage
            total_rows += len(rows)
        db.log_refresh(engine, tickers, total_rows, "success")
    except Exception as exc:  # noqa: BLE001 — surface any failure to the log
        db.log_refresh(engine, tickers, total_rows, "error", str(exc))
        raise
    return {"per_ticker": summary, "total_rows": total_rows}


def load_frame(tickers=None, metrics=None):
    """Tidy long DataFrame with a display-scaled `value_scaled` column."""
    engine = db.init_db()
    rows = db.read_fundamentals(engine, tickers=tickers, metrics=metrics)
    if not rows:
        return pd.DataFrame(columns=[
            "ticker", "metric", "fiscal_year", "value", "value_scaled",
            "period_end", "unit", "xbrl_tag", "source_accn",
        ])
    df = pd.DataFrame(rows)
    scales = {k: v["scale"] for k, v in METRICS.items()}
    df["value_scaled"] = df.apply(
        lambda r: (r["value"] / scales.get(r["metric"], 1.0))
        if pd.notna(r["value"]) else None, axis=1)
    df["metric_name"] = df["metric"].map(
        {k: v["name"] for k, v in METRICS.items()})
    return df


def pivot_metric(df, metric_key):
    """Wide table: rows = fiscal_year, columns = ticker, values = scaled value."""
    sub = df[df["metric"] == metric_key]
    if sub.empty:
        return pd.DataFrame()
    return sub.pivot_table(index="fiscal_year", columns="ticker",
                           values="value_scaled", aggfunc="last").sort_index()


def get_last_refresh():
    engine = db.init_db()
    return db.last_refresh(engine)
