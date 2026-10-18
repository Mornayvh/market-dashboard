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
import json
import logging
import re
import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import ASSETS
from src.data_ingest import fetch_fred_series
from src.data_process import process_all
from src.viz_helpers import fmt_change, fmt_value
from src.watchlist import (
    CURRENCY_SYMBOLS, WATCHLIST, fetch_closes, fetch_earnings, fetch_watchlist,
)

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

# How far back "reported this week" reaches. Seven days from the build date
# covers the Friday-evening Actions run and a weekend rebuild alike.
REPORTED_WITHIN_DAYS = 7

# Refuse to write a page where this share of holdings came back priceless.
# Yahoo rate-limits a datacentre IP, and on 10 October 2026 that silently
# produced a brief with 31 of 36 holdings blank which the workflow committed
# and reported as a success. Failing loudly beats shipping a gutted page.
MAX_BLANK_SHARE = 0.15

# Timeframes offered in the modal, and how many points of each survive into
# the page. The chart is 640 CSS pixels wide, so 100 points puts one every
# six — past the eye's ability to tell them apart, and the difference between
# a page that stays an email attachment and one that does not.
TIMEFRAMES = [("1Y", 365), ("3Y", 1095), ("5Y", 1825), ("10Y", 3650)]
SERIES_POINTS = 100
MIN_SERIES_POINTS = 12          # below this a window is not worth drawing
CHART_W, CHART_H, CHART_PAD = 640, 180, 12

# FRED series run back decades; this is deep enough for a Max button without
# hauling the Fed Funds rate since 1954 into an email attachment.
FRED_START = "1995-01-01"

# Hand-written each week and spliced in by update_commentary.py, which reuses
# render_commentary below so there is only ever one renderer. The markers in
# the page are how that script finds the boxes.
COMMENTARY_PATH = "weekly/commentary.md"
COMMENTARY_SECTIONS = ["Market Overview", "Stock Watchlist"]

# Per-asset commentary and news for the chart modals, written by hand in the
# same way and spliced in by the same script.
ASSETS_PATH = "weekly/assets.md"


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------

def read_commentary(path: str = COMMENTARY_PATH) -> dict:
    """The two hand-written paragraphs, keyed by section heading.

    Anything before the first "## " heading is the file's own instructions and
    is discarded. A heading with nothing under it yields no entry, so the box
    is left off the page rather than printed empty.
    """
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        logger.info("No %s — building without commentary.", path)
        return {}

    out = {}
    for chunk in raw.split("\n## ")[1:]:
        head, _, body = chunk.partition("\n")
        body = body.split("\n## ")[0].strip()
        if body:
            out[head.strip()] = body

    missing = [s for s in COMMENTARY_SECTIONS if s not in out]
    if missing:
        logger.warning("Commentary not written for: %s", ", ".join(missing))
    return out


def read_asset_notes(path: str = ASSETS_PATH) -> dict:
    """Per-asset commentary and news, keyed by whatever heading was typed.

    Resolution to an instrument happens later, in attach_asset_notes, so a
    heading can be a name ("Apple", "USD/ZAR") or a ticker ("AAPL") — nobody
    should have to type the internal slug.

    Each "### " section is free prose, optionally followed by a News: block of
        - YYYY-MM-DD | Headline | https://...
    """
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        return {}

    notes = {}
    for chunk in raw.split("\n### ")[1:]:
        head, _, body = chunk.partition("\n")
        body = body.split("\n### ")[0].split("\n## ")[0].strip()
        if not body:
            continue

        # Sections are introduced by bare "Earnings:" / "News:" labels on
        # their own line; everything before the first one is the prose.
        marks = [(m.start(), m.group(1)) for m in
                 re.finditer(r"^(Earnings|News):\s*$", body, re.M)]
        bounds = [m[0] for m in marks] + [len(body)]
        prose = body[:bounds[0]].strip()

        blocks = {}
        for i, (pos, name) in enumerate(marks):
            start = pos + body[pos:].index(":") + 1
            blocks[name] = body[start:bounds[i + 1]].strip()

        earnings = blocks.get("Earnings", "")
        articles = []
        for line in blocks.get("News", "").splitlines():
            line = line.strip().lstrip("-").strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 2:
                logger.warning("Skipping malformed news line under %r: %s", head.strip(), line)
                continue
            date, title = parts[0], parts[1]
            url = parts[2] if len(parts) > 2 else ""
            articles.append({"d": date, "t": title, "u": url})

        if prose or earnings or articles:
            notes[slugify(head.strip())] = {
                "c": prose, "e": earnings, "news": articles,
            }
    return notes


def attach_asset_notes(instruments: dict, aliases: dict, notes: dict) -> None:
    """Fold the hand-written notes into the instrument payloads, in place."""
    unmatched = []
    for key, note in notes.items():
        target = aliases.get(key)
        if not target:
            unmatched.append(key)
            continue
        for field in ("c", "e", "news"):   # never "er" — that is fetched, not written
            if note.get(field):
                instruments[target][field] = note[field]

    if unmatched:
        logger.warning("Asset notes matched nothing: %s", ", ".join(sorted(unmatched)))
    matched = len(notes) - len(unmatched)
    if matched:
        logger.info("Attached notes to %d instrument(s).", matched)


def render_commentary(text: str | None) -> str:
    """One commentary box, or nothing at all when the section is unwritten."""
    if not text:
        return ""
    paras = "".join(f"<p>{esc(p.strip())}</p>"
                    for p in re.split(r"\n\s*\n", text) if p.strip())
    return (
        '<aside class="commentary">'
        '<span class="commentary-label">Week in review</span>'
        f'<div class="commentary-body">{paras}</div>'
        "</aside>"
    )


def slugify(value: str) -> str:
    """Element id safe for tickers like BRK-B, 002594.SZ and names like S&P 500."""
    return re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()


def _num(val):
    """Coerce pandas NA to None so the templates have one empty case to test."""
    if val is None or pd.isna(val):
        return None
    return float(val)


def _thin(vals: list, n: int) -> list:
    """Reduce a series to at most n points by stride, always keeping the last."""
    if len(vals) <= n:
        return list(vals)
    stride = len(vals) / n
    out = [vals[int(i * stride)] for i in range(n)]
    out[-1] = vals[-1]
    return out


