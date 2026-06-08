"""
export_pdf.py — Render the Market Dashboard to a PDF snapshot.

Usage:
    python export_pdf.py                 # writes market_dashboard_<YYYY-MM-DD>.pdf
    python export_pdf.py --out brief.pdf # writes to a specific path

Requires FRED_API_KEY in env (or Streamlit secrets) for rates/credit data.
"""

import argparse
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)

from src.data_ingest import fetch_all_data
from src.data_process import process_all, get_category_df
from src.viz_helpers import fmt_change, fmt_value

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

# Order mirrors morning_email.py
SECTION_ORDER = ["Equities", "Rates", "Currency", "Credit", "Commodities", "Sentiment", "Volatility"]
SECTION_LABELS = {
    "Rates": "Rates",
    "Credit": "Credit Spreads",
    "Equities": "Equities",
    "Commodities": "Commodities",
    "Sentiment": "Sentiment",
    "Volatility": "Volatility",
    "Currency": "Currency",
}


def change_text_color(val, invert=False):
    if val is None or val == 0:
        return SLATE
    positive = val > 0
    if invert:
        positive = not positive
    return GREEN if positive else RED


def build_section_table(metrics_df, category):
    cat_df = get_category_df(metrics_df, category)
    if cat_df.empty:
        return None

    is_rate_cat = bool(cat_df["is_rate"].any())
    is_spread_cat = bool(cat_df["is_spread"].any())
    if is_rate_cat:
        chg_label = "abs"
    elif is_spread_cat:
        chg_label = "bps"
    else:
        chg_label = "%"

    header = ["Asset", "Last", f"1D ({chg_label})", f"1W ({chg_label})", f"LTM ({chg_label})"]
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
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])

    for row_idx, (name, row) in enumerate(cat_df.iterrows(), start=1):
        is_rate = bool(row["is_rate"])
        is_spread = bool(row["is_spread"])
        invert = bool(row["invert_color"])

        last_str = fmt_value(row["latest"], is_rate, is_spread)
        d1_str = fmt_change(row["daily_chg"], is_rate, is_spread)
        w1_str = fmt_change(row["weekly_chg"], is_rate, is_spread)
        ltm_str = fmt_change(row["ltm_chg"], is_rate, is_spread)

        data.append([name, last_str, d1_str, w1_str, ltm_str])

        style.add("TEXTCOLOR", (2, row_idx), (2, row_idx), change_text_color(row["daily_chg"], invert))
        style.add("TEXTCOLOR", (3, row_idx), (3, row_idx), change_text_color(row["weekly_chg"], invert))
        style.add("TEXTCOLOR", (4, row_idx), (4, row_idx), change_text_color(row["ltm_chg"], invert))

    table = Table(
        data,
        colWidths=[55 * mm, 28 * mm, 28 * mm, 28 * mm, 28 * mm],
        repeatRows=1,
    )
    table.setStyle(style)
    return table


def draw_page_chrome(canv: canvas.Canvas, doc):
    """Header band + footer rule, drawn on every page."""
    width, height = A4

    canv.setFillColor(NAVY)
    canv.rect(0, height - 22 * mm, width, 22 * mm, stroke=0, fill=1)

    canv.setFillColor(colors.white)
    canv.setFont("Helvetica-Bold", 16)
    canv.drawString(18 * mm, height - 13 * mm, "Market Dashboard")

    canv.setFillColor(MUTED)
    canv.setFont("Helvetica", 9)
    canv.drawString(18 * mm, height - 18 * mm, datetime.now().strftime("%A, %d %B %Y"))

    canv.setFillColor(MUTED)
    canv.setFont("Helvetica", 7)
    canv.drawRightString(
        width - 18 * mm,
        12 * mm,
        "Secco Capital  ·  Data: Yahoo Finance & FRED  ·  Confidential  ·  Not investment advice",
    )
    canv.drawRightString(width - 18 * mm, 8 * mm, f"Page {doc.page}")


def build_pdf(out_path: str):
    logger.info("Fetching market data...")
    raw = fetch_all_data()
    metrics = process_all(raw)
    logger.info("Data loaded for %d assets", len(raw))

    doc = BaseDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=28 * mm,
        bottomMargin=18 * mm,
        title="Market Dashboard",
        author="Secco Capital",
    )

    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height,
        showBoundary=0,
    )
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=draw_page_chrome)])

    section_style = ParagraphStyle(
        "section",
        fontName="Helvetica-Bold",
        fontSize=8,
        textColor=SLATE,
        spaceBefore=8,
        spaceAfter=4,
        leading=10,
    )

    story = []
    for cat in SECTION_ORDER:
        table = build_section_table(metrics, cat)
        if table is None:
            continue
        label = SECTION_LABELS.get(cat, cat).upper()
        story.append(Paragraph(label, section_style))
        story.append(table)
        story.append(Spacer(1, 6))

    doc.build(story)
    logger.info("Wrote %s", out_path)


def main():
    parser = argparse.ArgumentParser(description="Export Market Dashboard to PDF.")
    parser.add_argument(
        "--out",
        default=None,
        help="Output path. Defaults to market_dashboard_<YYYY-MM-DD>.pdf in cwd.",
    )
    args = parser.parse_args()

    out_path = args.out or f"market_dashboard_{datetime.now().strftime('%Y-%m-%d')}.pdf"
    build_pdf(out_path)
    print(f"✓ PDF written to {out_path}")


if __name__ == "__main__":
    main()
