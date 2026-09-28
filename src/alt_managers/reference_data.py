"""reference_data.py — Hand-maintained fundamentals NOT available via Yahoo.

Yahoo Finance carries no AUM (assets under management) for alt managers — it is a
business fundamental each firm reports in its quarterly results, not a market data
field. This module holds **Total AUM** as a small, manually-refreshed table so the
comparison page can show size-of-business alongside the market-data columns.

Nothing refreshes this file automatically: the figures move only when someone edits
it, which is why they sit at the last reporting date checked, not at today's date.

REFRESH WORKFLOW
----------------
Each quarter, once the last firm has reported (US managers report Q-end + ~4-5 weeks;
the Europeans report half-yearly), for each ticker update:
  * total_aum_usd_bn — Total AUM in USD billions (convert if the firm reports in
    another currency; the rate and date used are noted in `source`)
  * as_of           — the reporting date the figure applies to (YYYY-MM-DD)
  * source          — the primary disclosure it came from, plus any basis caveat
Then bump LAST_VERIFIED. Set total_aum_usd_bn to None when a firm does not report a
comparable Total-AUM figure (advisory-led or proprietary-capital businesses); the
page renders "—".

Next refresh due: Q3'26 / 9M'26 reporting, from late October 2026.

CURRENT STATE
-------------
Every figure below was checked against the firm's own Q2'26 (US) or H1'26 (Europe)
disclosure on the LAST_VERIFIED date. Two carry a basis caveat, both flagged in
`source`:
  * BAM  — the press release says only "over USD 1tn"; the Q2'26 supplemental (p.2)
           gives USD 1.3tn. Not like-for-like with the other rows: BAM defines AUM
           across Brookfield as a whole (incl. Brookfield Corporation) and states its
           methodology differs from other alt managers. Its comparable, precisely-
           disclosed manager metric is fee-bearing capital of USD 672bn.
  * CVC  — the H1'26 results disclose fee-paying AUM (EUR 153.2bn) only; the total
           AUM figure is CVC's own EUR 212bn, stated as at 30 June 2026.
"""

from __future__ import annotations

# Date the whole table was last checked against primary disclosures (YYYY-MM-DD).
LAST_VERIFIED = "2026-09-28"

# EUR->USD rate used for the European conversions below: EURUSD=X close on
# 30 June 2026 (Yahoo Finance), the reporting date those figures apply to.
_EURUSD_30JUN26 = 1.1422

# Total AUM in USD billions, at each firm's latest reported date. See module docstring.
AUM: dict[str, dict] = {
    # Big Seven — US diversified (Q2'26, quarter ended 30 June 2026)
    "BX":      {"total_aum_usd_bn": 1346, "as_of": "2026-06-30",
                "source": "Q2'26 results — total AUM USD 1,346.3bn; fee-earning USD 961.6bn"},
    "KKR":     {"total_aum_usd_bn":  796, "as_of": "2026-06-30",
                "source": "Q2'26 earnings release — AUM USD 796bn, +16% y/y"},
    "APO":     {"total_aum_usd_bn": 1050, "as_of": "2026-06-30",
                "source": "Q2'26 results — 'approximately USD 1.05tn'"},
    "CG":      {"total_aum_usd_bn":  485, "as_of": "2026-06-30",
                "source": "Q2'26 results — total AUM USD 485bn; fee-earning USD 334bn"},
    "BAM":     {"total_aum_usd_bn": 1300, "as_of": "2026-06-30",
                "source": "Q2'26 supplemental p.2 — 'USD 1.3T Assets Under Management'; "
                          "fee-bearing capital USD 672bn. Brookfield-wide basis (incl. "
                          "Brookfield Corporation), methodology differs from peers"},
    "TPG":     {"total_aum_usd_bn":  327, "as_of": "2026-06-30",
                "source": "Q2'26 results — USD 327bn, +25% y/y"},
    # European (report in their own currency; converted at _EURUSD_30JUN26)
    "EQT.ST":  {"total_aum_usd_bn":  332, "as_of": "2026-06-30",
                "source": "H1'26 report — total AUM EUR 291bn (FAUM EUR 155bn), "
                          "converted at EUR/USD 1.1422 on 30 Jun 2026"},
    "CVC.AS":  {"total_aum_usd_bn":  242, "as_of": "2026-06-30",
                "source": "H1'26 — total AUM EUR 212bn as at 30 Jun 2026 (results "
                          "disclose fee-paying AUM EUR 153.2bn only), converted at "
                          "EUR/USD 1.1422 on 30 Jun 2026"},
    "PGHN.SW": {"total_aum_usd_bn":  186, "as_of": "2026-06-30",
                "source": "H1'26 results — USD 186bn; Partners Group reports in USD"},
}


def get(ticker: str) -> dict:
    """Reference record for a ticker. Always returns a dict; unknown -> all None."""
    return AUM.get(ticker, {"total_aum_usd_bn": None, "as_of": None, "source": None})


def total_aum_usd_bn(ticker: str) -> float | None:
    """Total AUM in USD billions, or None if not tracked/comparable."""
    return get(ticker).get("total_aum_usd_bn")