def _window(win, scale: float, dp: int) -> dict:
    """Values plus the date of each one, for the chart's hover readout.

    Dates ride along as whole-day offsets from the window's first date rather
    than as strings: trading days are not evenly spaced, so the hover card
    would drift by days if the position were interpolated, and 100 ISO dates
    per window across 62 instruments and 5 windows is a lot of page to carry.
    """
    idx = _thin(list(win.index), SERIES_POINTS)
    start = idx[0]
    return {
        "v": [round(float(v) * scale, dp) for v in _thin(win.tolist(), SERIES_POINTS)],
        "t": start.strftime("%Y-%m-%d"),
        "o": [int((d - start).days) for d in idx],
    }


def build_timeframes(close, scale: float = 1.0, dp: int = 2) -> tuple[dict, str | None]:
    """Chart series per timeframe, offering only the ones the history covers.

    A holding listed two years ago gets 1Y and Max and nothing else — putting
    a "10Y" button on two years of data and drawing the same line as "3Y"
    would be a lie about the history, and three identical charts besides.
    """
    if close is None or len(close) < MIN_SERIES_POINTS:
        return {}, None

    end = close.index[-1]
    span_days = (end - close.index[0]).days

    out = {}
    for label, days in TIMEFRAMES:
        if span_days < days:
            continue
        win = close[close.index >= end - pd.Timedelta(days=days)]
        if len(win) >= MIN_SERIES_POINTS:
            out[label] = _window(win, scale, dp)
    out["Max"] = _window(close, scale, dp)

    return out, ("1Y" if "1Y" in out else "Max")


def fetch_market_history() -> dict:
    """Full close history for every macro asset, keyed by display name.

    Yahoo in one batch; FRED one series at a time, since each is a separate
    endpoint. FRED_START rather than the ingest layer's rolling year, because
    the brief charts rates and spreads over a decade.
    """
    yf_assets = [a for a in ASSETS if a.ticker]
    closes = fetch_closes([a.ticker for a in yf_assets], "max")

    out = {}
    for a in yf_assets:
        c = closes.get(a.ticker)
        if c is not None and len(c):
            out[a.name] = c

    for a in ASSETS:
        if a.name in out or not a.fred_id:
            continue
        df = fetch_fred_series(a.fred_id, observation_start=FRED_START)
        if df is not None and not df.empty:
            out[a.name] = df["Close"]

    logger.info("History for %d/%d macro assets", len(out), len(ASSETS))
    return out


def collect_market(instruments: dict, aliases: dict) -> dict:
    """Macro side. Appends each asset's modal payload to `instruments`."""
    logger.info("Fetching market data...")
    history = fetch_market_history()
    metrics = process_all({k: v.to_frame("Close") for k, v in history.items()})
    logger.info("Market data loaded for %d assets", len(metrics))

    # The brief is anchored on the US close, so the S&P's last bar is the date
    # the prices actually describe. Using the build date instead would stamp a
    # Saturday or Sunday on it whenever the Friday job runs past midnight UTC,
    # which is most weeks. Crypto and FX trade through the weekend, so the
    # latest bar across all assets would not fix it either.
    anchor = history.get("S&P 500")
    as_at = anchor.index[-1] if anchor is not None and len(anchor) else None

    rows_by_name, sections = {}, []
    for category in SECTION_ORDER:
        rows = []
        for name, r in metrics[metrics["category"] == category].iterrows():
            is_rate, is_spread = bool(r["is_rate"]), bool(r["is_spread"])
            changes = [
                (_num(r["daily_chg"]), fmt_change(_num(r["daily_chg"]), is_rate, is_spread)),
                (_num(r["weekly_chg"]), fmt_change(_num(r["weekly_chg"]), is_rate, is_spread)),
                (_num(r["ltm_chg"]), fmt_change(_num(r["ltm_chg"]), is_rate, is_spread)),
            ]
            invert = bool(r["invert_color"])
            row = {
                "name": name,
                "value": fmt_value(_num(r["latest"]), is_rate, is_spread),
                "changes": changes,
                "invert": invert,
                "slug": slugify(name),
            }
            rows.append(row)
            rows_by_name[name] = row

            # Spreads are carried as percent and shown as bps, so the chart has
            # to be scaled the same way the table is.
            scale = 100.0 if is_spread else 1.0
            suffix = " bps" if is_spread else ("%" if is_rate else "")
            dp = 0 if is_spread else 2
            tf, default = build_timeframes(history.get(name), scale, dp)
            aliases[slugify(name)] = row["slug"]
            instruments[row["slug"]] = {
                "n": name,
                "m": f"{SECTION_LABELS.get(category, category)} · market overview",
                "p": row["value"],
                "sym": "", "suf": suffix, "dp": dp,
                "s": [["1 day", changes[0][1], tone(changes[0][0], invert)],
                      ["1 week", changes[1][1], tone(changes[1][0], invert)],
                      ["12 months", changes[2][1], tone(changes[2][0], invert)]],
                "tf": tf, "d": default,
            }

        if rows:
            sections.append({"title": SECTION_LABELS.get(category, category), "rows": rows})

    key_levels = [rows_by_name[n] for n in KEY_LEVELS if n in rows_by_name]
    return {"sections": sections, "key_levels": key_levels, "as_at": as_at}


