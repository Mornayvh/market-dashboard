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
import xml.etree.ElementTree as ET
from datetime import date
from typing import Optional

import requests

from src.config import (
    get_sec_user_agent, SEC_TICKER_MAP_URL, SEC_COMPANYFACTS_URL,
    SEC_SUBMISSIONS_URL, SEC_SUBMISSIONS_FILE_URL, SEC_FILING_DIR_URL,
    SEC_RATE_LIMIT_SECONDS, FUNDAMENTALS_METRICS as METRICS,
    EQUITY_COMPONENTS_AXIS, COMMON_STOCK_MEMBERS, ISSUANCE_SHARES_CONCEPT_PREFIX,
)

_LINKBASE_SUFFIXES = ("_cal.xml", "_def.xml", "_lab.xml", "_pre.xml")


def _lname(tag: str) -> str:
    """Local name of a namespaced XML tag/attribute ('{ns}Foo' -> 'Foo')."""
    return (tag or "").rsplit("}", 1)[-1].split(":")[-1]


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

    def _get_bytes(self, url: str) -> bytes:
        time.sleep(SEC_RATE_LIMIT_SECONDS)
        r = self.session.get(url, timeout=60)
        r.raise_for_status()
        return r.content

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

    def list_10k_filings(self, cik: str):
        """All 10-K / 10-K/A filings as dicts {fy, accn, period_end, filed}.

        Reads the submissions feed, including the older 'files' shards so the
        full filing history (not just the most recent ~1000) is covered.
        """
        data = self._get(SEC_SUBMISSIONS_URL.format(cik=cik))
        blocks = [data["filings"]["recent"]]
        for f in data["filings"].get("files", []):
            blocks.append(self._get(SEC_SUBMISSIONS_FILE_URL.format(name=f["name"])))
        out = []
        for b in blocks:
            for i in range(len(b.get("form", []))):
                if b["form"][i] not in ("10-K", "10-K/A"):
                    continue
                end = b["reportDate"][i]
                out.append({
                    "fy": int(end[:4]) if end else None,
                    "accn": b["accessionNumber"][i],
                    "period_end": end,
                    "filed": b["filingDate"][i],
                })
        return out

    def instance_url(self, cik: str, accn: str) -> Optional[str]:
        """Locate a filing's XBRL instance document via its directory index.

        The instance is the .xml that is not a linkbase (_cal/_def/_lab/_pre) and
        not the FilingSummary. Inline-XBRL filings expose it as '*_htm.xml';
        older filings carry a single standalone instance .xml. Returns None if
        no instance is present (e.g. very old non-XBRL filings)."""
        base = SEC_FILING_DIR_URL.format(cik_int=int(cik), accn=accn.replace("-", ""))
        idx = self._get(base + "/index.json")
        xmls = [it["name"] for it in idx["directory"]["item"]
                if it["name"].lower().endswith(".xml")]
        cand = [x for x in xmls
                if not x.endswith(_LINKBASE_SUFFIXES) and "FilingSummary" not in x]
        if not cand:
            return None
        preferred = [x for x in cand if x.endswith("_htm.xml")]
        return f"{base}/{(preferred or cand)[0]}"


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


def _parse_contexts(root):
    """Map XBRL context id -> (start, end, [(axis_localname, member_localname)])."""
    ctx = {}
    for el in root:
        if _lname(el.tag) != "context":
            continue
        start = end = None
        dims = []
        for p in el.iter():
            ln = _lname(p.tag)
            if ln == "startDate":
                start = p.text
            elif ln == "endDate":
                end = p.text
            elif ln == "instant":
                start, end = "instant", p.text
            elif ln == "explicitMember":
                dims.append((_lname(p.get("dimension")), _lname((p.text or "").strip())))
        ctx[el.get("id")] = (start, end, dims)
    return ctx


