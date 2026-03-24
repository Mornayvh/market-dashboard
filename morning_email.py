"""
morning_email.py — Sends a morning market snapshot email via Azure Communication Services.

Usage:
    python morning_email.py

Environment variables required:
    FRED_API_KEY                — FRED API key for rates/spreads
    AZURE_COMM_CONNECTION_STR   — Azure Communication Services connection string
    AZURE_SENDER_ADDRESS        — Sender address from your verified domain (e.g. donotreply@xxxxx.azurecomm.net)
    EMAIL_RECIPIENTS            — Comma-separated list of recipient emails

Azure Setup (one-time, ~10 minutes):
    1. Go to https://portal.azure.com
    2. Create a "Communication Services" resource (free tier available)
    3. Inside it, go to "Email" > "Try Email" > set up a free Azure subdomain
    4. Copy the connection string from Settings > Keys
    5. Copy the sender address (e.g. donotreply@xxxxx.azurecomm.net)

Schedule via GitHub Actions (see .github/workflows/morning_email.yml)
"""

import os
import sys
import logging
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
        ytd = build_change_html(row["ytd_chg"], is_rate, is_spread, invert)

        rows_html += f"""
        <tr>
            <td style="padding:6px 10px; border-bottom:1px solid #E2E8F0; font-weight:500; color:#1E293B;">{idx}</td>
            <td style="padding:6px 10px; border-bottom:1px solid #E2E8F0; text-align:right; font-family:'Courier New',monospace; color:#1E293B;">{val_str}</td>
            <td style="padding:6px 10px; border-bottom:1px solid #E2E8F0; text-align:right; font-family:'Courier New',monospace;">{daily}</td>
            <td style="padding:6px 10px; border-bottom:1px solid #E2E8F0; text-align:right; font-family:'Courier New',monospace;">{weekly}</td>
            <td style="padding:6px 10px; border-bottom:1px solid #E2E8F0; text-align:right; font-family:'Courier New',monospace;">{ytd}</td>
        </tr>"""

    return f"""
    <table style="width:100%; border-collapse:collapse; font-family:Arial,sans-serif; font-size:13px; margin-bottom:20px;">
        <thead>
            <tr style="background:#F8FAFC;">
                <th style="padding:8px 10px; border-bottom:2px solid #CBD5E1; text-align:left; font-size:11px; color:#64748B; text-transform:uppercase; letter-spacing:0.05em;">Asset</th>
                <th style="padding:8px 10px; border-bottom:2px solid #CBD5E1; text-align:right; font-size:11px; color:#64748B; text-transform:uppercase;">Last</th>
                <th style="padding:8px 10px; border-bottom:2px solid #CBD5E1; text-align:right; font-size:11px; color:#64748B; text-transform:uppercase;">1D ({chg_label})</th>
                <th style="padding:8px 10px; border-bottom:2px solid #CBD5E1; text-align:right; font-size:11px; color:#64748B; text-transform:uppercase;">1W ({chg_label})</th>
                <th style="padding:8px 10px; border-bottom:2px solid #CBD5E1; text-align:right; font-size:11px; color:#64748B; text-transform:uppercase;">YTD ({chg_label})</th>
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
        "Crypto": "Crypto",
        "Volatility": "Volatility",
        "Currency": "Currency",
    }
    for cat in CATEGORIES:
        label = section_labels.get(cat, cat)
        table = build_table_html(metrics_df, cat)
        if table:
            tables_html += build_section_header(label) + table

    # Build commentary section
    commentary_html = ""
    if commentary_text:
        paragraphs = [p.strip() for p in commentary_text.split("\n\n") if p.strip()]
        commentary_paras = "".join(
            f'<p style="margin:0 0 10px 0; line-height:1.6;">{p}</p>'
            for p in paragraphs
        )
        commentary_html = f"""
        {build_section_header("Morning Commentary")}
        <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px;
             padding:16px 20px; font-family:Arial,sans-serif; font-size:13px; color:#334155;
             margin-bottom:20px;">
            {commentary_paras}
            <div style="font-size:10px; color:#94A3B8; margin-top:12px; padding-top:8px; border-top:1px solid #E2E8F0;">
                Analyst notes · Not investment advice
            </div>
        </div>"""

    # Assemble full email
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
                {commentary_html}

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

def send_email(html_body, subject, sender, connection_string, recipients):
    """Send the email via Azure Communication Services."""
    from azure.communication.email import EmailClient

    client = EmailClient.from_connection_string(connection_string)

    message = {
        "senderAddress": sender,
        "recipients": {
            "to": [{"address": r, "displayName": ""} for r in recipients],
        },
        "content": {
            "subject": subject,
            "html": html_body,
            "plainText": "Market Dashboard — open the live dashboard: " + DASHBOARD_URL,
        },
    }

    try:
        poller = client.begin_send(message)
        result = poller.result()
        logger.info(f"Email sent successfully. ID: {result['id']}, Status: {result['status']}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Check env vars
    connection_string = os.environ.get("AZURE_COMM_CONNECTION_STR")
    sender = os.environ.get("AZURE_SENDER_ADDRESS")
    recipients_str = os.environ.get("EMAIL_RECIPIENTS")

    if not all([connection_string, sender, recipients_str]):
        print("\nMissing environment variables. Set the following:\n")
        print('  export AZURE_COMM_CONNECTION_STR="endpoint=https://...;accessKey=..."')
        print('  export AZURE_SENDER_ADDRESS="donotreply@xxxxx.azurecomm.net"')
        print('  export EMAIL_RECIPIENTS="boss@company.com,partner2@company.com"')
        print()
        sys.exit(1)

    recipients = [r.strip() for r in recipients_str.split(",")]

    # Fetch and process data
    logger.info("Fetching market data...")
    raw_data = fetch_all_data()
    metrics_df = process_all(raw_data)
    logger.info(f"Data loaded for {len(raw_data)} assets")

    # Generate commentary
    commentary = generate_commentary(metrics_df)

    # Build email
    today_str = datetime.now().strftime("%d %b %Y")
    subject = f"Market Snapshot — {today_str}"
    html = build_email_html(metrics_df, commentary)

    # Send
    send_email(html, subject, sender, connection_string, recipients)
    print(f"\n✓ Morning snapshot sent to {', '.join(recipients)}\n")


if __name__ == "__main__":
    main()
