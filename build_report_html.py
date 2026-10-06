"""
build_report_html.py — Render the weekly brief (market overview + stock
watchlist) to one self-contained HTML page.

.github/workflows/weekly_report.yml builds this every Friday after the US
close and commits a dated copy under weekly/archive/, which is the file that
gets attached to the weekly email to principals. The output is committed
rather than gitignored so a `git pull` is the only step between the build and
sending it.

Usage:
    python build_report_html.py                  # writes weekly/weekly_brief.html
    python build_report_html.py --out page.html  # writes to a specific path

Pulls through the same src/ ingest layer as the PDF exporters, so the page,
the PDFs and the Streamlit dashboard always agree. FRED_API_KEY in env (or
Streamlit secrets) supplies rates and credit; without it those rows read "—".
"""

import argparse
import html
import logging
import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from export_watchlist_pdf import fetch_one
from src.config import CATEGORIES
from src.data_ingest import fetch_all_data
from src.data_process import process_all
from src.viz_helpers import fmt_change, fmt_value
from src.watchlist import CURRENCY_SYMBOLS, WATCHLIST

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Reading order for the brief: risk assets first, then the rates/credit backdrop.
# Mirrors SECTION_ORDER in export_pdf.py — keep the two in step.
SECTION_ORDER = ["Equities", "Rates", "Currency", "Credit", "Commodities", "Sentiment", "Volatility"]
SECTION_LABELS = {"Credit": "Credit Spreads"}

# The band across the top. Each is a name in src/config.ASSETS; anything not
# fetched that week is dropped from the band rather than shown blank.
KEY_LEVELS = [
    "S&P 500", "Nasdaq 100", "JSE All Share", "US 10Y Yield",
    "Gold", "Oil (Brent)", "USD/ZAR", "VIX",
]

MOVERS_PER_SIDE = 3  # top N risers and N fallers in the movers strip


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------

def _num(val):
    """Coerce pandas NA to None so the templates have one empty case to test."""
    if val is None or pd.isna(val):
        return None
    return float(val)


def collect_market() -> dict:
    """Fetch and shape the macro side: {category: [row, ...]} plus key levels."""
    logger.info("Fetching market data...")
    metrics = process_all(fetch_all_data())
    logger.info("Market data loaded for %d assets", len(metrics))

    rows_by_name = {}
    sections = []
    for category in SECTION_ORDER:
        rows = []
        subset = metrics[metrics["category"] == category]
        for name, r in subset.iterrows():
            is_rate, is_spread = bool(r["is_rate"]), bool(r["is_spread"])
            row = {
                "name": name,
                "value": fmt_value(_num(r["latest"]), is_rate, is_spread),
                "changes": [
                    (_num(r["daily_chg"]), fmt_change(_num(r["daily_chg"]), is_rate, is_spread)),
                    (_num(r["weekly_chg"]), fmt_change(_num(r["weekly_chg"]), is_rate, is_spread)),
                    (_num(r["ltm_chg"]), fmt_change(_num(r["ltm_chg"]), is_rate, is_spread)),
                ],
                "invert": bool(r["invert_color"]),
            }
            rows.append(row)
            rows_by_name[name] = row
        if rows:
            sections.append({"title": SECTION_LABELS.get(category, category), "rows": rows})

    key_levels = [rows_by_name[n] for n in KEY_LEVELS if n in rows_by_name]
    return {"sections": sections, "key_levels": key_levels}


def collect_watchlist() -> dict:
    """Fetch and shape the holdings side: one group per WATCHLIST key."""
    logger.info("Fetching watchlist data for %d names...",
                sum(len(v) for v in WATCHLIST.values()))
    groups, movers = [], []
    for group, stocks in WATCHLIST.items():
        rows = []
        for name, ticker, currency in stocks:
            price, c1d, c1m, cltm, hi, lo = fetch_one(ticker)
            price, c1d, c1m, cltm = _num(price), _num(c1d), _num(c1m), _num(cltm)
            hi, lo = _num(hi), _num(lo)

            # Where the last price sits in the 52-week range, 0–1. Needs a full
            # year of history (fetch_one returns hi/lo as None otherwise) and a
            # range wide enough to place a marker in.
            pos = None
            if None not in (price, hi, lo) and hi > lo:
                pos = min(max((price - lo) / (hi - lo), 0.0), 1.0)

            rows.append({
                "name": name, "ticker": ticker, "currency": currency,
                "price": fmt_price(price, currency),
                "changes": [(c1d, fmt_pct(c1d)), (c1m, fmt_pct(c1m)), (cltm, fmt_pct(cltm))],
                "hi": fmt_price(hi, currency), "lo": fmt_price(lo, currency),
                "pos": pos,
            })
            if c1m is not None:
                movers.append({"name": name, "chg": c1m, "label": fmt_pct(c1m)})
        groups.append({"title": group, "rows": rows})

    movers.sort(key=lambda m: m["chg"], reverse=True)
    top = movers[:MOVERS_PER_SIDE]
    bottom = [m for m in movers[-MOVERS_PER_SIDE:] if m not in top]
    return {"groups": groups, "movers": top + list(reversed(bottom))}


