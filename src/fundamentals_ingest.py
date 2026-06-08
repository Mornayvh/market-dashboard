"""
fundamentals_ingest.py
Ingestion layer: pull XBRL company-facts from SEC EDGAR and normalize them
into rows ready for the database. Mirrors the role of data_ingest.py.

Key responsibilities:
  - resolve tickers -> zero-padded CIKs (via SEC ticker map)
  - fetch companyfacts JSON per company
  - extract ANNUAL (10-K, fiscal-year) values per metric, trying candidate
    XBRL tags in order until one is populated
  - align each value to the filing's OWN fiscal year + period end date
    (this is what fixes the calendar-vs-fiscal-year offset)
"""

import time
from datetime import date
from typing import Optional

import requests

from src.config import (
    get_sec_user_agent, SEC_TICKER_MAP_URL, SEC_COMPANYFACTS_URL,
    SEC_RATE_LIMIT_SECONDS, FUNDAMENTALS_METRICS as METRICS,
)


class SecClient:
    def __init__(self, user_agent: Optional[str] = None):
        user_agent = user_agent or get_sec_user_agent()
        if not user_agent or "@" not in user_agent:
            raise ValueError(
                "SEC_USER_AGENT must be a real 'Name email@domain' string. "
                "The SEC blocks requests without it. Set the SEC_USER_AGENT "
                "env var or add it to Streamlit secrets under [general]."
            )
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate",
        })

    def _get(self, url: str) -> dict:
        time.sleep(SEC_RATE_LIMIT_SECONDS)
        r = self.session.get(url, timeout=30)
        r.raise_for_status()
        return r.json()

    def resolve_ciks(self, tickers):
        raw = self._get(SEC_TICKER_MAP_URL)
        lookup = {row["ticker"].upper(): (f'{row["cik_str"]:010d}', row["title"])
                  for row in raw.values()}
        out = {}
        for t in tickers:
            hit = lookup.get(t.upper())
            if hit:
                out[t.upper()] = {"cik": hit[0], "name": hit[1]}
        return out

    def company_facts(self, cik: str) -> dict:
        return self._get(SEC_COMPANYFACTS_URL.format(cik=cik))


def _extract_metric(facts: dict, metric_key: str, metric_cfg: dict):
    """Return list of normalized rows for one metric, or [] if no tag matched.

    Candidate tags are applied PER FISCAL YEAR in priority order: a later tag
    only fills years the earlier tags didn't cover. Filers rename tags across
    eras (e.g. NVDA's buybacks moved from StockRepurchasedDuringPeriodShares
    to StockRepurchasedAndRetiredDuringPeriodShares in FY2023), so taking the
    first tag with *any* data would silently truncate recent years.

    Within one filing, every fact (current year + prior-year comparatives)
    carries the filing's own `fy`, so we only accept the filing's CURRENT-year
    fact: period-end year must equal `fy` (true for every filer in the
    configured universe — relax if you ever add a filer that labels its fiscal
    year by start year), and the period must be annual-length (old filings
    occasionally mislabel quarterly windows as fp=FY). This is what keeps each
    value aligned to the filing's own fiscal year + period end. The latest
    filed date then wins per fy, so 10-K/A restatements supersede.
    """
    unit = metric_cfg["unit"]
    by_fy = {}
    for taxonomy, tag in metric_cfg["tags"]:
        node = facts.get("facts", {}).get(taxonomy, {}).get(tag)
        if not node:
            continue
        unit_data = node.get("units", {}).get(unit)
        if not unit_data:
            continue
        for item in unit_data:
            if item.get("fp") != "FY":
                continue
            if item.get("form") not in ("10-K", "10-K/A"):
                continue
            fy = item.get("fy")
            if fy is None:
                continue
            end, start = item.get("end") or "", item.get("start") or ""
            if not end or int(end[:4]) != fy:
                continue  # comparative period or mislabelled fy
            if start:
                days = (date.fromisoformat(end) - date.fromisoformat(start)).days
                if not 330 <= days <= 400:
                    continue  # not an annual window (e.g. quarterly fact tagged FY)
            prev = by_fy.get(fy)
            if prev is not None and prev["_tag"] != tag:
                continue  # a higher-priority tag already supplied this year
            if prev is None or item.get("filed", "") > prev.get("filed", ""):
                by_fy[fy] = item | {"_tag": tag}
    rows = []
    for fy, item in sorted(by_fy.items()):
        rows.append({
            "metric": metric_key,
            "fiscal_year": fy,
            "period_end": item.get("end"),
            "value": item.get("val"),
            "unit": unit,
            "xbrl_tag": item.get("_tag"),
            "source_accn": item.get("accn"),
            "filed": item.get("filed"),
        })
    return rows


def fetch_company_rows(client: SecClient, cik: str, ticker: str):
    """Fetch + normalize all metrics for one company. Returns list of row dicts."""
    facts = client.company_facts(cik)
    all_rows = []
    coverage = {}
    for metric_key, metric_cfg in METRICS.items():
        rows = _extract_metric(facts, metric_key, metric_cfg)
        coverage[metric_key] = len(rows)
        for r in rows:
            r["cik"] = cik
            r["ticker"] = ticker
        all_rows.extend(rows)
    return all_rows, coverage
