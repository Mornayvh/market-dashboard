"""
weekly_report_email.py — Emails the weekly PDF dashboard report to principals via Resend.

Generates the Market Dashboard and Stock Watchlist PDFs (no Streamlit server
required — both pull data directly through the src/ ingest layer / yfinance,
exactly like the standalone export scripts) and emails them as attachments.

Usage:
    python weekly_report_email.py

Environment variables required:
    FRED_API_KEY        — FRED API key for rates/spreads (used by the market PDF)
    RESEND_API_KEY      — Resend API key (free at resend.com)
    EMAIL_RECIPIENTS    — Comma-separated list of recipient emails

Schedule via GitHub Actions (see .github/workflows/weekly_report.yml)
"""

import base64
import logging
import os
import sys
from datetime import datetime

import requests

# Add project root to path so we can import project modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Both export scripts expose build_pdf(out_path); alias to disambiguate.
from export_pdf import build_pdf as build_market_pdf
from export_watchlist_pdf import build_pdf as build_watchlist_pdf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------

def generate_pdfs(date_tag: str):
    """Build both report PDFs and return their paths as (market, watchlist)."""
    market_path = f"market_dashboard_{date_tag}.pdf"
    watchlist_path = f"stock_watchlist_{date_tag}.pdf"

    logger.info("Building Market Dashboard PDF...")
    build_market_pdf(market_path)

    logger.info("Building Stock Watchlist PDF...")
    build_watchlist_pdf(watchlist_path)

    return market_path, watchlist_path


# ---------------------------------------------------------------------------
# Email body + send
# ---------------------------------------------------------------------------

def build_text_body(date_str: str) -> str:
    """Short, professional plain-text body."""
    return (
        "Good morning,\n\n"
        f"Please find attached the Secco Capital weekly dashboard report for {date_str}:\n\n"
        "  • Market Dashboard — rates, equities, commodities, credit and volatility\n"
        "  • Stock Watchlist — core, connected and global holdings\n\n"
        "Both are point-in-time snapshots sourced from Yahoo Finance and FRED.\n\n"
        "Kind regards,\n"
        "Secco Capital\n\n"
        "—\n"
        "Confidential. Not investment advice."
    )


def encode_attachment(path: str) -> dict:
    """Read a file and return a Resend attachment dict (base64 content)."""
    with open(path, "rb") as f:
        content = base64.b64encode(f.read()).decode("ascii")
    return {"filename": os.path.basename(path), "content": content}


def send_email(text_body, subject, api_key, recipients, attachment_paths):
    """Send the email with PDF attachments via Resend API (single HTTP POST)."""
    attachments = [encode_attachment(p) for p in attachment_paths]

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": "Secco Capital <onboarding@resend.dev>",
            "to": recipients,
            "subject": subject,
            "text": text_body,
            "attachments": attachments,
        },
        timeout=60,
    )

    if resp.status_code == 200:
        email_id = resp.json().get("id", "unknown")
        logger.info(f"Email sent successfully. ID: {email_id}")
    else:
        logger.error(f"Resend API error {resp.status_code}: {resp.text}")
        raise RuntimeError(f"Email failed: {resp.status_code} {resp.text}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    api_key = os.environ.get("RESEND_API_KEY")
    recipients_str = os.environ.get("EMAIL_RECIPIENTS")

    if not all([api_key, recipients_str]):
        print("\nMissing environment variables. Set the following:\n")
        print('  export RESEND_API_KEY="re_xxxxxxxxx"')
        print('  export EMAIL_RECIPIENTS="boss@company.com,partner2@company.com"')
        print()
        sys.exit(1)

    recipients = [r.strip() for r in recipients_str.split(",")]

    date_tag = datetime.now().strftime("%Y-%m-%d")        # for filenames
    date_str = datetime.now().strftime("%d %b %Y")        # for subject / body

    market_path, watchlist_path = generate_pdfs(date_tag)

    subject = f"Secco Capital — Weekly Dashboard Report {date_str}"
    text = build_text_body(date_str)

    send_email(text, subject, api_key, recipients, [market_path, watchlist_path])
    print(f"\n✓ Weekly report sent to {', '.join(recipients)}\n")


if __name__ == "__main__":
    main()
