"""
fundamentals_db.py
Database layer (schema + read/write helpers) for SEC fundamentals.

Uses SQLAlchemy Core so the same code works on SQLite now and Postgres later
by changing only FUNDAMENTALS_DB_URL in src/config.py.

Schema (3 tables):
  companies        — one row per tracked company (ticker, cik, name)
  fundamentals     — one row per (company, metric, fiscal_year): the value
                     plus provenance (source filing, period end, xbrl tag)
  refresh_log      — one row per refresh run, with timestamp and status
"""

from datetime import datetime, timezone

from sqlalchemy import (
    create_engine, MetaData, Table, Column, Integer, String, Float,
    DateTime, UniqueConstraint, select, delete,
)

from src.config import FUNDAMENTALS_DB_URL as DB_URL, FUNDAMENTALS_DB_PATH as DB_PATH

metadata = MetaData()

companies = Table(
    "companies", metadata,
    Column("cik", String, primary_key=True),
    Column("ticker", String, nullable=False, index=True),
    Column("name", String),
    Column("updated_at", DateTime),
)

fundamentals = Table(
    "fundamentals", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("cik", String, nullable=False, index=True),
    Column("ticker", String, nullable=False, index=True),
    Column("metric", String, nullable=False),       # key from FUNDAMENTALS_METRICS
    Column("fiscal_year", Integer, nullable=False),  # the filing's own FY
    Column("period_end", String),                    # e.g. 2024-01-28
    Column("value", Float),                           # raw value (not scaled)
    Column("unit", String),
    Column("xbrl_tag", String),                       # which tag supplied it
    Column("source_accn", String),                   # SEC accession number
    Column("filed", String),
    Column("fetched_at", DateTime),
    UniqueConstraint("cik", "metric", "fiscal_year", name="uq_company_metric_year"),
)

refresh_log = Table(
    "refresh_log", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("run_at", DateTime),
    Column("tickers", String),
    Column("rows_written", Integer),
    Column("status", String),
    Column("message", String),
)


def get_engine():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(DB_URL, future=True)


def init_db(engine=None):
    engine = engine or get_engine()
    metadata.create_all(engine)
    return engine


def upsert_company(engine, cik, ticker, name):
    now = datetime.now(timezone.utc)
    with engine.begin() as conn:
        existing = conn.execute(
            select(companies.c.cik).where(companies.c.cik == cik)
        ).first()
        if existing:
            conn.execute(companies.update().where(companies.c.cik == cik)
                         .values(ticker=ticker, name=name, updated_at=now))
        else:
            conn.execute(companies.insert().values(
                cik=cik, ticker=ticker, name=name, updated_at=now))


def replace_fundamentals(engine, cik, ticker, rows):
    """Replace all fundamentals rows for a company with a fresh set.

    `rows` is a list of dicts with keys matching the fundamentals columns
    (minus id). Using replace keeps the table clean across re-fetches.
    """
    now = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(delete(fundamentals).where(fundamentals.c.cik == cik))
        if rows:
            for r in rows:
                r.setdefault("fetched_at", now)
            conn.execute(fundamentals.insert(), rows)


def log_refresh(engine, tickers, rows_written, status, message=""):
    with engine.begin() as conn:
        conn.execute(refresh_log.insert().values(
            run_at=datetime.now(timezone.utc),
            tickers=",".join(tickers),
            rows_written=rows_written,
            status=status,
            message=message[:500],
        ))


def last_refresh(engine):
    with engine.begin() as conn:
        row = conn.execute(
            select(refresh_log).order_by(refresh_log.c.run_at.desc()).limit(1)
        ).first()
    return dict(row._mapping) if row else None


def read_fundamentals(engine, tickers=None, metrics=None):
    """Return all fundamentals rows as a list of dicts, optionally filtered."""
    q = select(fundamentals)
    if tickers:
        q = q.where(fundamentals.c.ticker.in_(tickers))
    if metrics:
        q = q.where(fundamentals.c.metric.in_(metrics))
    q = q.order_by(fundamentals.c.ticker, fundamentals.c.metric,
                   fundamentals.c.fiscal_year)
    with engine.begin() as conn:
        rows = conn.execute(q).all()
    return [dict(r._mapping) for r in rows]


def tracked_tickers(engine):
    with engine.begin() as conn:
        rows = conn.execute(select(companies.c.ticker)).all()
    return [r[0] for r in rows]