def collect_watchlist(instruments: dict, aliases: dict) -> dict:
    """Holdings side. Appends each holding's modal payload to `instruments`."""
    tickers = [t for stocks in WATCHLIST.values() for _, t, _ in stocks]
    logger.info("Fetching watchlist data for %d names...", len(tickers))
    fetched, closes = fetch_watchlist(tickers, period="max")

    # Refreshed every build, so the brief reflects whatever has most recently
    # been reported without anyone editing a file. Never fatal: a company with
    # no earnings history simply has no figures block.
    earnings = fetch_earnings(tickers)

    groups, movers, reported, blank = [], [], [], 0
    for group, stocks in WATCHLIST.items():
        rows = []
        for name, ticker, currency in stocks:
            price, c1d, c1m, cltm, hi, lo = fetched[ticker]
            if price is None:
                blank += 1

            # Where the last price sits in the 52-week range, 0-1. Needs a full
            # year of history (fetch_watchlist returns hi/lo as None otherwise)
            # and a range wide enough to place a marker in.
            pos = None
            if None not in (price, hi, lo) and hi > lo:
                pos = min(max((price - lo) / (hi - lo), 0.0), 1.0)

            changes = [(c1d, fmt_pct(c1d)), (c1m, fmt_pct(c1m)), (cltm, fmt_pct(cltm))]
            row = {
                "name": name, "ticker": ticker, "currency": currency,
                "price": fmt_price(price, currency),
                "changes": changes,
                "hi": fmt_price(hi, currency), "lo": fmt_price(lo, currency),
                "pos": pos,
                # Element ids must survive tickers like BRK-B and 002594.SZ.
                "slug": slugify(ticker),
            }
            rows.append(row)
            if c1m is not None:
                movers.append({"name": name, "chg": c1m, "label": fmt_pct(c1m)})

            # Who reported since last week's brief. Built from the fetched
            # earnings rather than written by hand, so it cannot drift from
            # the figures in the modal it points at.
            er = earnings.get(ticker) or {}
            if er.get("on") and er.get("age") is not None \
                    and er["age"] <= REPORTED_WITHIN_DAYS:
                reported.append({
                    "name": name,
                    "slug": row["slug"],
                    "on": er["on"],
                    "when": _short_date(er["on"]),
                    "surp": er.get("surp"),
                    "age": er["age"],
                })

            stats = [["1 day", changes[0][1], tone(c1d)],
                     ["1 month", changes[1][1], tone(c1m)],
                     ["12 months", changes[2][1], tone(cltm)]]
            if pos is not None:
                stats += [["52-week low", row["lo"], ""], ["52-week high", row["hi"], ""]]

            tf, default = build_timeframes(closes.get(ticker))
            # Reachable as "Apple" or "AAPL"; the name loses to the ticker
            # only where a name is shared, e.g. SpaceX sits in both tables.
            aliases.setdefault(slugify(name), row["slug"])
            aliases[slugify(ticker)] = row["slug"]
            instruments[row["slug"]] = {
                "n": name,
                "m": f"{ticker} · {group} · quoted in {currency}",
                "p": row["price"],
                "sym": CURRENCY_SYMBOLS.get(currency, ""), "suf": "", "dp": 2,
                "s": stats, "tf": tf, "d": default,
                "er": earnings.get(ticker),
            }

        groups.append({"title": group, "rows": rows})

    if tickers and blank / len(tickers) > MAX_BLANK_SHARE:
        raise RuntimeError(
            f"{blank} of {len(tickers)} holdings came back with no price "
            f"({blank / len(tickers):.0%}, limit {MAX_BLANK_SHARE:.0%}). "
            "Yahoo is almost certainly rate-limiting this IP. Refusing to "
            "write a page this incomplete — rerun the job."
        )

    movers.sort(key=lambda m: m["chg"], reverse=True)
    top = movers[:MOVERS_PER_SIDE]
    bottom = [m for m in movers[-MOVERS_PER_SIDE:] if m not in top]
    reported.sort(key=lambda r: (-r["age"], r["name"]))   # earliest report first
    return {"groups": groups, "movers": top + list(reversed(bottom)),
            "reported": reported}


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


def _short_date(value: str) -> str:
    """"13 October 2026" -> "13 Oct", for the reported-this-week chips."""
    try:
        return datetime.strptime(value, "%d %B %Y").strftime("%d %b").lstrip("0")
    except (TypeError, ValueError):
        return value


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
  /* One row, always. auto-fit used to drop the last tile onto a second row
     the moment the tiles stopped fitting; --levels is the actual tile count,
     set on the element, so adding or removing a key level stays correct.
     minmax(0, 1fr) rather than 1fr so a long figure cannot widen its column. */
  grid-template-columns: repeat(var(--levels, 8), minmax(0, 1fr));
  gap: 1px;
  background: var(--border);
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
  box-shadow: var(--shadow);
}

.level {
  background: var(--surface);
  padding: 13px 10px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.level .label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: var(--ink-3);
}

.level .value {
  font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  /* Sized to the column, not the viewport: the page caps at 1120px, so a vw
     clamp resolves to its ceiling on any large monitor and overflows. Eight
     columns give ~134px, less 20px padding; "108,311.34" is the longest
     figure here and needs ~102px at this size. */
  font-size: 17px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  letter-spacing: -.02em;
  white-space: nowrap;
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

/* ---- Reported this week ---- */

/* A chip that opens its holding's modal. Same shape as a movers chip, with
   the affordance a button needs: the table rows carry one too. */
.chip.jump {
  font-family: inherit;
  color: inherit;
  cursor: pointer;
  transition: border-color .12s, background .12s;
}

.chip.jump:hover,
.chip.jump:focus-visible {
  border-color: var(--ink-3);
  background: var(--surface-alt);
}

.chip.jump:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

.chip .when {
  font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11px;
  color: var(--ink-3);
  font-variant-numeric: tabular-nums;
}

/* Always its own line under the chips rather than trailing whichever one
   happens to end the row, which reads as a stray fragment. */
.reported .hint {
  flex-basis: 100%;
  margin-top: 1px;
  font-size: 11px;
  color: var(--ink-3);
  font-style: italic;
}

/* ---- Weekly commentary ---- */

.commentary {
  background: var(--surface-alt);
  border: 1px solid var(--border);
  border-radius: 7px;
  padding: 17px 20px 19px;
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.commentary-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: var(--ink-3);
}

/* Set in the serif, against tables set in mono — the shift in voice is what
   marks this as written rather than measured. */
.commentary-body {
  font-family: Newsreader, ui-serif, Georgia, serif;
  /* Full box width. A measure cap looked half-empty against a box as wide as
     the tables; the extra leading below is what keeps the longer lines
     tracking, since the eye has further to travel back. */
  font-size: 17px;
  line-height: 1.72;
  color: var(--ink);
  display: flex;
  flex-direction: column;
  gap: 11px;
}

.commentary-body p { margin: 0; }

/* Justify the running prose only — the tables, labels and captions stay
   ranged left, where justification would simply stretch short strings.
   hyphens: auto matters more than usual here: the commentary box runs the
   full page width, and justified text that cannot break words opens rivers
   of white space between them. It needs a language, which .page declares. */
.commentary-body p,
.asset-note p,
.asset-earnings p {
  text-align: justify;
  -webkit-hyphens: auto;
  hyphens: auto;
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
  border-collapse: collapse;
  /* Fixed, with the widths declared below, so every section's columns land in
     the same place. Under auto layout each table sized its own columns to its
     own longest cell, so Credit Spreads and Equities stepped out of line with
     each other down the page. */
  table-layout: fixed;
}

/* Market Overview: Instrument | Level | 1D | 1W | LTM */
.t-macro { min-width: 780px; }
.t-macro th:nth-child(1), .t-macro td:nth-child(1) { width: 36%; }
.t-macro th:nth-child(n+2), .t-macro td:nth-child(n+2) { width: 16%; }

/* Stock Watchlist: Holding | Price | 1D | 1M | LTM | 52-Week Range */
.t-watch { min-width: 940px; }
.t-watch th:nth-child(1), .t-watch td:nth-child(1) { width: 26%; }
.t-watch th:nth-child(2), .t-watch td:nth-child(2) { width: 14%; }
.t-watch th:nth-child(n+3):nth-child(-n+5),
.t-watch td:nth-child(n+3):nth-child(-n+5) { width: 11%; }
.t-watch th:nth-child(6), .t-watch td:nth-child(6) { width: 27%; }

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

/* ---- Clickable rows ---- */

tr.clickable { cursor: pointer; }

tr.clickable:hover td,
tr.clickable:focus-visible td { background: var(--surface-alt); }

tr.clickable:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}

