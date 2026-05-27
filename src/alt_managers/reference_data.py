"""reference_data.py — Hand-maintained fundamentals NOT available via Yahoo.

Yahoo Finance carries no AUM (assets under management) for alt managers — it is a
business fundamental each firm reports in its quarterly results, not a market data
field. This module holds **Total AUM** as a small, manually-refreshed table so the
comparison page can show size-of-business alongside the market-data columns.

REFRESH WORKFLOW
----------------
Each quarter, for each ticker update:
  * total_aum_usd_bn — Total AUM in USD billions (convert if the firm reports in
    another currency; the reporting currency is noted in `source` where relevant)
  * as_of           — the reporting date the figure applies to (YYYY-MM-DD)
  * source          — where it came from (e.g. "Q1'26 results")
Set total_aum_usd_bn to None when a firm does not report a comparable Total-AUM
figure (advisory-led or proprietary-capital businesses); the page renders "—".

⚠️  THE SEEDED FIGURES BELOW ARE APPROXIMATE AND MUST BE VERIFIED against each
    firm's primary disclosure before they are relied upon. They were seeded from
    public disclosures around the `as_of` dates shown and are intentionally
    rounded. Treat them as placeholders until checked.
"""

from __future__ import annotations

# Total AUM in USD billions. See module docstring — VERIFY before relying on these.
AUM: dict[str, dict] = {
    # Big Seven — US diversified
    "BX":      {"total_aum_usd_bn": 1200, "as_of": "2025-12-31", "source": "Q4'25 results — VERIFY"},
    "KKR":     {"total_aum_usd_bn":  680, "as_of": "2025-12-31", "source": "Q4'25 results — VERIFY"},
    "APO":     {"total_aum_usd_bn":  840, "as_of": "2025-12-31", "source": "Q4'25 results — VERIFY"},
    "ARES":    {"total_aum_usd_bn":  560, "as_of": "2025-12-31", "source": "Q4'25 results — VERIFY"},
    "CG":      {"total_aum_usd_bn":  470, "as_of": "2025-12-31", "source": "Q4'25 results — VERIFY"},
    "OWL":     {"total_aum_usd_bn":  290, "as_of": "2025-12-31", "source": "Q4'25 results — VERIFY"},
    "BN":      {"total_aum_usd_bn": None, "as_of": None,         "source": "AUM reported at BAM level — do not double-count"},
    "BAM":     {"total_aum_usd_bn": 1050, "as_of": "2025-12-31", "source": "Q4'25 — Brookfield total AUM — VERIFY"},
    "TPG":     {"total_aum_usd_bn":  250, "as_of": "2025-12-31", "source": "Q4'25 results — VERIFY"},
    # European (reported currency noted; figures converted to USD — VERIFY)
    "EQT.ST":  {"total_aum_usd_bn":  280, "as_of": "2025-12-31", "source": "FY'25, reports in EUR — VERIFY"},
    "CVC.AS":  {"total_aum_usd_bn":  215, "as_of": "2025-12-31", "source": "FY'25, reports in EUR — VERIFY"},
    "III.L":   {"total_aum_usd_bn": None, "as_of": None,         "source": "Proprietary-capital model; no comparable AUM"},
    "BPT.L":   {"total_aum_usd_bn":   47, "as_of": "2025-12-31", "source": "FY'25, reports in EUR — VERIFY"},
    "PGHN.SW": {"total_aum_usd_bn":  150, "as_of": "2025-12-31", "source": "FY'25 results — VERIFY"},
    # Specialists
    "HLNE":    {"total_aum_usd_bn":  135, "as_of": "2025-12-31", "source": "Latest results (AUM, excl. AUA) — VERIFY"},
    "STEP":    {"total_aum_usd_bn":  190, "as_of": "2025-12-31", "source": "Latest results — VERIFY"},
    "PAX":     {"total_aum_usd_bn":   45, "as_of": "2025-12-31", "source": "Q4'25 results — VERIFY"},
    "PJT":     {"total_aum_usd_bn": None, "as_of": None,         "source": "Advisory-led; minimal AUM"},
    "EMG.L":   {"total_aum_usd_bn":  175, "as_of": "2025-12-31", "source": "FY'25 results — VERIFY"},
}


def get(ticker: str) -> dict:
    """Reference record for a ticker. Always returns a dict; unknown -> all None."""
    return AUM.get(ticker, {"total_aum_usd_bn": None, "as_of": None, "source": None})


def total_aum_usd_bn(ticker: str) -> float | None:
    """Total AUM in USD billions, or None if not tracked/comparable."""
    return get(ticker).get("total_aum_usd_bn")
