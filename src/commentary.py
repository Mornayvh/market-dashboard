"""
commentary.py — Market commentary for the dashboard.
Static commentary updated manually. Edit the COMMENTARY dict below each morning,
or leave it as-is for a standing view. If ANTHROPIC_API_KEY is set, AI-generated
commentary will be used instead.

To update: edit the 'text' field in COMMENTARY below. Keep each paragraph
on a single line separated by double newlines.
"""

import os
import logging
from datetime import datetime
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static commentary — edit this section each morning
# ---------------------------------------------------------------------------

COMMENTARY = {
    "date": "2026-03-23",
    "text": (
        "Risk-off tone persists heading into the new week. The S&P 500 closed at "
        "6,507 on Friday \u2014 its fourth consecutive weekly decline and roughly 5% "
        "below the January high of 6,797. The VIX spiked to 26.8, well above its "
        "long-run average, signalling that options markets are pricing meaningfully "
        "higher uncertainty. The Iran conflict and its oil supply implications "
        "remain the dominant macro driver."
        "\n\n"
        "Rates are under upward pressure as inflation expectations firm. The 10Y "
        "yield edged to 4.39%, reflecting a market that now sees the Fed on hold "
        "for the foreseeable future. With Brent crude trading above $112 and WTI "
        "near $98, the stagflation narrative is gaining traction \u2014 Goldman noted "
        "that equities have not priced in enough risk premium for a prolonged "
        "disruption. Credit spreads bear watching; any widening in HY would signal "
        "real stress beyond the equity surface."
        "\n\n"
        "Equities are bifurcating. Tech and growth continue to lead losses \u2014 the "
        "Nasdaq fell 2% on Friday \u2014 while the Russell 2000 has slipped into "
        "correction territory, down 10% from its recent high. The rotation toward "
        "defensives and energy is accelerating. Notable: Nike, Home Depot, and "
        "O\u2019Reilly Auto all trading at 52-week lows, which may present value "
        "opportunities for patient capital."
        "\n\n"
        "Gold pulled back sharply despite the risk-off environment, weighed down "
        "by dollar strength and fading rate-cut expectations. Oil remains the "
        "story \u2014 Iraq\u2019s force majeure on foreign-operated oilfields and Hormuz "
        "transit disruptions are keeping Brent elevated. Bitcoin is consolidating "
        "around $68K, caught between risk-asset selling pressure and its "
        "inflation-hedge bid."
        "\n\n"
        "Key watches this week: any Hormuz developments or ceasefire signals will "
        "drive oil and by extension the entire macro complex. The market is now "
        "pricing a 35% recession probability per JPMorgan\u2019s regime models, up from "
        "10% two weeks ago. If spreads start widening in sympathy, the current "
        "correction could deepen meaningfully."
    ),
}

# ---------------------------------------------------------------------------
# Commentary retrieval
# ---------------------------------------------------------------------------

def generate_commentary(metrics_df: pd.DataFrame) -> Optional[str]:
    """
    Return market commentary. Uses static text by default.
    Set ANTHROPIC_API_KEY env var to enable AI-generated commentary.
    """
    # Check for AI commentary first
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        ai_commentary = _generate_ai_commentary(metrics_df, api_key)
        if ai_commentary:
            return ai_commentary

    # Fall back to static commentary
    return COMMENTARY.get("text")


def _generate_ai_commentary(metrics_df: pd.DataFrame, api_key: str) -> Optional[str]:
    """
    Generate commentary via Anthropic API. Returns None on failure,
    falling back to static commentary.
    """
    try:
        import requests
        from src.viz_helpers import fmt_value, fmt_change

        # Build data context
        lines = []
        for name, row in metrics_df.iterrows():
            is_rate = row.get("is_rate", False)
            is_spread = row.get("is_spread", False)
            val = fmt_value(row["latest"], is_rate, is_spread)
            daily = fmt_change(row["daily_chg"], is_rate, is_spread)
            weekly = fmt_change(row["weekly_chg"], is_rate, is_spread)
            ytd = fmt_change(row["ytd_chg"], is_rate, is_spread)
            lines.append(f"{name}: {val} (1D: {daily}, 1W: {weekly}, YTD: {ytd})")

        data_summary = "\n".join(lines)
        today_str = datetime.now().strftime("%A, %d %B %Y")

        prompt = (
            f"You are a senior macro strategist writing a brief morning market "
            f"commentary for investment partners at a private investment firm. "
            f"Today is {today_str}.\n\n"
            f"Here is today's market data:\n\n{data_summary}\n\n"
            f"Write a concise market commentary in 4-5 short paragraphs covering: "
            f"overall market tone, rates & credit, equities, commodities & crypto, "
            f"and what to watch. Be direct and opinionated. Use actual numbers. "
            f"Keep each paragraph to 2-3 sentences. No bullet points, no headers, "
            f"no bold text, no disclaimers. Total: 150-200 words."
        )

        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")

        return text.strip() if text.strip() else None

    except Exception as e:
        logger.warning(f"AI commentary failed, using static: {e}")
        return None
