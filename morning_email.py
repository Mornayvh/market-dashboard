"""
morning_email.py — Sends a morning market snapshot email via Resend.

Usage:
    python morning_email.py

Environment variables required:
    FRED_API_KEY        — FRED API key for rates/spreads
    RESEND_API_KEY      — Resend API key (free at resend.com)
    EMAIL_RECIPIENTS    — Comma-separated list of recipient emails

Setup:
    1. Sign up at https://resend.com (free, 100 emails/day)
    2. Create an API key in the dashboard
    3. Set the env vars above

Schedule via GitHub Actions (see .github/workflows/morning_email.yml)
"""

import os
import sys
import logging
import requests
from datetime import datetime

# Add project root to path so we can import src modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import ASSETS, CATEGORIES, ASSETS_BY_CATEGORY
from src.data_ingest import fetch_all_data
from src.data_process import process_all, get_category_df
from src.viz_helpers import fmt_value, fmt_change, change_color
from src.commentary import generate_commentary

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DASHBOARD_URL = "https://market-dashboard-secco-capital.streamlit.app"

# ---------------------------------------------------------------------------
# Email HTML builder
# ---------------------------------------------------------------------------

def build_change_html(val, is_rate=False, is_spread=False, invert=False):
    """Format a change value with color."""
    color = change_color(val, invert)
    formatted = fmt_change(val, is_rate, is_spread)
    return f'<span style="color:{color}; font-weight:600;">{formatted}</span>'


def build_table_html(metrics_df, category):
    """Build an HTML table for a single asset category."""
    cat_df = get_category_df(metrics_df, category)
    if cat_df.empty:
        return ""

    is_rate_cat = cat_df["is_rate"].any()
    is_spread_cat = cat_df["is_spread"].any()
    if is_rate_cat:
        chg_label = "abs"
    elif is_spread_cat:
        chg_label = "bps"
    else:
        chg_label = "%"

    rows_html = ""
    for idx, row in cat_df.iterrows():
        is_rate = row["is_rate"]
        is_spread = row["is_spread"]
        invert = row["invert_color"]
        val_str = fmt_value(row["latest"], is_rate, is_spread)

        daily = build_change_html(row["daily_chg"], is_rate, is_spread, invert)
        weekly = build_change_html(row["weekly_chg"], is_rate, is_spread, invert)
        ltm = build_change_html(row["ltm_chg"], is_rate, is_spread, invert)

        rows_html += f"""
        <tr>
            <td style="padding:6px 10px; border-bottom:1px solid #E2E8F0; font-weight:500; color:#1E293B;">{idx}</td>
            <td style="padding:6px 10px; border-bottom:1px solid #E2E8F0; text-align:right; font-family:'Courier New',monospace; color:#1E293B;">{val_str}</td>
            <td style="padding:6px 10px; border-bottom:1px solid #E2E8F0; text-align:right; font-family:'Courier New',monospace;">{daily}</td>
            <td style="padding:6px 10px; border-bottom:1px solid #E2E8F0; text-align:right; font-family:'Courier New',monospace;">{weekly}</td>
            <td style="padding:6px 10px; border-bottom:1px solid #E2E8F0; text-align:right; font-family:'Courier New',monospace;">{ltm}</td>
        </tr>"""

    return f"""
    <table style="width:100%; border-collapse:collapse; font-family:Arial,sans-serif; font-size:13px; margin-bottom:20px;">
        <thead>
            <tr style="background:#F8FAFC;">
                <th style="padding:8px 10px; border-bottom:2px solid #CBD5E1; text-align:left; font-size:11px; color:#64748B; text-transform:uppercase; letter-spacing:0.05em;">Asset</th>
                <th style="padding:8px 10px; border-bottom:2px solid #CBD5E1; text-align:right; font-size:11px; color:#64748B; text-transform:uppercase;">Last</th>
                <th style="padding:8px 10px; border-bottom:2px solid #CBD5E1; text-align:right; font-size:11px; color:#64748B; text-transform:uppercase;">1D ({chg_label})</th>
                <th style="padding:8px 10px; border-bottom:2px solid #CBD5E1; text-align:right; font-size:11px; color:#64748B; text-transform:uppercase;">1W ({chg_label})</th>
                <th style="padding:8px 10px; border-bottom:2px solid #CBD5E1; text-align:right; font-size:11px; color:#64748B; text-transform:uppercase;">LTM ({chg_label})</th>
            </tr>
        </thead>
        <tbody>{rows_html}</tbody>
    </table>"""


