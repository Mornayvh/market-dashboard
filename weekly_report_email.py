"""
weekly_report_email.py — Emails the weekly dashboard report via Resend.

Builds the Market Dashboard and Stock Watchlist PDFs (no Streamlit server
needed — both pull data through the src/ ingest layer, exactly like the
standalone export scripts), asks Claude for a short note on what drove markets
this week, and sends the lot as one email with both PDFs attached.

Usage:
    python weekly_report_email.py            # build, generate note, send
    python weekly_report_email.py --dry-run  # build and print, send nothing

Environment:
    RESEND_API_KEY      required — Resend API key
    EMAIL_RECIPIENTS    required — comma-separated recipients
    EMAIL_FROM          optional — sender, default "Secco Capital <reports@seccocapital.com>"
                                   (the domain must be verified in Resend)
    ANTHROPIC_API_KEY   optional — enables the weekly note; without it the
                                   report still sends, just without commentary
    FRED_API_KEY        optional — rates and spreads on the market PDF

Scheduled by .github/workflows/weekly_report.yml (Fridays after the US close).
"""

import argparse
import base64
import logging
import os
import sys
from datetime import datetime

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Both exporters expose build_pdf(out_path); alias to disambiguate.
from export_pdf import build_pdf as build_market_pdf
from export_watchlist_pdf import build_pdf as build_watchlist_pdf
from src.weekly_note import generate_weekly_note

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_FROM = "Secco Capital <reports@seccocapital.com>"
RESEND_MAX_TOTAL_MB = 40  # Resend's per-message ceiling, attachments included


# ---------------------------------------------------------------------------
# Email body
# ---------------------------------------------------------------------------

def _note_html(note: str | None, sources: list[tuple[str, str]]) -> str:
    """The commentary block. Renders nothing at all when there is no note, so
    the email degrades to a clean PDFs-only report."""
    if not note:
        return ""

    paragraphs = "".join(
        f'<p style="margin:0 0 0.7rem 0;">{p.strip()}</p>'
        for p in note.split("\n\n") if p.strip()
    )

    sources_html = ""
    if sources:
        items = "".join(
            f'<li style="margin-bottom:3px;">'
            f'<a href="{url}" style="color:#4F7FD6; text-decoration:none;">{title}</a></li>'
            for title, url in sources[:8]
        )
        sources_html = (
            '<div style="margin-top:14px; padding-top:10px; border-top:1px solid #E2E8F0;">'
            '<div style="font-family:\'Courier New\',monospace; font-size:10px; '
            'text-transform:uppercase; letter-spacing:0.1em; color:#94A3B8; '
            'margin-bottom:6px;">Sources</div>'
            f'<ul style="margin:0; padding-left:16px; font-size:11px; color:#64748B;">{items}</ul>'
            "</div>"
        )

    return f"""
    <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px;
         padding:16px 18px; margin-bottom:22px;">
      <div style="font-family:'Courier New',monospace; font-size:10px; font-weight:700;
           text-transform:uppercase; letter-spacing:0.1em; color:#64748B;
           padding-bottom:8px; margin-bottom:10px; border-bottom:1px solid #E2E8F0;">
        The Week in Markets
      </div>
      <div style="font-size:13.5px; line-height:1.65; color:#1E293B;">{paragraphs}</div>
      {sources_html}
    </div>"""


def build_html(date_str: str, note: str | None, sources: list[tuple[str, str]]) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0; padding:0; background:#F1F5F9;">
  <div style="max-width:680px; margin:20px auto; background:#FFFFFF;
       border:1px solid #E2E8F0; border-radius:8px; overflow:hidden;
       font-family:Arial,Helvetica,sans-serif;">

    <div style="background:#1E293B; padding:20px 24px;">
      <div style="font-size:18px; font-weight:700; color:#FFFFFF;">Weekly Dashboard Report</div>
      <div style="font-size:12px; color:#94A3B8; margin-top:2px;">{date_str}</div>
    </div>

    <div style="padding:22px 24px;">
      {_note_html(note, sources)}

      <div style="font-size:13.5px; line-height:1.6; color:#1E293B;">
        Attached:
        <ul style="margin:8px 0 0 0; padding-left:18px;">
          <li style="margin-bottom:4px;"><b>Market Dashboard</b> — rates, equities,
              commodities, credit, FX and volatility</li>
          <li><b>Stock Watchlist</b> — core, connected and global holdings</li>
        </ul>
      </div>

      <div style="margin-top:18px; font-size:12px; color:#64748B;">
        Both are point-in-time snapshots sourced from Yahoo Finance and FRED.
      </div>
    </div>

    <div style="background:#F8FAFC; border-top:1px solid #E2E8F0; padding:12px 24px;
         font-size:10px; color:#94A3B8; text-align:center;">
      Secco Capital · Internal · Confidential · Not investment advice
    </div>
  </div>
