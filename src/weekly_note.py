"""
weekly_note.py — The short market note that heads the weekly report email.

Asks Claude to write 2-3 paragraphs on what drove markets over the week, using
the server-side web search tool so the *causes* are grounded in real coverage
rather than invented. The *moves* are never searched for: they are taken from
our own dashboard data and passed in, so the note quotes the same numbers the
attached PDFs show.

CONFIDENTIALITY
---------------
Only macro market data goes into the prompt — indices, rates, spreads,
commodities, FX, volatility. The stock watchlist and any holding, client or
counterparty name is deliberately never sent, because the web search tool turns
prompt content into third-party queries. Keep it that way when editing.

Requires ANTHROPIC_API_KEY. Every failure path returns None so the report still
sends without a note rather than not sending at all.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)

MODEL = "claude-opus-5"

# Refusal fallback: on a policy decline the API re-runs the request on another
# model inside the same call. Market commentary should never trip a classifier,
# but the call is cheap insurance. Orgs without the beta enabled get a 400, so
# _create() retries once without it rather than losing the note.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

SYSTEM = (
    "You are a macro strategist writing the standing weekly note for an "
    "investment team at a UK multi-family office. The readers are experienced "
    "investment professionals: never explain financial fundamentals, never add "
    "disclaimers, never pad. UK English spelling throughout."
)


def _fmt(val, is_rate: bool, is_spread: bool) -> str:
    if val is None or pd.isna(val):
        return "n/a"
    if is_rate:
        return f"{val:.2f}%"
    if is_spread:
        return f"{val:.0f}bp"
    return f"{val:.2f}"


def _fmt_chg(val, is_rate: bool, is_spread: bool) -> str:
    if val is None or pd.isna(val):
        return "n/a"
    sign = "+" if val > 0 else ""
    if is_rate:
        return f"{sign}{val:.2f}pp"
    if is_spread:
        return f"{sign}{val:.0f}bp"
    return f"{sign}{val:.2f}%"


def format_market_data(metrics_df: pd.DataFrame) -> str:
    """The week's moves as a compact text table, grouped by category.

    This is the note's factual base — everything the model is allowed to state
    as a number must come from here.
    """
    lines: list[str] = []
    for category in metrics_df["category"].unique():
        rows = metrics_df[metrics_df["category"] == category]
        lines.append(f"\n{category}:")
        for name, row in rows.iterrows():
            is_rate = bool(row.get("is_rate", False))
            is_spread = bool(row.get("is_spread", False))
            lines.append(
                f"  {name}: {_fmt(row['latest'], is_rate, is_spread)}"
                f"  (1W {_fmt_chg(row['weekly_chg'], is_rate, is_spread)},"
                f" LTM {_fmt_chg(row['ltm_chg'], is_rate, is_spread)})"
            )
    return "\n".join(lines)


def _build_prompt(data_summary: str, as_of: datetime) -> str:
    return (
        f"Today is {as_of.strftime('%A, %d %B %Y')}. Write this week's market note.\n\n"
        "Here is our own dashboard data for the week just ended. Rates and "
        "spreads move in percentage points and basis points; everything else in "
        "percent:\n"
        f"{data_summary}\n\n"
        "Search the web for what actually happened in markets this week — the "
        "macro prints, central bank communication, geopolitics and earnings that "
        "moved the numbers above. Search for indices, rates and macro events "
        "only.\n\n"
        "Then write 2-3 paragraphs, 150-250 words total, covering what moved and "
        "why, and what to watch next week.\n\n"
        "Rules:\n"
        "- Every number you quote must come from the dashboard data above. Do "
        "not source figures from search results, and do not invent any.\n"
        "- Attribute causes only to what you actually found in search. Where a "
        "move has no clear driver in the coverage, say the move happened "
        "without a clean explanation rather than reaching for one.\n"
        "- Be direct and opinionated about what matters. No hedging filler.\n"
        "- Plain paragraphs separated by blank lines. No headers, no bullets, "
        "no bold, no title, no sign-off."
    )


def _create(client, prompt: str):
    """One Messages call with web search. Retries without the fallback beta if
    this org does not have it enabled, so a 400 there costs the note nothing."""
    import anthropic

    kwargs = dict(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM,
        tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 8}],
        messages=[{"role": "user", "content": prompt}],
        output_config={"effort": "high"},
    )
    try:
        return client.beta.messages.create(
            betas=[FALLBACK_BETA], fallbacks="default", **kwargs
        )
    except anthropic.BadRequestError as e:
        logger.warning("Fallback beta rejected (%s); retrying without it.", e)
        return client.messages.create(**kwargs)


def _extract(resp) -> tuple[str, list[tuple[str, str]]]:
    """Pull the note text and any cited (title, url) pairs out of the response."""
    text = "".join(b.text for b in resp.content if b.type == "text").strip()

    sources: list[tuple[str, str]] = []
    seen: set[str] = set()
    for block in resp.content:
        # A successful web_search_tool_result carries a list of results; an
        # errored one carries a single error object instead, so check the type.
        if getattr(block, "type", None) == "web_search_tool_result":
            content = getattr(block, "content", None)
            if not isinstance(content, list):
                logger.warning("Web search returned an error: %r", content)
                continue
            for r in content:
                url = getattr(r, "url", None)
                if url and url not in seen:
                    seen.add(url)
                    sources.append((getattr(r, "title", None) or url, url))
    return text, sources


def generate_weekly_note(
    metrics_df: pd.DataFrame, as_of: datetime | None = None
) -> tuple[str | None, list[tuple[str, str]]]:
    """Return (note_text, sources). Returns (None, []) on any failure — the
    caller should send the report without a note rather than not send it."""
    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic package not installed — sending without a note.")
        return None, []

    as_of = as_of or datetime.now()
    prompt = _build_prompt(format_market_data(metrics_df), as_of)

    # In CI the key arrives as an env var. Locally the SDK also resolves an
    # `ant auth login` profile, so fall through to the zero-arg client rather
    # than insisting on the variable.
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    try:
        client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        resp = _create(client, prompt)

    except (anthropic.AuthenticationError, TypeError):
        # TypeError is what the SDK raises when no credential source resolves
        # at all, which is the ordinary local case.
        logger.warning(
            "No Anthropic credentials (set ANTHROPIC_API_KEY) — sending without a note."
        )
        return None, []
    except Exception as e:
        logger.warning("Note generation failed (%s) — sending without one.", e)
        return None, []

    try:
        if resp.stop_reason == "refusal":
            detail = getattr(resp, "stop_details", None)
            logger.warning(
                "Model declined the request (%s) — sending without a note.",
                getattr(detail, "category", "unknown"),
            )
            return None, []

        text, sources = _extract(resp)
        if not text:
            logger.warning("Empty note returned — sending without one.")
            return None, []

        logger.info("Note generated: %d words, %d sources.", len(text.split()), len(sources))
        return text, sources

    except Exception as e:
        logger.warning("Could not read the response (%s) — sending without a note.", e)
        return None, []