# ---------------------------------------------------------------------------
# Formatting — watchlist only; the macro side comes pre-formatted from
# src.viz_helpers so the page and the Streamlit dashboard never disagree.
# ---------------------------------------------------------------------------

def fmt_price(val, currency) -> str:
    """Price with its listing currency symbol, precision scaled to magnitude."""
    if val is None:
        return "—"
    sym = CURRENCY_SYMBOLS.get(currency, "")
    if val >= 10000:
        return f"{sym}{val:,.0f}"
    if val >= 100:
        return f"{sym}{val:,.1f}"
    return f"{sym}{val:,.2f}"


def fmt_pct(val) -> str:
    if val is None:
        return "—"
    return f"{'+' if val >= 0 else ''}{val:.1f}%"


def tone(val, invert=False) -> str:
    """CSS class for a change cell. invert for VIX and spreads, where up is bad."""
    if val is None or val == 0:
        return "flat"
    return ("neg" if val > 0 else "pos") if invert else ("pos" if val > 0 else "neg")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

CSS = """
:root {
  --ground: #F1F5F9;
  --surface: #FFFFFF;
  --surface-alt: #F8FAFC;
  --border: #E2E8F0;
  --rule: #CBD5E1;
  --ink: #1E293B;
  --ink-2: #64748B;
  --ink-3: #94A3B8;
  --accent: #4F7FD6;
  --pos: #16A34A;
  --neg: #DC2626;
  --flat: #94A3B8;
  --track: #E2E8F0;
  --shadow: 0 1px 2px rgba(30, 41, 59, .06), 0 8px 24px -16px rgba(30, 41, 59, .25);
}

/* Dark for viewers on the default "system" setting, unless they chose light. */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground: #0B1220;
    --surface: #131C2E;
    --surface-alt: #18233A;
    --border: #27354F;
    --rule: #33425F;
    --ink: #E8EDF6;
    --ink-2: #A5B2C8;
    --ink-3: #7A8AA3;
    --accent: #7FA7E8;
    --pos: #3DD68C;
    --neg: #FF6F6F;
    --flat: #7A8AA3;
    --track: #27354F;
    --shadow: 0 1px 2px rgba(0, 0, 0, .4), 0 8px 24px -16px rgba(0, 0, 0, .8);
  }
}

/* And for viewers who explicitly chose dark, whatever their OS says. */
:root[data-theme="dark"] {
  --ground: #0B1220;
  --surface: #131C2E;
  --surface-alt: #18233A;
  --border: #27354F;
  --rule: #33425F;
  --ink: #E8EDF6;
  --ink-2: #A5B2C8;
  --ink-3: #7A8AA3;
  --accent: #7FA7E8;
  --pos: #3DD68C;
  --neg: #FF6F6F;
  --flat: #7A8AA3;
  --track: #27354F;
  --shadow: 0 1px 2px rgba(0, 0, 0, .4), 0 8px 24px -16px rgba(0, 0, 0, .8);
}

* { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--ground);
  color: var(--ink);
  font-family: "IBM Plex Sans", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 15px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

.page {
  max-width: 1120px;
  margin: 0 auto;
  padding: 28px 20px 64px;
  display: flex;
  flex-direction: column;
  gap: 34px;
}

/* ---- Masthead ---- */

.masthead {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-bottom: 20px;
  border-bottom: 2px solid var(--ink);
}

.eyebrow {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: .14em;
  text-transform: uppercase;
  color: var(--accent);
}

.masthead h1 {
  margin: 0;
  font-family: Newsreader, ui-serif, Georgia, serif;
  font-size: clamp(2rem, 6vw, 3.1rem);
  font-weight: 500;
  line-height: 1.05;
  letter-spacing: -.015em;
  text-wrap: balance;
}

.standfirst {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  font-size: 13px;
  color: var(--ink-2);
}

.standfirst .sep { color: var(--ink-3); }

/* ---- Key levels band ---- */

.levels {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1px;
  background: var(--border);
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
  box-shadow: var(--shadow);
}

.level {
  background: var(--surface);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.level .label {
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: var(--ink-3);
}

.level .value {
  font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 19px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  letter-spacing: -.02em;
}

.level .delta {
  font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

/* ---- Movers strip ---- */

.movers {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px 10px;
}

.movers .caption {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: var(--ink-3);
  margin-right: 2px;
}

.chip {
  display: inline-flex;
  align-items: baseline;
  gap: 7px;
  padding: 5px 11px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--surface);
  font-size: 13px;
  white-space: nowrap;
}

.chip b {
  font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

/* ---- Sections and tables ---- */

section { display: flex; flex-direction: column; gap: 16px; }

.section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.section-head h2 {
  margin: 0;
  font-family: Newsreader, ui-serif, Georgia, serif;
  font-size: 1.6rem;
  font-weight: 500;
  letter-spacing: -.01em;
}

.section-head .note { font-size: 12.5px; color: var(--ink-2); }

.block { display: flex; flex-direction: column; gap: 0; }

.block > h3 {
  margin: 0;
  padding: 10px 16px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: var(--ink-2);
  background: var(--surface-alt);
  border: 1px solid var(--border);
  border-bottom: 0;
  border-radius: 6px 6px 0 0;
}

.scroll {
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: 0 0 6px 6px;
  background: var(--surface);
  box-shadow: var(--shadow);
}

table {
  width: 100%;
  min-width: 540px;
  border-collapse: collapse;
}

th {
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: var(--ink-3);
  text-align: right;
  padding: 9px 16px;
  border-bottom: 1px solid var(--rule);
  white-space: nowrap;
}

th:first-child { text-align: left; }

td {
  padding: 9px 16px;
  border-bottom: 1px solid var(--border);
  text-align: right;
  font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 13.5px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

tr:last-child td { border-bottom: 0; }

td.name {
  text-align: left;
  font-family: "IBM Plex Sans", ui-sans-serif, system-ui, sans-serif;
  font-size: 14px;
  white-space: normal;
}

td.name .tick {
  color: var(--ink-3);
  font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 10.5px;
  margin-left: 7px;
}

td.level-val { color: var(--ink); }

.pos { color: var(--pos); }
.neg { color: var(--neg); }
.flat { color: var(--flat); }

/* ---- 52-week range ---- */

.range { display: flex; align-items: center; gap: 9px; justify-content: flex-end; }

.range .bound { font-size: 11.5px; color: var(--ink-3); }

.track {
  position: relative;
  width: 72px;
  height: 3px;
  border-radius: 2px;
  background: var(--track);
  flex: none;
}

.marker {
  position: absolute;
  top: 50%;
  width: 7px;
  height: 7px;
  margin: -3.5px 0 0 -3.5px;
  border-radius: 50%;
  background: var(--accent);
}

.range.empty { color: var(--ink-3); }

/* ---- Footer ---- */

footer {
  border-top: 1px solid var(--border);
  padding-top: 18px;
  font-size: 12px;
  color: var(--ink-3);
  display: flex;
  flex-direction: column;
  gap: 5px;
}

@media (max-width: 600px) {
  .page { padding: 20px 14px 48px; gap: 26px; }
  th, td { padding-left: 12px; padding-right: 12px; }
}
"""

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    'family=IBM+Plex+Mono:wght@400;500&'
    'family=IBM+Plex+Sans:wght@400;500;600&'
    'family=Newsreader:opsz,wght@6..72,400;6..72,500&display=swap">'
)


