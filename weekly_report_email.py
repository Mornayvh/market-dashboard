"""
weekly_report_email.py — Emails the weekly dashboard report via Resend.

Builds the Market Dashboard and Stock Watchlist PDFs (no Streamlit server
needed — both pull data through the src/ ingest layer, exactly like the
standalone export scripts) and sends them as one email with both attached.

Usage:
    python weekly_report_email.py            # build and send
    python weekly_report_email.py --dry-run  # build and print, send nothing
    python weekly_report_email.py --check    # verify key and sender, build nothing

Environment (a variable set to the empty string counts as unset — see env()):
    RESEND_API_KEY      required — Resend API key
    EMAIL_RECIPIENTS    required — comma-separated recipients
    EMAIL_FROM          optional — sender, default "Secco Capital <reports@seccocapital.com>"
                                   (the domain must be verified in Resend)
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

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_FROM = "Secco Capital <reports@seccocapital.com>"
RESEND_MAX_TOTAL_MB = 40  # Resend's per-message ceiling, attachments included


def env(name: str, default: str | None = None) -> str | None:
    """Read an environment variable, treating blank as unset.

    GitHub Actions expands `env: X: ${{ secrets.X }}` to the empty string when
    the secret does not exist, so the variable is present but empty and a plain
    os.environ.get(name, default) returns "" rather than the default. Every
    optional variable must come through here.
    """
    value = os.environ.get(name)
    return value.strip() if value and value.strip() else default


# ---------------------------------------------------------------------------
# Email body
# ---------------------------------------------------------------------------

def build_html(date_str: str) -> str:
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


def build_text(date_str: str) -> str:
    """Plain-text alternative for clients that reject HTML."""
    parts = [
        f"Weekly Dashboard Report — {date_str}",
        "",
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
        raise RuntimeError(
            f"Resend API error {resp.status_code} sending from {sender!r} to "
            f"{len(recipients)} recipient(s): {resp.text}"
        )
    logger.info("Sent. Resend id: %s", resp.json().get("id", "unknown"))


def preflight(api_key: str, sender: str) -> None:
    """Check the key and the sender domain with Resend.

    Runs before the PDF build so a credential or domain problem surfaces in
    seconds with a usable message, rather than three minutes later as an
    opaque API error.
    """
    domain = sender.rsplit("@", 1)[-1].rstrip(">").strip().lower()

    resp = requests.get(
        "https://api.resend.com/domains",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30,
    )
    if resp.status_code in (401, 403) or (
        resp.status_code == 400 and "api key" in resp.text.lower()
    ):
        raise RuntimeError(
            f"Resend rejected the API key ({resp.status_code}): {resp.text}\n"
            "Check the RESEND_API_KEY repo secret against a live key at "
            "https://resend.com/api-keys."
        )
    if resp.status_code != 200:
        raise RuntimeError(f"Resend API error {resp.status_code}: {resp.text}")

    registered = {d["name"].lower(): d.get("status") for d in resp.json().get("data", [])}
    logger.info("Resend domains: %s", registered or "(none registered)")

    # Resend's shared sandbox sender needs no verification, but it delivers
    # only to the address that owns the Resend account.
    if domain.endswith("resend.dev"):
        logger.warning(
            "Sending from %s — Resend's sandbox sender. No domain verification "
            "needed, but it delivers only to the Resend account owner's own "
            "address; every other recipient is dropped.", domain
        )
        return

    status = registered.get(domain)
    if status is None:
        raise RuntimeError(
            f"Sender domain '{domain}' is not registered in this Resend account "
            f"(registered: {', '.join(registered) or 'none'}). Either add and "
            f"verify it at https://resend.com/domains, or set EMAIL_FROM to a "
            f"sender on a domain that is already verified."
        )
    if status != "verified":
        raise RuntimeError(
            f"Sender domain '{domain}' is registered but its status is "
            f"'{status}', not 'verified' — finish its DNS records at "
            f"https://resend.com/domains."
        )
    logger.info("Sender domain '%s' is verified.", domain)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="Build the PDFs and print what would be sent; send nothing.")
    ap.add_argument("--check", action="store_true",
                    help="Verify the Resend key and sender domain; build and send nothing.")
    args = ap.parse_args()

    api_key = env("RESEND_API_KEY")
    recipients_str = env("EMAIL_RECIPIENTS")
    sender = env("EMAIL_FROM", DEFAULT_FROM)

    if args.check:
        print(f"FROM: {sender}")
        print(f"TO:   {recipients_str or '(unset)'}")
        if not api_key:
            sys.exit("RESEND_API_KEY is unset or empty — nothing to check.")
        preflight(api_key, sender)
        print("\n\u2713 Resend key and sender domain both check out.")
        return

    if not args.dry_run:
        missing = [n for n, v in (("RESEND_API_KEY", api_key),
                                  ("EMAIL_RECIPIENTS", recipients_str)) if not v]
        if missing:
            sys.exit(
                f"Missing or empty: {', '.join(missing)}. Set:\n"
                '  export RESEND_API_KEY="re_..."\n'
                '  export EMAIL_RECIPIENTS="a@example.com,b@example.com"\n'
                "Or pass --dry-run to build without sending."
            )
        # Credentials before compute: the build takes minutes, this takes a second.
        preflight(api_key, sender)

    date_tag = datetime.now().strftime("%Y-%m-%d")
    date_str = datetime.now().strftime("%d %B %Y")

    logger.info("Building Market Dashboard PDF...")
    market_pdf = f"market_dashboard_{date_tag}.pdf"
    build_market_pdf(market_pdf)

    logger.info("Building Stock Watchlist PDF...")
    watchlist_pdf = f"stock_watchlist_{date_tag}.pdf"
    build_watchlist_pdf(watchlist_pdf)

    subject = f"Secco Capital — Weekly Dashboard Report, {date_str}"
    html = build_html(date_str)
    text = build_text(date_str)

    if args.dry_run:
        print("\n" + "=" * 70)
        print(f"SUBJECT: {subject}")
        print(f"FROM:    {sender}")
        print(f"TO:      {recipients_str or '(unset)'}")
        print("=" * 70)
        for p in (market_pdf, watchlist_pdf):
            print(f"attachment: {p} ({os.path.getsize(p) / 1000:.0f} KB)")
        print("\nDry run — nothing sent.")
        return

    recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]
    send_email(subject, html, text, recipients, [market_pdf, watchlist_pdf], api_key, sender)
    print(f"\n✓ Weekly report sent to {', '.join(recipients)}\n")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        # Config and API failures are operational, not bugs — a traceback in
        # the Actions log buries the one line that says what went wrong.
        sys.exit(f"ERROR: {exc}")