/* A quiet affordance — the table must still read as a table, not a toolbar. */
tr.clickable td.name::after {
  content: "›";
  color: var(--ink-3);
  margin-left: 6px;
  opacity: 0;
}

tr.clickable:hover td.name::after,
tr.clickable:focus-visible td.name::after { opacity: 1; }

/* ---- Detail dialog ---- */

#sheet {
  /* Wider than the original 680px: the earnings block now carries a four
     column table, and the chart reads better with the extra room. Still well
     inside the 1120px page so it does not fill a large screen edge to edge. */
  width: min(880px, calc(100vw - 32px));
  padding: 0;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
  color: var(--ink);
  box-shadow: 0 24px 64px -24px rgba(15, 23, 42, .55);
}

#sheet::backdrop { background: rgba(15, 23, 42, .55); }

.panel { padding: 22px 24px 24px; display: flex; flex-direction: column; gap: 18px; }

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  flex-wrap: wrap;
  /* The close button is absolutely positioned against the dialog and so takes
     no space in this row: it sits 14px from the dialog's right edge and is
     30px wide, while the panel's own padding stops 24px in. Without this the
     button lands on top of the price. Only the header row gives up the width;
     the chart below still runs edge to edge. */
  padding-right: 34px;
}

.panel-head h3 {
  margin: 0;
  font-family: Newsreader, ui-serif, Georgia, serif;
  font-size: 1.5rem;
  font-weight: 500;
}

.panel-sub { margin: 3px 0 0; font-size: 12px; color: var(--ink-2); }

.panel-price {
  font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 1.5rem;
  font-variant-numeric: tabular-nums;
  letter-spacing: -.02em;
}

/* ---- Timeframe buttons ---- */

.tfbar {
  display: flex;
  gap: 4px;
  padding: 3px;
  background: var(--surface-alt);
  border: 1px solid var(--border);
  border-radius: 7px;
  align-self: flex-start;
  flex-wrap: wrap;
}

.tf {
  appearance: none;
  border: 1px solid transparent;
  background: transparent;
  color: var(--ink-2);
  font: 500 12px/1 "IBM Plex Sans", ui-sans-serif, system-ui, sans-serif;
  letter-spacing: .04em;
  padding: 7px 13px;
  border-radius: 5px;
  cursor: pointer;
  font-variant-numeric: tabular-nums;
}

.tf:hover { color: var(--ink); background: var(--surface); }

.tf.on {
  background: var(--surface);
  border-color: var(--border);
  color: var(--ink);
  box-shadow: 0 1px 2px rgba(15, 23, 42, .08);
}

.tf:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }

/* ---- Chart ---- */

.chart-wrap { margin: 0; display: flex; flex-direction: column; gap: 7px; }

/* The hidden attribute loses to any author rule that sets display, and the
   three elements below all set display: flex. Without this they are never
   actually hidden — an empty hovercard parks on every chart and an empty
   note leaves a stray rule under the stats. */
#sheet-hover[hidden],
#sheet-note[hidden],
#sheet-earnings[hidden],
#sheet-news[hidden] { display: none; }

.chart-plot { position: relative; }

#sheet-chart { width: 100%; height: 180px; display: block; overflow: visible; }

/* ---- Hover readout ---- */

.chart-cursor { stroke: var(--ink-3); stroke-width: 1; stroke-dasharray: 2 3; }
.chart-dot { fill: var(--surface); stroke: var(--trace); stroke-width: 2; }

.hovercard {
  position: absolute;
  top: 0;
  /* Centred on the cursor by script, which also keeps it inside the plot. */
  transform: translateX(-50%);
  pointer-events: none;
  background: var(--ink);
  color: var(--surface);
  border-radius: 5px;
  padding: 5px 9px;
  font-size: 11.5px;
  line-height: 1.45;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 14px -6px rgba(15, 23, 42, .6);
}

.hover-date { color: var(--ink-3); font-size: 10px; letter-spacing: .04em; text-transform: uppercase; }

.hover-price {
  font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 13px;
}

/* ---- Per-asset commentary and news ---- */

.asset-note {
  font-family: Newsreader, ui-serif, Georgia, serif;
  font-size: 15.5px;
  line-height: 1.68;
  color: var(--ink);
  border-top: 1px solid var(--border);
  padding-top: 15px;
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.asset-note p { margin: 0; }

.asset-earnings {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-top: 1px solid var(--border);
  padding-top: 15px;
}

.asset-earnings .earnings-label,
.asset-news .news-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: var(--ink-3);
}

/* Fetched figures: set apart from the written note above them, because one
   refreshes every build and the other does not. */