def build_section_header(title):
    """Build a section header."""
    return f"""
    <div style="font-family:Arial,sans-serif; font-size:11px; font-weight:700; color:#64748B;
         text-transform:uppercase; letter-spacing:0.1em; padding:8px 0 6px 0;
         border-bottom:1px solid #E2E8F0; margin-top:16px; margin-bottom:8px;">
        {title}
    </div>"""


def build_email_html(metrics_df, commentary_text):
    """Build the complete email HTML."""
    today_str = datetime.now().strftime("%A, %d %B %Y")

    # Build all data tables
    tables_html = ""
    section_labels = {
        "Rates": "Rates",
        "Credit": "Credit Spreads",
        "Equities": "Equities",
        "Commodities": "Commodities",
        "Sentiment": "Sentiment",
        "Volatility": "Volatility",
        "Currency": "Currency",
    }
    # Email table order: Equities, Rates, Currencies, Credit, Commodities, Sentiment, Volatility
    email_order = ["Equities", "Rates", "Currency", "Credit", "Commodities", "Sentiment", "Volatility"]
    for cat in email_order:
        label = section_labels.get(cat, cat)
        table = build_table_html(metrics_df, cat)
        if table:
            tables_html += build_section_header(label) + table

    # Assemble full email (no commentary)
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin:0; padding:0; background:#F1F5F9;">
        <div style="max-width:680px; margin:20px auto; background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; overflow:hidden;">

            <!-- Header -->
            <div style="background:#1E293B; padding:20px 24px;">
                <div style="font-family:Arial,sans-serif; font-size:18px; font-weight:700; color:#FFFFFF;">
                    Market Dashboard
                </div>
                <div style="font-family:Arial,sans-serif; font-size:12px; color:#94A3B8; margin-top:2px;">
                    {today_str}
                </div>
            </div>

            <!-- Body -->
            <div style="padding:20px 24px;">
                {tables_html}

                <!-- Dashboard link -->
                <div style="text-align:center; margin:24px 0 16px 0;">
                    <a href="{DASHBOARD_URL}"
                       style="display:inline-block; background:#2563EB; color:#FFFFFF; font-family:Arial,sans-serif;
                              font-size:13px; font-weight:600; text-decoration:none; padding:10px 28px;
                              border-radius:4px;">
                        Open Live Dashboard &rarr;
                    </a>
                </div>
            </div>

            <!-- Footer -->
            <div style="background:#F8FAFC; border-top:1px solid #E2E8F0; padding:12px 24px;
                 font-family:Arial,sans-serif; font-size:10px; color:#94A3B8; text-align:center;">
                Secco Capital · Market Dashboard v1.0 · Data from Yahoo Finance &amp; FRED · Not investment advice
            </div>
        </div>
    </body>
    </html>"""

    return html

# ---------------------------------------------------------------------------
# Send email
# ---------------------------------------------------------------------------

def send_email(html_body, subject, api_key, recipients):
    """Send the email via Resend API (single HTTP POST, no SDK needed)."""
    resp = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": "Market Dashboard <onboarding@resend.dev>",
            "to": recipients,
            "subject": subject,
            "html": html_body,
        },
        timeout=30,
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
    # Check env vars
    api_key = os.environ.get("RESEND_API_KEY")
    recipients_str = os.environ.get("EMAIL_RECIPIENTS")

    if not all([api_key, recipients_str]):
        print("\nMissing environment variables. Set the following:\n")
        print('  export RESEND_API_KEY="re_xxxxxxxxx"')
        print('  export EMAIL_RECIPIENTS="boss@company.com,partner2@company.com"')
        print()
        sys.exit(1)

    recipients = [r.strip() for r in recipients_str.split(",")]

    # Fetch and process data
    logger.info("Fetching market data...")
    raw_data = fetch_all_data()
    metrics_df = process_all(raw_data)
    logger.info(f"Data loaded for {len(raw_data)} assets")

    # Build email (no commentary)
    today_str = datetime.now().strftime("%d %b %Y")
    subject = f"Market Snapshot \u2014 {today_str}"
    html = build_email_html(metrics_df, None)

    # Send
    send_email(html, subject, api_key, recipients)
    print(f"\n\u2713 Morning snapshot sent to {', '.join(recipients)}\n")


if __name__ == "__main__":
    main()