def esc(s) -> str:
    return html.escape(str(s))


def change_cells(changes, invert=False) -> str:
    """The three change columns, each coloured by sign."""
    return "".join(
        f'<td class="{tone(val, invert)}">{esc(label)}</td>' for val, label in changes
    )


def render_market_section(section: dict) -> str:
    rows = "".join(
        "<tr>"
        f'<td class="name">{esc(r["name"])}</td>'
        f'<td class="level-val">{esc(r["value"])}</td>'
        f'{change_cells(r["changes"], r["invert"])}'
        "</tr>"
        for r in section["rows"]
    )
    return (
        '<div class="block">'
        f'<h3>{esc(section["title"])}</h3>'
        '<div class="scroll"><table>'
        "<thead><tr><th>Instrument</th><th>Level</th><th>1D</th><th>1W</th><th>LTM</th></tr></thead>"
        f"<tbody>{rows}</tbody>"
        "</table></div></div>"
    )


def render_range(r: dict) -> str:
    """52-week low, a track with the last price marked, and the high."""
    if r["pos"] is None:
        return '<td class="range empty">—</td>'
    return (
        '<td><div class="range">'
        f'<span class="bound">{esc(r["lo"])}</span>'
        f'<span class="track"><span class="marker" style="left:{r["pos"] * 100:.1f}%"></span></span>'
        f'<span class="bound">{esc(r["hi"])}</span>'
        "</div></td>"
    )