.earnings-meta {
  margin: 0;
  font-size: 11.5px;
  color: var(--ink-3);
  font-variant-numeric: tabular-nums;
}

/* A report well past any normal reporting cycle is the case worth seeing. */
.earnings-meta.stale { color: var(--neg); font-weight: 600; }

.earnings-facts {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 11px 13px;
  background: var(--surface-alt);
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 12.5px;
  font-variant-numeric: tabular-nums;
}

.ef-row { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }

.ef-k {
  flex: none;
  min-width: 142px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: .07em;
  text-transform: uppercase;
  color: var(--ink-3);
}

.ef-v {
  font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  color: var(--ink);
}

.ef-row b { font-weight: 500; font-family: "IBM Plex Mono", ui-monospace, Menlo, monospace; }

/* Quarter against the same quarter a year earlier — the comparison that says
   whether the business grew, which a surprise against consensus does not. */
.earnings-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: auto;
  font-variant-numeric: tabular-nums;
}

.earnings-table th {
  font-size: 10px;
  letter-spacing: .07em;
  text-transform: uppercase;
  color: var(--ink-3);
  text-align: right;
  padding: 6px 10px;
  border-bottom: 1px solid var(--rule);
  white-space: nowrap;
}

.earnings-table th:first-child { text-align: left; }

.earnings-table td {
  padding: 7px 10px;
  text-align: right;
  border-bottom: 1px solid var(--border);
  font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12.5px;
  white-space: nowrap;
}

.earnings-table td:first-child {
  text-align: left;
  font-family: "IBM Plex Sans", ui-sans-serif, system-ui, sans-serif;
  color: var(--ink-2);
}

.earnings-table tr:last-child td { border-bottom: 0; }

.earnings-basis {
  margin: 0;
  font-size: 11px;
  line-height: 1.5;
  color: var(--ink-3);
  font-family: "IBM Plex Sans", ui-sans-serif, system-ui, sans-serif;
}

.earnings-next {
  margin: 0;
  font-size: 11.5px;
  color: var(--ink-3);
  font-family: "IBM Plex Sans", ui-sans-serif, system-ui, sans-serif;
}

.asset-earnings p {
  margin: 0;
  font-family: Newsreader, ui-serif, Georgia, serif;
  font-size: 15.5px;
  line-height: 1.68;
  color: var(--ink);
}

.asset-news {
  display: flex;
  flex-direction: column;
  gap: 0;
  border-top: 1px solid var(--border);
  padding-top: 15px;
}

.asset-news .news-label { margin-bottom: 9px; }

.news-item {
  display: flex;
  gap: 12px;
  align-items: baseline;
  padding: 8px 0;
  border-top: 1px solid var(--border);
}

.news-item:first-of-type { border-top: 0; }

/* The date is the point of this list: it is how you tell a piece written
   this week from one carried over because the week was quiet. */
.news-date {
  flex: none;
  font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11px;
  color: var(--ink-3);
  font-variant-numeric: tabular-nums;
  min-width: 68px;
}

.news-title { font-size: 13.5px; line-height: 1.45; color: var(--ink); text-decoration: none; }
a.news-title:hover { color: var(--accent); text-decoration: underline; }
a.news-title:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 2px; }

.news-stale { color: var(--ink-3); font-size: 11px; font-style: italic; }

.chart-axis {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 11px;
  color: var(--ink-3);
  font-variant-numeric: tabular-nums;
}

/* Direction is the chart's only colour, and it carries meaning, so it comes
   from the same pos/neg tokens the change columns use. */
#sheet-chart.up   { --trace: var(--pos); }
#sheet-chart.down { --trace: var(--neg); }

.chart-line { fill: none; stroke: var(--trace); stroke-width: 1.75; vector-effect: non-scaling-stroke; }
.chart-area { fill: var(--trace); opacity: .10; stroke: none; }
.chart-end  { fill: var(--trace); }

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(96px, 1fr));
  gap: 1px;
  background: var(--border);
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
}

.stat { background: var(--surface); padding: 10px 12px; display: flex; flex-direction: column; gap: 2px; }

.stat .k {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: .07em;
  text-transform: uppercase;
  color: var(--ink-3);
}

.stat .v {
  font-family: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 14px;
  font-variant-numeric: tabular-nums;
}

#sheet-close {
  position: absolute;
  top: 12px;
  right: 14px;
  width: 30px;
  height: 30px;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: var(--surface);
  color: var(--ink-2);
  font-size: 15px;
  line-height: 1;
  cursor: pointer;
}

#sheet-close:hover { background: var(--surface-alt); color: var(--ink); }
#sheet-close:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

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

