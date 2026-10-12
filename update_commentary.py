"""
update_commentary.py — Put this week's hand-written commentary into the brief.

Rewrites just the two commentary boxes in the already-built pages. No market
data is refetched, so every figure stays as at Friday's close and this runs in
about a second rather than the three minutes a rebuild costs.

Usage:
    python update_commentary.py              # weekly/weekly_brief.html + the
                                             # newest dated copy in archive/
    python update_commentary.py a.html b.html   # or name the pages yourself

Edit weekly/commentary.md first — it is gitignored and local to you; the
blank form is weekly/commentary.template.md. A section left empty removes its
box rather than printing an empty one.
"""

import argparse
import glob
import json
import logging
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_report_html import (
    COMMENTARY_SECTIONS, read_asset_notes, read_commentary, render_commentary, slugify,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

CANONICAL = "weekly/weekly_brief.html"
COMMENTARY = "weekly/commentary.md"
TEMPLATE = "weekly/commentary.template.md"
ASSETS = "weekly/assets.md"
ASSETS_TEMPLATE = "weekly/assets.template.md"
ARCHIVE_GLOB = "weekly/archive/secco-market-brief-*.html"

# Marker name in the page -> heading in commentary.md
SLOTS = {"market": "Market Overview", "watchlist": "Stock Watchlist"}


def default_targets() -> list[str]:
    """The canonical page plus the newest dated copy — the one you send."""
    targets = [p for p in (CANONICAL,) if os.path.exists(p)]
    archive = sorted(glob.glob(ARCHIVE_GLOB))
    if archive:
        targets.append(archive[-1])
    return targets


DATA_BLOCK = re.compile(
    r'(<script id="brief-data" type="application/json">)(.*?)(</script>)', re.S)


def patch_assets(page: str, notes: dict, path: str) -> str:
    """Rewrite the per-asset notes inside the page's embedded JSON.

    The modal reads commentary and news from that payload, so unlike the two
    section boxes there is no markup to swap — the data itself is edited and
    re-serialised. Aliases are rebuilt from the payload rather than stored,
    so a heading can be a name or a ticker exactly as it can at build time.
    """
    m = DATA_BLOCK.search(page)
    if not m:
        logger.warning("%s has no embedded data block — asset notes skipped.", path)
        return page

    data = json.loads(m.group(2))

    aliases = {}
    for key, inst in data.items():
        aliases[key] = key
        aliases.setdefault(slugify(inst["n"]), key)
        ticker = inst.get("m", "").split(" · ")[0]
        if ticker:
            aliases.setdefault(slugify(ticker), key)

    # Clear last week's notes first, or an asset dropped from the file keeps
    # the commentary it had.
    for inst in data.values():
        inst.pop("c", None)
        inst.pop("news", None)

    unmatched = []
    for key, note in notes.items():
        target = aliases.get(key)
        if not target:
            unmatched.append(key)
            continue
        if note["c"]:
            data[target]["c"] = note["c"]
        if note["news"]:
            data[target]["news"] = note["news"]

    if unmatched:
        logger.warning("Asset notes matched nothing: %s", ", ".join(sorted(unmatched)))

    body = json.dumps(data, separators=(",", ":"))
    return DATA_BLOCK.sub(lambda mm: mm.group(1) + body + mm.group(3), page, count=1)


def patch(path: str, commentary: dict, notes: dict) -> bool:
    with open(path, encoding="utf-8") as f:
        page = f.read()

    original = page
    for slot, heading in SLOTS.items():
        marker = re.compile(f"(<!--commentary:{slot}-->).*?(<!--/commentary:{slot}-->)", re.S)
        if not marker.search(page):
            logger.error("%s has no '%s' commentary marker — rebuild it with "
                         "build_report_html.py before patching.", path, slot)
            return False
        # A lambda, not a replacement string: commentary text containing a
        # backslash or \\1 would otherwise be read as a group reference.
        body = render_commentary(commentary.get(heading))
        page = marker.sub(lambda m: m.group(1) + body + m.group(2), page, count=1)

    page = patch_assets(page, notes, path)

    if page == original:
        logger.info("%s already up to date.", path)
        return True

    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    logger.info("Updated %s", path)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pages", nargs="*", help="Pages to patch (default: the latest brief)")
    args = ap.parse_args()

    # The working copy is gitignored, so a fresh clone has only the template.
    created = []
    for working, template in ((COMMENTARY, TEMPLATE), (ASSETS, ASSETS_TEMPLATE)):
        if not os.path.exists(working) and os.path.exists(template):
            shutil.copy(template, working)
            created.append(working)
    if created:
        sys.exit(f"Created {' and '.join(created)} from the template(s). "
                 f"Write this week's commentary in, then run this again.")

    commentary = read_commentary()
    notes = read_asset_notes()
    written = [s for s in COMMENTARY_SECTIONS if s in commentary]
    if not written and not notes:
        sys.exit(
            f"Nothing written in {COMMENTARY} or {ASSETS} — fill in a section "
            "under '## Market Overview' or '## Stock Watchlist', or an asset "
            "under a '### ' heading, first."
        )

    # Printed back so last week's prose on this week's numbers is caught here,
    # rather than by a principal reading it.
    print("\nWriting into the brief:\n")
    for heading in COMMENTARY_SECTIONS:
        body = commentary.get(heading)
        preview = (body[:150] + "...") if body and len(body) > 150 else (body or "(none)")
        print(f"  {heading}\n    {preview}\n")

    targets = args.pages or default_targets()
    if not targets:
        sys.exit(f"No pages found. Expected {CANONICAL} — build it first.")

    if notes:
        print(f"  Per-asset notes: {len(notes)} asset(s)\n")

    ok = all([patch(p, commentary, notes) for p in targets])
    skipped = [s for s in COMMENTARY_SECTIONS if s not in commentary]
    if skipped:
        logger.warning("No box added for: %s", ", ".join(skipped))
    print(f"\n{'✓' if ok else '✗'} {len(written)} of {len(COMMENTARY_SECTIONS)} "
          f"section(s) written into {len(targets)} page(s).\n")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