def render_watchlist_group(group: dict) -> str:
    rows = "".join(
        "<tr>"
        f'<td class="name">{esc(r["name"])}<span class="tick">{esc(r["ticker"])}</span></td>'
        f'<td class="level-val">{esc(r["price"])}</td>'
        f'{change_cells(r["changes"])}'
        f"{render_range(r)}"
        "</tr>"
        for r in group["rows"]
    )
    return (
        '<div class="block">'
        f'<h3>{esc(group["title"])}</h3>'
        '<div class="scroll"><table>'
        "<thead><tr><th>Holding</th><th>Price</th><th>1D</th><th>1M</th><th>LTM</th>"
        "<th>52-Week Range</th></tr></thead>"
        f"<tbody>{rows}</tbody>"
        "</table></div></div>"
    )


def render_html(market: dict, watch: dict, now: datetime) -> str:
    levels = "".join(
        '<div class="level">'
        f'<span class="label">{esc(r["name"])}</span>'
        f'<span class="value">{esc(r["value"])}</span>'
        f'<span class="delta {tone(r["changes"][1][0], r["invert"])}">'
        f'{esc(r["changes"][1][1])} 1W</span>'
        "</div>"
        for r in market["key_levels"]
    )

    movers = "".join(
        f'<span class="chip">{esc(m["name"])}'
        f'<b class="{tone(m["chg"])}">{esc(m["label"])}</b></span>'
        for m in watch["movers"]
    )
    movers_block = (
        f'<div class="movers"><span class="caption">Biggest 1M moves</span>{movers}</div>'
        if movers else ""
    )

    n_holdings = sum(len(g["rows"]) for g in watch["groups"])

    return f"""<title>Secco Weekly Market Brief</title>
{FONTS}
<style>{CSS}</style>

<div class="page">

  <header class="masthead">
    <span class="eyebrow">Secco Capital</span>
    <h1>Weekly Market Brief</h1>
    <div class="standfirst">
      <span>As at {now.strftime("%A, %d %B %Y")}</span>
      <span class="sep">·</span>
      <span>Rebuilt every Friday after the New York close</span>
    </div>
  </header>

  <div class="levels">{levels}</div>

  <section>
    <div class="section-head">
      <h2>Market Overview</h2>
      <span class="note">Rates and spreads move in absolute terms; everything else in per cent.</span>
    </div>
    {"".join(render_market_section(s) for s in market["sections"])}
  </section>

  <section>
    <div class="section-head">
      <h2>Stock Watchlist</h2>
      <span class="note">{n_holdings} holdings · priced in the listing currency</span>
    </div>
    {movers_block}
    {"".join(render_watchlist_group(g) for g in watch["groups"])}
  </section>

  <footer>
    <span>Point-in-time snapshot built {now.astimezone().strftime("%d %B %Y at %H:%M %Z")}.
          Sources: Yahoo Finance (prices), FRED (rates and credit spreads).</span>
    <span>Secco Capital · Confidential · Not investment advice.</span>
  </footer>

</div>
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build(out_path: str) -> str:
    market = collect_market()
    watch = collect_watchlist()
    page = render_html(market, watch, datetime.now())

    parent = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(parent, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(page)

    logger.info("Wrote %s (%.0f KB)", out_path, os.path.getsize(out_path) / 1000)
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="weekly/weekly_brief.html",
                    help="Output path (default: weekly/weekly_brief.html)")
    args = ap.parse_args()
    build(args.out)


if __name__ == "__main__":
    main()
