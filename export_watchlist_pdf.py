"""
export_watchlist_pdf.py — Render the Stock Watchlist to a PDF snapshot.

Usage:
    python export_watchlist_pdf.py                 # writes stock_watchlist_<YYYY-MM-DD>.pdf
    python export_watchlist_pdf.py --out brief.pdf # writes to a specific path

Mirrors the layout and styling of pages/3_Stock_Watchlist.py.
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Palette mirrors src/viz_helpers.py COLORS
NAVY = colors.HexColor("#1E293B")
SLATE = colors.HexColor("#64748B")
MUTED = colors.HexColor("#94A3B8")
BORDER = colors.HexColor("#E2E8F0")
ROW_ALT = colors.HexColor("#F8FAFC")
GREEN = colors.HexColor("#16A34A")
RED = colors.HexColor("#DC2626")

# Keep in sync with pages/3_Stock_Watchlist.py WATCHLIST
WATCHLIST = {
    "Core Holdings": [
        ("Richemont", "CFR.SW", "CHF"),
        ("Remgro", "REM.JO", "ZAR"),
        ("Reinet", "REINA.AS", "EUR"),
    ],
    "Connected Holdings": [
        ("BAT (LSE)", "BATS.L", "GBP"),
        ("BAT (JSE)", "BTI.JO", "ZAR"),
        ("FirstRand", "FSR.JO", "ZAR"),
        ("OUTsurance", "OUT.JO", "ZAR"),
        ("Discovery", "DSY.JO", "ZAR"),
    ],
    "Global": [
        ("Berkshire Hathaway", "BRK-B", "USD"),
        ("Apple", "AAPL", "USD"),
        ("Alphabet", "GOOGL", "USD"),
        ("Amazon", "AMZN", "USD"),
        ("Meta", "META", "USD"),
        ("Microsoft", "MSFT", "USD"),
        ("Nvidia", "NVDA", "USD"),
        ("Tesla", "TSLA", "USD"),
        ("Alibaba", "BABA", "USD"),
        ("BYD", "BYDDY", "USD"),
        ("Tencent", "TCEHY", "USD"),
        ("Apollo", "APO", "USD"),
        ("KKR", "KKR", "USD"),
        ("Dell", "DELL", "USD"),
        ("Palo Alto", "PANW", "USD"),
        ("Deere & Co", "DE", "USD"),
        ("Teledyne", "TDY", "USD"),
        ("Waste Management", "WM", "USD"),
        ("Uber", "UBER", "USD"),
        ("Markel", "MKL", "USD"),
    ],
}

CURRENCY_SYMBOLS = {"USD": "$", "GBP": "£", "EUR": "€", "CHF": "CHF ", "ZAR": "R"}


def fmt_price(val, currency):
    if val is None or pd.isna(val):
        return "—"
    sym = CURRENCY_SYMBOLS.get(currency, "")
    if val >= 10000:
        return f"{sym}{val:,.0f}"
    if val >= 100:
        return f"{sym}{val:,.1f}"
    return f"{sym}{val:,.2f}"


def fmt_chg(val):
    if val is None or pd.isna(val):
        return "—"
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.1f}%"


def chg_color(val):
    if val is None or pd.isna(val) or val == 0:
        return SLATE
    return GREEN if val > 0 else RED


def fetch_one(ticker: str):
    """Return (price, chg_1d, chg_1w, chg_ltm, high_52w, low_52w) or all-None on failure."""
    try:
        hist = yf.Ticker(ticker).history(period="1y", auto_adjust=True)
        if hist is None or hist.empty or "Close" not in hist.columns:
            return (None,) * 6

        hist.index = pd.to_datetime(hist.index).tz_localize(None)
        close = hist["Close"]
        last = float(close.iloc[-1])

        chg_1d = (last / float(close.iloc[-2]) - 1) * 100 if len(close) >= 2 else None

        chg_1w = None
        week_ago = datetime.now() - timedelta(days=7)
        week_data = close[close.index <= week_ago]
        if not week_data.empty:
            chg_1w = (last / float(week_data.iloc[-1]) - 1) * 100

        chg_ltm = (last / float(close.iloc[0]) - 1) * 100 if len(close) >= 2 else None

        return last, chg_1d, chg_1w, chg_ltm, float(close.max()), float(close.min())
    except Exception as e:
        logger.warning("Fetch failed for %s: %s", ticker, e)
        return (None,) * 6


def build_group_table(rows):
    """rows: list of (name, ticker, currency, price, c1d, c1w, cltm, hi, lo)."""
    header = ["Stock", "Price", "1D", "1W", "LTM", "52W High", "52W Low"]
    data = [header]

    style = TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7.5),
        ("TEXTCOLOR", (0, 0), (-1, 0), SLATE),
        ("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (-1, 0), ROW_ALT),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica"),
        ("FONTNAME", (1, 1), (-1, -1), "Courier"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TEXTCOLOR", (0, 1), (0, -1), NAVY),
        ("TEXTCOLOR", (1, 1), (1, -1), NAVY),
        ("TEXTCOLOR", (5, 1), (6, -1), NAVY),
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])

    label_style = ParagraphStyle(
        "stockname", fontName="Helvetica", fontSize=9, leading=11, textColor=NAVY,
    )

    for i, (name, ticker, currency, price, c1d, c1w, cltm, hi, lo) in enumerate(rows, start=1):
        label = Paragraph(
            f'{name} <font size=6.5 color="#94A3B8">{ticker}</font>', label_style,
        )
        data.append([
            label,
            fmt_price(price, currency),
            fmt_chg(c1d), fmt_chg(c1w), fmt_chg(cltm),
            fmt_price(hi, currency), fmt_price(lo, currency),
        ])
        style.add("TEXTCOLOR", (2, i), (2, i), chg_color(c1d))
        style.add("TEXTCOLOR", (3, i), (3, i), chg_color(c1w))
        style.add("TEXTCOLOR", (4, i), (4, i), chg_color(cltm))

    table = Table(
        data,
        colWidths=[44 * mm, 22 * mm, 16 * mm, 16 * mm, 18 * mm, 22 * mm, 22 * mm],
        repeatRows=1,
    )
    table.setStyle(style)
    return table


def draw_page_chrome(canv: canvas.Canvas, doc):
    width, height = A4

    canv.setFillColor(NAVY)
    canv.rect(0, height - 22 * mm, width, 22 * mm, stroke=0, fill=1)

    canv.setFillColor(colors.white)
    canv.setFont("Helvetica-Bold", 16)
    canv.drawString(18 * mm, height - 13 * mm, "Stock Watchlist")

    canv.setFillColor(MUTED)
    canv.setFont("Helvetica", 9)
    canv.drawString(18 * mm, height - 18 * mm, datetime.now().strftime("%A, %d %B %Y"))

    canv.setFillColor(MUTED)
    canv.setFont("Helvetica", 7)
    canv.drawRightString(
        width - 18 * mm, 12 * mm,
        "Secco Capital  ·  Data: Yahoo Finance  ·  Confidential  ·  Not investment advice",
    )
    canv.drawRightString(width - 18 * mm, 8 * mm, f"Page {doc.page}")


def build_pdf(out_path: str):
    logger.info("Fetching watchlist data...")
    fetched = {}
    for group, stocks in WATCHLIST.items():
        for name, ticker, currency in stocks:
            fetched[ticker] = fetch_one(ticker)
    logger.info("Data loaded for %d stocks", len(fetched))

    doc = BaseDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=28 * mm,
        bottomMargin=18 * mm,
        title="Stock Watchlist",
        author="Secco Capital",
    )

    frame = Frame(
        doc.leftMargin, doc.bottomMargin, doc.width, doc.height, showBoundary=0,
    )
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=draw_page_chrome)])

    section_style = ParagraphStyle(
        "section", fontName="Helvetica-Bold", fontSize=8, textColor=SLATE,
        spaceBefore=8, spaceAfter=4, leading=10,
    )

    story = []
    for group, stocks in WATCHLIST.items():
        story.append(Paragraph(group.upper(), section_style))
        rows = [
            (name, ticker, currency, *fetched[ticker])
            for name, ticker, currency in stocks
        ]
        story.append(build_group_table(rows))
        story.append(Spacer(1, 6))

    doc.build(story)
    logger.info("Wrote %s", out_path)


def main():
    parser = argparse.ArgumentParser(description="Export Stock Watchlist to PDF.")
    parser.add_argument(
        "--out", default=None,
        help="Output path. Defaults to stock_watchlist_<YYYY-MM-DD>.pdf in cwd.",
    )
    args = parser.parse_args()

    out_path = args.out or f"stock_watchlist_{datetime.now().strftime('%Y-%m-%d')}.pdf"
    build_pdf(out_path)
    print(f"✓ PDF written to {out_path}")


if __name__ == "__main__":
    main()