@media (max-width: 880px) {
  /* Four columns leave room for the full-size figure again. */
  .levels { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .level .value { font-size: 19px; }
}

@media (max-width: 460px) {
  .levels { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 600px) {
  .page { padding: 20px 14px 48px; gap: 26px; }
  th, td { padding-left: 12px; padding-right: 12px; }
}
"""

# Raw string: the JS carries regex escapes like /\n\s*\n/, which a plain
# triple-quote would turn into real newlines and silently break. The %d slots
# are the chart geometry and are unaffected by raw.
#
# Kept out of the page template because that is an f-string and this is full
# of braces. <dialog> is doing the real work — modality, Esc and focus return
# are the browser's job, not ours.
SCRIPT = r"""
(function () {
  var D = JSON.parse(document.getElementById('brief-data').textContent);
  var sheet = document.getElementById('sheet');
  if (!sheet || !sheet.showModal) return;   // no <dialog>: rows stay inert

  var W = __W__, H = __H__, PAD = __PAD__;
  var svg = document.getElementById('sheet-chart');
  var NS = 'http://www.w3.org/2000/svg';
  var current = null, frame = null;

  function fmt(v, inst) {
    var a = Math.abs(v);
    var dp = Math.min(inst.dp, a >= 10000 ? 0 : (a >= 100 ? 1 : inst.dp));
    return inst.sym + v.toLocaleString('en-GB', {
      minimumFractionDigits: dp, maximumFractionDigits: dp
    }) + inst.suf;
  }

  var MONTHS = ['Jan','Feb','Mar','Apr','May','Jun',
                'Jul','Aug','Sep','Oct','Nov','Dec'];

  function dateAt(win, i) {
    // Parsed as UTC and read back as UTC, so a timezone west of Greenwich
    // cannot shift every label back by a day.
    var d = new Date(win.t + 'T00:00:00Z');
    d.setUTCDate(d.getUTCDate() + win.o[i]);
    return d;
  }

  function dayLabel(d) {
    return ('0' + d.getUTCDate()).slice(-2) + ' ' + MONTHS[d.getUTCMonth()] +
           ' ' + d.getUTCFullYear();
  }

  function monthLabel(d) { return MONTHS[d.getUTCMonth()] + ' ' + d.getUTCFullYear(); }

  function el(name, attrs) {
    var n = document.createElementNS(NS, name);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  }

  function draw(inst, key) {
    var win = inst.tf[key];
    svg.textContent = '';
    if (!win) return;

    var v = win.v, lo = Math.min.apply(null, v), hi = Math.max.apply(null, v);
    var span = hi - lo, usable = H - 2 * PAD, step = W / (v.length - 1);

    var pts = v.map(function (y, i) {
      // A dead-flat series would divide by zero; park it on the centre line.
      var py = span === 0 ? PAD + usable / 2 : PAD + (hi - y) / span * usable;
      return [i * step, py];
    });

    var line = 'M' + pts.map(function (p) {
      return p[0].toFixed(1) + ',' + p[1].toFixed(1);
    }).join(' L');

    svg.setAttribute('class', v[v.length - 1] >= v[0] ? 'up' : 'down');
    svg.appendChild(el('path', {d: line + ' L' + W + ',' + H + ' L0,' + H + ' Z',
                                'class': 'chart-area'}));
    svg.appendChild(el('path', {d: line, 'class': 'chart-line'}));
    svg.appendChild(el('circle', {cx: pts[pts.length - 1][0].toFixed(1),
                                  cy: pts[pts.length - 1][1].toFixed(1),
                                  r: 4, 'class': 'chart-end'}));

    document.getElementById('sheet-from').textContent =
      monthLabel(dateAt(win, 0)) + '  ·  low ' + fmt(lo, inst);
    document.getElementById('sheet-to').textContent =
      'high ' + fmt(hi, inst) + '  ·  ' + monthLabel(dateAt(win, v.length - 1));

    // Hover state belongs to the window just drawn, not the one before it.
    plot = {win: win, inst: inst, pts: pts};
    hideHover();

    Array.prototype.forEach.call(document.querySelectorAll('.tf'), function (b) {
      var on = b.dataset.tf === key;
      b.classList.toggle('on', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
  }

  var hover = document.getElementById('sheet-hover');
  var plot = null;

  function hideHover() {
    hover.hidden = true;
    var old = svg.querySelector('.chart-cursor');
    if (old) old.remove();
    old = svg.querySelector('.chart-dot');
    if (old) old.remove();
  }

  function showHover(clientX) {
    if (!plot) return;
    var box = svg.getBoundingClientRect();
    if (!box.width) return;

    // Nearest point to the cursor, in the SVG's own coordinate space.
    var x = (clientX - box.left) / box.width * W;
    var i = Math.round(x / (W / (plot.pts.length - 1)));
    i = Math.max(0, Math.min(plot.pts.length - 1, i));

    var p = plot.pts[i];
    hideHover();
    svg.appendChild(el('line', {x1: p[0], y1: 0, x2: p[0], y2: H, 'class': 'chart-cursor'}));
    svg.appendChild(el('circle', {cx: p[0], cy: p[1], r: 4, 'class': 'chart-dot'}));

    hover.querySelector('.hover-date').textContent = dayLabel(dateAt(plot.win, i));
    hover.querySelector('.hover-price').textContent = fmt(plot.win.v[i], plot.inst);
    hover.hidden = false;

    // Keep the card inside the plot rather than letting it hang off an edge.
    var left = p[0] / W * box.width;
    var half = hover.offsetWidth / 2;
    hover.style.left = Math.max(half, Math.min(box.width - half, left)) + 'px';
  }

  svg.addEventListener('mousemove', function (e) { showHover(e.clientX); });
  svg.addEventListener('mouseleave', hideHover);
  svg.addEventListener('touchmove', function (e) {
    if (e.touches.length) { e.preventDefault(); showHover(e.touches[0].clientX); }
  }, {passive: false});
  svg.addEventListener('touchend', hideHover);

  function renderNote(inst) {
    var note = document.getElementById('sheet-note');
    note.textContent = '';
    note.hidden = !inst.c;
    if (!inst.c) return;
    inst.c.split(/\n\s*\n/).forEach(function (para) {
      var p = document.createElement('p');
      p.textContent = para.trim();     // text, never markup
      note.appendChild(p);
    });
  }

  function renderEarnings(inst) {
    var box = document.getElementById('sheet-earnings');
    box.textContent = '';
    var er = inst.er;
    box.hidden = !inst.e && !er;
    if (box.hidden) return;

    var label = document.createElement('span');
    label.className = 'earnings-label';
    label.textContent = 'Most recent earnings report';
    box.appendChild(label);

    // Fetched figures first: these refresh on every build, so they are the
    // part that stays current between hand-written notes.
    if (er && er.on) {
      var meta = document.createElement('p');
      meta.className = 'earnings-meta';
      var when = 'Reported ' + er.on;
      if (er.age != null) when += '  \u00b7  ' + er.age + ' days ago';
      if (er.fin) when += '  \u00b7  quarter ended ' + er.fin.end;
      meta.textContent = when;
      if (er.age != null && er.age > 200) meta.classList.add('stale');
      box.appendChild(meta);

      var facts = document.createElement('div');
      facts.className = 'earnings-facts';

      function line(label, value, pct) {
        var row = document.createElement('div');
        row.className = 'ef-row';
        var k = document.createElement('span');
        k.className = 'ef-k'; k.textContent = label; row.appendChild(k);
        var v = document.createElement('span');
        v.className = 'ef-v'; v.textContent = value; row.appendChild(v);
        if (pct != null) {
          var b = document.createElement('b');
          b.className = pct >= 0 ? 'pos' : 'neg';
          b.textContent = (pct >= 0 ? '+' : '') + pct + '%';
          row.appendChild(b);
        }
        facts.appendChild(row);
      }

      line('Against consensus',
           er.est != null ? er.eps + ' against ' + er.est + ' expected' : 'EPS ' + er.eps,
           er.surp);
      if (er.py != null) line('Versus a year earlier', er.eps + ' against ' + er.py, er.yoy);
      if (er.beats != null) {
        line('Track record',
             'Above consensus in ' + er.beats + ' of last ' + er.of +
             ', average ' + (er.avg >= 0 ? '+' : '') + er.avg + '%', null);
      }
      box.appendChild(facts);

      if (er.fin && er.fin.rows.length) {
        var tbl = document.createElement('table');
        tbl.className = 'earnings-table';
        var head = document.createElement('tr');
        ['Metric', 'Actual', 'Year earlier', 'Change'].forEach(function (t) {
          var th = document.createElement('th'); th.textContent = t; head.appendChild(th);
        });
        tbl.appendChild(head);
        er.fin.rows.forEach(function (r) {
          var tr = document.createElement('tr');
          r.forEach(function (cell, i) {
            var td = document.createElement('td');
            td.textContent = cell;
            if (i === 3 && cell !== '\u2014') td.className = cell.charAt(0) === '-' ? 'neg' : 'pos';
            tr.appendChild(td);
          });
          tbl.appendChild(tr);
        });
        box.appendChild(tbl);

        // The consensus line and the filed diluted figure are different
        // measures. Where they diverge materially, say so rather than leave a
        // reader to assume one of them is wrong.
        var filed = null;
        er.fin.rows.forEach(function (r) {
          if (r[0] === 'Diluted EPS') filed = parseFloat(r[1].replace(/,/g, ''));
        });
        if (filed != null && er.eps && Math.abs(filed - er.eps) / Math.abs(er.eps) > 0.2) {
          var note = document.createElement('p');
          note.className = 'earnings-basis';
          note.textContent = 'Consensus is compared on an adjusted basis (' + er.eps +
            '); the diluted figure above (' + filed.toFixed(2) + ') is as filed. ' +
            'They are different measures, not a discrepancy.';
          box.appendChild(note);
        }
      }
    }

    if (er && er.next) {
      var nxt = document.createElement('p');
      nxt.className = 'earnings-next';
      nxt.textContent = 'Next report expected ' + er.next + '.';
      box.appendChild(nxt);
    }

    if (inst.e) {
      inst.e.split(/\n\s*\n/).forEach(function (para) {
        var p = document.createElement('p');
        p.textContent = para.trim();     // text, never markup
        box.appendChild(p);
      });
    }
  }

  function renderNews(inst) {
    var box = document.getElementById('sheet-news');
    box.textContent = '';
    var items = inst.news || [];
    box.hidden = !items.length;
    if (!items.length) return;

    var label = document.createElement('span');
    label.className = 'news-label';
    label.textContent = 'In the news';
    box.appendChild(label);

    items.forEach(function (n) {
      var row = document.createElement('div');
      row.className = 'news-item';

      var date = document.createElement('span');
      date.className = 'news-date';
      date.textContent = n.d;
      row.appendChild(date);

      var title = document.createElement(n.u ? 'a' : 'span');
      title.className = 'news-title';
      title.textContent = n.t;
      if (n.u) { title.href = n.u; title.target = '_blank'; title.rel = 'noopener noreferrer'; }
      row.appendChild(title);

      box.appendChild(row);
    });
  }

  function open(id) {
    var inst = D[id];
    if (!inst) return;
    current = inst;

    document.getElementById('sheet-name').textContent = inst.n;
    document.getElementById('sheet-meta').textContent = inst.m;
    document.getElementById('sheet-price').textContent = inst.p;

    document.getElementById('sheet-stats').innerHTML = inst.s.map(function (st) {
      return '<div class="stat"><span class="k"></span><span class="v ' + st[2] +
             '"></span></div>';
    }).join('');
    // Values are written as text, never parsed as markup.
    Array.prototype.forEach.call(document.querySelectorAll('#sheet-stats .stat'),
      function (d, i) {
        d.querySelector('.k').textContent = inst.s[i][0];
        d.querySelector('.v').textContent = inst.s[i][1];
      });

    var bar = document.getElementById('sheet-tfs');
    bar.textContent = '';
    Object.keys(inst.tf).forEach(function (k) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'tf';
      b.dataset.tf = k;
      b.textContent = k;
      b.addEventListener('click', function () { draw(current, k); });
      bar.appendChild(b);
    });

    renderNote(inst);
    renderEarnings(inst);
    renderNews(inst);

    if (inst.d) draw(inst, inst.d);
    sheet.showModal();
  }

  Array.prototype.forEach.call(document.querySelectorAll('tr.clickable'), function (row) {
    row.addEventListener('click', function () { open(row.dataset.id); });
    row.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(row.dataset.id); }
    });
  });

  // The reported-this-week chips point at the same payloads. They are real
  // buttons, so Enter and Space come free and need no key handler.
  Array.prototype.forEach.call(document.querySelectorAll('.jump'), function (el) {
    el.addEventListener('click', function () { open(el.dataset.id); });
  });

  document.getElementById('sheet-close')
          .addEventListener('click', function () { sheet.close(); });

  // Click outside the panel closes it. The dialog fills the backdrop, so
  // compare against its box rather than looking at the event target.
  sheet.addEventListener('close', hideHover);

  sheet.addEventListener('click', function (e) {
    var b = sheet.getBoundingClientRect();
    if (e.clientX < b.left || e.clientX > b.right ||
        e.clientY < b.top  || e.clientY > b.bottom) sheet.close();
  });

  // Redraw on resize so the line keeps its aspect; viewBox handles the rest.
  window.addEventListener('resize', function () {
    if (!current || !sheet.open) return;
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(function () {
      var on = document.querySelector('.tf.on');
      if (on) draw(current, on.dataset.tf);
    });
  });
}());
"""

# Token substitution rather than %-formatting: the script contains literal
# per-cent signs (the earnings surprise, for one) and every one of them would
# have to be escaped. Tokens cannot collide with JavaScript syntax.
SCRIPT = (SCRIPT.replace("__W__", str(CHART_W))
                .replace("__H__", str(CHART_H))
                .replace("__PAD__", str(CHART_PAD)))

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
        f'<tr class="clickable" tabindex="0" role="button" data-id="{r["slug"]}" '
        f'aria-label="Chart for {esc(r["name"])}">'
        f'<td class="name">{esc(r["name"])}</td>'
        f'<td class="level-val">{esc(r["value"])}</td>'
        f'{change_cells(r["changes"], r["invert"])}'
        "</tr>"
        for r in section["rows"]
    )
    return (
        '<div class="block">'
        f'<h3>{esc(section["title"])}</h3>'
        '<div class="scroll"><table class="t-macro">'
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


def render_reported(reported: list) -> str:
    """The "reported this week" strip above the watchlist tables.

    Each chip opens the same modal as its table row, so a reader can go from
    "who reported" straight to the figures without hunting for the line.
    Generated from the fetched earnings, never hand-written.
    """
    if not reported:
        return ""
    chips = "".join(
        f'<button type="button" class="chip jump" data-id="{esc(r["slug"])}" '
        f'title="Reported {esc(r["on"])} — open the figures">'
        f'{esc(r["name"])}<span class="when">{esc(r["when"])}</span>'
        + (f'<b class="{tone(r["surp"])}">{fmt_pct(r["surp"])}</b>'
           if r.get("surp") is not None else "")
        + "</button>"
        for r in reported
    )
    return (
        '<div class="movers reported">'
        '<span class="caption">Reported this week</span>'
        f'{chips}'
        '<span class="hint">versus consensus · select for detail</span>'
        "</div>"
    )


def render_watchlist_group(group: dict) -> str:
    rows = "".join(
        f'<tr class="clickable" tabindex="0" role="button" data-id="{r["slug"]}" '
        f'aria-label="Chart for {esc(r["name"])}">'
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
        '<div class="scroll"><table class="t-watch">'
        "<thead><tr><th>Holding</th><th>Price</th><th>1D</th><th>1M</th><th>LTM</th>"
        "<th>52-Week Range</th></tr></thead>"
        f"<tbody>{rows}</tbody>"
        "</table></div></div>"
    )


def render_html(market: dict, watch: dict, instruments: dict,
                commentary: dict, now: datetime) -> str:
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
    reported_block = render_reported(watch.get("reported", []))

    n_holdings = sum(len(g["rows"]) for g in watch["groups"])

    # Embedded as a JSON script block rather than a JS literal so the series
    # never have to survive escaping into executable source.
    data_json = json.dumps(instruments, separators=(",", ":"))

    as_at = market.get("as_at")
    as_at_line = (
        f'Prices as at the close of {as_at.strftime("%A, %d %B %Y")}'
        if as_at is not None else "Point-in-time snapshot"
    )

    return f"""<title>Secco Weekly Market Brief</title>
{FONTS}
<style>{CSS}</style>

<div class="page" lang="en-GB">

  <header class="masthead">
    <span class="eyebrow">Secco Capital</span>
    <h1>Weekly Market Brief</h1>
    <div class="standfirst">
      <span>{as_at_line}</span>
      <span class="sep">·</span>
      <span>Rebuilt every Friday after the New York close</span>
    </div>
  </header>

  <div class="levels" style="--levels:{len(market["key_levels"])}">{levels}</div>

  <section>
    <div class="section-head">
      <h2>Market Overview</h2>
      <span class="note">Select any row for its price history. Rates and spreads
        move in absolute terms; everything else in per cent.</span>
    </div>
    <!--commentary:market-->{render_commentary(commentary.get("Market Overview"))}<!--/commentary:market-->
    {"".join(render_market_section(s) for s in market["sections"])}
  </section>

  <section>
    <div class="section-head">
      <h2>Stock Watchlist</h2>
      <span class="note">{n_holdings} holdings · priced in the listing currency</span>
    </div>
    <!--commentary:watchlist-->{render_commentary(commentary.get("Stock Watchlist"))}<!--/commentary:watchlist-->
    {reported_block}
    {movers_block}
    {"".join(render_watchlist_group(g) for g in watch["groups"])}
  </section>

  <dialog id="sheet" aria-labelledby="sheet-name">
    <button id="sheet-close" type="button" aria-label="Close">&#215;</button>
    <div class="panel">
      <div class="panel-head">
        <div>
          <h3 id="sheet-name"></h3>
          <p class="panel-sub" id="sheet-meta"></p>
        </div>
        <div class="panel-price" id="sheet-price"></div>
      </div>
      <div class="tfbar" id="sheet-tfs" role="group" aria-label="Chart timeframe"></div>
      <figure class="chart-wrap">
        <div class="chart-plot">
          <svg id="sheet-chart" viewBox="0 0 {CHART_W} {CHART_H}"
               preserveAspectRatio="none" role="img" aria-label="Price history"></svg>
          <div class="hovercard" id="sheet-hover" hidden aria-hidden="true">
            <span class="hover-date"></span><span class="hover-price"></span>
          </div>
        </div>
        <figcaption class="chart-axis">
          <span id="sheet-from"></span><span id="sheet-to"></span>
        </figcaption>
      </figure>
      <div class="stats" id="sheet-stats"></div>
      <div class="asset-note" id="sheet-note" hidden></div>
      <div class="asset-earnings" id="sheet-earnings" hidden></div>
      <div class="asset-news" id="sheet-news" hidden></div>
    </div>
  </dialog>

  <script id="brief-data" type="application/json">{data_json}</script>

  <footer>
    <span>Point-in-time snapshot built {now.astimezone().strftime("%d %B %Y at %H:%M %Z")}.
          Sources: Yahoo Finance (prices), FRED (rates and credit spreads).</span>
    <span>Secco Capital · Confidential · Not investment advice.</span>
  </footer>

</div>

<script>{SCRIPT}</script>
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build(out_path: str) -> str:
    instruments, aliases = {}, {}
    market = collect_market(instruments, aliases)
    watch = collect_watchlist(instruments, aliases)
    attach_asset_notes(instruments, aliases, read_asset_notes())
    page = render_html(market, watch, instruments, read_commentary(), datetime.now())

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
    try:
        main()
    except RuntimeError as exc:
        # An incomplete fetch is operational, not a bug — a traceback buries
        # the one line saying why nothing was written.
        sys.exit(f"ERROR: {exc}")