def _rollforward_issuance_shares(instance_bytes: bytes, fiscal_year: int):
    """Sum every issuance-share concept tagged against a single common-stock equity
    component for `fiscal_year`. Returns (total_shares, [concepts]) or (None, []).

    The equity-statement rollforward facts carry exactly one dimension — the
    equity-components axis on a common-stock member. Facts with a different or
    additional axis (e.g. AwardTypeAxis) are note-level breakdowns and are skipped
    to avoid double counting. Filers report EITHER a single combined issuance line
    (StockIssuedDuringPeriodSharesNewIssues) OR a set of subtype lines (RSU
    settlement, acquisitions, option exercises) in a given year, never both, so
    summing every matched concept yields the period's gross issuance.
    """
    try:
        root = ET.fromstring(instance_bytes)
    except ET.ParseError:
        return None, []
    ctx = _parse_contexts(root)
    fy = str(fiscal_year)
    by_concept = {}
    for el in root:
        # Issuance lines may be us-gaap OR a filer extension (e.g. Meta tags
        # RSU-settlement shares in its own namespace), so match on local-name
        # prefix regardless of namespace. Nothing else starts with this prefix.
        ln = _lname(el.tag)
        if not ln.startswith(ISSUANCE_SHARES_CONCEPT_PREFIX):
            continue
        meta = ctx.get(el.get("contextRef"))
        if not meta:
            continue
        start, end, dims = meta
        if start in (None, "instant") or not end or len(dims) != 1:
            continue
        if not (start[:4] == fy and end[:4] == fy):
            continue
        try:
            if not 330 <= (date.fromisoformat(end) - date.fromisoformat(start)).days <= 400:
                continue  # not an annual window
        except ValueError:
            continue
        axis, member = dims[0]
        if axis != EQUITY_COMPONENTS_AXIS or member not in COMMON_STOCK_MEMBERS:
            continue
        try:
            by_concept.setdefault(ln, {})[member] = float(el.text)
        except (TypeError, ValueError):
            continue
    if not by_concept:
        return None, []
    # Per concept: an explicit aggregate (CommonStockMember) supersedes a
    # per-share-class split; otherwise sum the class members (dual-class filers).
    total = 0.0
    for members in by_concept.values():
        total += members.get("CommonStockMember", sum(members.values()))
    return total, sorted(by_concept)


def _fill_equity_rollforward(client: SecClient, cik: str, ticker: str,
                             metric_key: str, metric_cfg: dict, covered_years: set):
    """Dimensional fallback rows for fiscal years companyfacts left empty.

    Only the missing years are fetched (each instance is a multi-MB download), so
    filers already covered by companyfacts incur no extra requests."""
    try:
        filings = client.list_10k_filings(cik)
    except Exception:  # noqa: BLE001 — never let the fallback break a refresh
        return []
    # Group filings per fiscal year, newest-filed first. A 10-K/A restatement
    # should supersede the original — but Part III-only amendments carry no XBRL
    # instance, so we try candidates in order and take the first that parses,
    # falling back to the original 10-K when the amendment has no instance.
    by_fy = {}
    for f in filings:
        if f["fy"] is None or f["fy"] in covered_years:
            continue
        by_fy.setdefault(f["fy"], []).append(f)
    rows = []
    for fy, candidates in sorted(by_fy.items()):
        for f in sorted(candidates, key=lambda x: x["filed"], reverse=True):
            try:
                url = client.instance_url(cik, f["accn"])
                shares, concepts = _rollforward_issuance_shares(
                    client._get_bytes(url), fy) if url else (None, [])
            except Exception:  # noqa: BLE001 — skip unreadable filing, try next
                continue
            if shares is None:
                continue
            rows.append({
                "metric": metric_key,
                "fiscal_year": fy,
                "period_end": f["period_end"],
                "value": shares,
                "unit": metric_cfg["unit"],
                "xbrl_tag": "equity rollforward: " + "+".join(concepts),
                "source_accn": f["accn"],
                "filed": f["filed"],
                "cik": cik,
                "ticker": ticker,
            })
            break
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

    # Dimensional gap-fill for metrics companyfacts can't fully see (issuance_shares).
    for metric_key, metric_cfg in METRICS.items():
        if not metric_cfg.get("equity_rollforward"):
            continue
        covered = {r["fiscal_year"] for r in all_rows if r["metric"] == metric_key}
        extra = _fill_equity_rollforward(client, cik, ticker, metric_key,
                                         metric_cfg, covered)
        coverage[f"{metric_key}_rollforward"] = len(extra)
        all_rows.extend(extra)
    return all_rows, coverage