</body></html>"""


def build_text(date_str: str, note: str | None) -> str:
    """Plain-text alternative. Mail clients that reject HTML still get the note."""
    parts = [f"Weekly Dashboard Report — {date_str}", ""]
    if note:
        parts += ["THE WEEK IN MARKETS", "", note, ""]
    parts += [
        "Attached:",
        "  - Market Dashboard — rates, equities, commodities, credit, FX and volatility",
        "  - Stock Watchlist — core, connected and global holdings",
        "",
        "Both are point-in-time snapshots sourced from Yahoo Finance and FRED.",
        "",
        "--",
        "Secco Capital · Internal · Confidential · Not investment advice",
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Send
# ---------------------------------------------------------------------------

def encode_attachment(path: str) -> dict:
    with open(path, "rb") as f:
        return {
            "filename": os.path.basename(path),
            "content": base64.b64encode(f.read()).decode("ascii"),
        }


def send_email(subject, html, text, recipients, attachment_paths, api_key, sender):
    attachments = [encode_attachment(p) for p in attachment_paths]

    # base64 inflates by ~4/3; fail with a clear message rather than a 413.
    total_mb = sum(len(a["content"]) for a in attachments) / 1_000_000
    if total_mb > RESEND_MAX_TOTAL_MB:
        raise RuntimeError(
            f"Attachments total {total_mb:.1f}MB encoded, over Resend's "
            f"{RESEND_MAX_TOTAL_MB}MB limit."
        )

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "from": sender,
            "to": recipients,
            "subject": subject,
            "html": html,
            "text": text,
            "attachments": attachments,
        },
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Resend API error {resp.status_code}: {resp.text}")
    logger.info("Sent. Resend id: %s", resp.json().get("id", "unknown"))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="Build the PDFs and note, print the note, send nothing.")
    args = ap.parse_args()

    api_key = os.environ.get("RESEND_API_KEY")
    recipients_str = os.environ.get("EMAIL_RECIPIENTS")
    sender = os.environ.get("EMAIL_FROM", DEFAULT_FROM)

    if not args.dry_run and not (api_key and recipients_str):
        sys.exit(
            "Missing environment variables. Set:\n"
            '  export RESEND_API_KEY="re_..."\n'
            '  export EMAIL_RECIPIENTS="a@example.com,b@example.com"\n'
            "Or pass --dry-run to build without sending."
        )

    date_tag = datetime.now().strftime("%Y-%m-%d")
    date_str = datetime.now().strftime("%d %B %Y")

    logger.info("Building Market Dashboard PDF...")
    market_pdf = f"market_dashboard_{date_tag}.pdf"
    metrics = build_market_pdf(market_pdf)   # reused for the note, not refetched

    logger.info("Building Stock Watchlist PDF...")
    watchlist_pdf = f"stock_watchlist_{date_tag}.pdf"
    build_watchlist_pdf(watchlist_pdf)

    # Macro metrics only — the note generator must never see the watchlist.
    logger.info("Generating the weekly note...")
    note, sources = generate_weekly_note(metrics)

    subject = f"Secco Capital — Weekly Dashboard Report, {date_str}"
    html = build_html(date_str, note, sources)
    text = build_text(date_str, note)

    if args.dry_run:
        print("\n" + "=" * 70)
        print(f"SUBJECT: {subject}")
        print(f"FROM:    {sender}")
        print(f"TO:      {recipients_str or '(unset)'}")
        print("=" * 70)
        print(note or "(no note — ANTHROPIC_API_KEY unset or generation failed)")
        if sources:
            print("\nSOURCES:")
            for title, url in sources:
                print(f"  - {title}\n    {url}")
        print("=" * 70)
        for p in (market_pdf, watchlist_pdf):
            print(f"attachment: {p} ({os.path.getsize(p) / 1000:.0f} KB)")
        print("\nDry run — nothing sent.")
        return

    recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]
    send_email(subject, html, text, recipients, [market_pdf, watchlist_pdf], api_key, sender)
    print(f"\n✓ Weekly report sent to {', '.join(recipients)}\n")


if __name__ == "__main__":
    main()
