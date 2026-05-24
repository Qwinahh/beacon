"""
Tweet content generation via the Claude API.

The writer receives a candidate item, assembled persona context, and recent
post history, then generates a tweet that sounds like Quin actually wrote it --
not a news summary bot.

The key rule: every post must say something SPECIFIC. A number, a mechanic,
a comparison, an implication. If the only take is "X happened and it's
interesting", we don't post.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Optional, Union

import anthropic

from bot.brain.context import build_system_prompt, build_writer_context
from bot.config import CLAUDE_MAX_TOKENS, CLAUDE_MODEL, TEMPLATE_FALLBACK
from bot.sources.defillama import RaiseItem, TvlMoverItem
from bot.sources.rss import FeedItem

log = logging.getLogger(__name__)

CandidateItem = Union[FeedItem, RaiseItem, TvlMoverItem]

# Phrases that signal a generic, low-value post. If the generated tweet
# contains any of these, it gets rejected and we skip rather than post slop.
_REJECT_PHRASES = [
    "worth watching",
    "keep an eye on",
    "looks interesting",
    "could be big",
    "this is huge",
    "bullish signal",
    "looking good",
    "exciting times",
    "to the moon",
    "very exciting",
    "pretty interesting",
    "pretty bullish",
    "seems bullish",
    "things are heating up",
    "the market is",
    "markets are",
    "crypto is",
    "btc is up",
    "btc is down",
    "eth is up",
    "eth is down",
    "price action",
    "looking promising",
    "could be a game changer",
    "game changer",
    "revolutionary",
    "this changes everything",
]

# A post must contain at least one of these to be considered substantive.
# Numbers count automatically if present as digits.
_SUBSTANCE_PATTERNS = [
    r"\$[\d,.]+[MBKmb]?",  # dollar amounts: $4.2B, $50M, $1,540
    r"\d+[\.,]?\d*%",       # percentages: 40%, 0.05%, 3.2%
    r"\d+[hHdDwW]",         # time-based: 48h, 7d, 2w
    r"\b\d{2,}\b",          # any 2+ digit number
]


# ---------------------------------------------------------------------------
# Item summary builders
# ---------------------------------------------------------------------------

def _build_item_summary(item: CandidateItem) -> str:
    if isinstance(item, RaiseItem):
        amt = f"${item.amount:.0f}M" if item.amount else "undisclosed"
        return (
            f"Type: funding round\n"
            f"Project: {item.name}\n"
            f"Amount: {amt}\n"
            f"Round: {item.round_name}\n"
            f"Category: {item.category}"
        )
    if isinstance(item, TvlMoverItem):
        direction = "gained" if item.change_pct > 0 else "lost"
        return (
            f"Type: TVL movement\n"
            f"Protocol: {item.name}\n"
            f"TVL {direction}: {abs(item.change_pct):.1f}% in 24h\n"
            f"Current TVL: ${item.tvl_usd:,.0f}\n"
            f"Category: {item.category}"
        )
    return f"Type: news\nHeadline: {item.title}\nSource: {item.source}"


def _build_portfolio_context(portfolio: dict) -> str:
    positions = portfolio.get("positions", [])
    airdrops  = portfolio.get("airdrops", [])
    if not positions and not airdrops:
        return ""
    lines = ["Held positions (end tweet with '(position disclosed)' if relevant):"]
    for p in positions:
        if p.get("status") == "active":
            lines.append(f"  - {p['project']} ({p.get('ticker', '')}): {p.get('entry_note', '')}")
    for a in airdrops:
        if a.get("status") == "farming":
            lines.append(f"  - Farming {a['project']}: {', '.join(a.get('actions', []))}")
    return "\n".join(lines)


def _item_topic(item: CandidateItem) -> str:
    if isinstance(item, FeedItem):
        return item.topic or ""
    return getattr(item, "topic", getattr(item, "category", "")) or ""


def _item_title(item: CandidateItem) -> str:
    if isinstance(item, (RaiseItem, TvlMoverItem)):
        return item.name
    return item.title


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------

def _user_prompt(
    item: CandidateItem,
    portfolio: dict,
    recent_formats: list[str],
    x_conversation: Optional[str] = None,
) -> str:
    topic  = _item_topic(item)
    title  = _item_title(item)

    item_block      = _build_item_summary(item)
    portfolio_block = _build_portfolio_context(portfolio)
    format_history  = ", ".join(recent_formats[-5:]) if recent_formats else "none"
    context_block   = build_writer_context(topic, title, x_conversation)

    parts: list[str] = []

    if context_block:
        parts += [context_block, "---"]

    parts += [
        "Write one tweet about the following item.",
        "",
        item_block,
    ]

    if portfolio_block:
        parts += ["", portfolio_block]

    parts += [
        "",
        f"Formats used recently (avoid repeating): {format_history}",
        "",
        "HARD REQUIREMENTS -- the tweet will be rejected if it breaks these:",
        "1. Must contain at least one specific number, dollar amount, percentage, or named protocol mechanic.",
        "2. Must state an implication or take -- not just describe what happened.",
        "3. No phrases like 'worth watching', 'looks interesting', 'bullish signal', 'game changer'.",
        "4. Under 270 characters. No hashtags. No URLs. No quotes around the output.",
        "5. Output only the tweet text. Nothing else.",
        "",
        "GOOD examples (study the structure, not the content):",
        '- "Variational airdrop points now worth ~$1,540 each at Hyperliquid-comparable FDV. That changes the math on whether the farm is worth it."',
        '- "Hyperliquid OI hit $4.2B yesterday -- up 40% in two weeks. HLP is absorbing that without blowing out. The model is holding."',
        '- "Kaito season 2 window is open. Engagement-to-point ratio is way worse than season 1 -- the farm is crowded now."',
        '- "EigenLayer AVS count just crossed 50 but fee revenue is still near zero. Builder activity ≠ protocol revenue yet."',
        '- "Meteora MET unlock in 48h. $23M worth. If you\'re LP\'ing, watch pool incentive changes this week."',
        "",
        "BAD examples (never write like this):",
        '- "Hyperliquid is looking really strong right now, worth keeping an eye on."',
        '- "DeFi TVL is up this week. Exciting times for the space."',
        '- "This raise could be a game changer for the sector."',
        '- "BTC is up today. Market looking bullish."',
    ]

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Quality validation
# ---------------------------------------------------------------------------

def _validate_quality(text: str) -> tuple[bool, str]:
    """
    Returns (is_valid, reason_if_rejected).

    Checks:
    1. No generic low-value phrases.
    2. Contains at least one specific number or data point.
    3. Minimum length (a post under 60 chars can't say anything substantive).
    """
    lower = text.lower()

    for phrase in _REJECT_PHRASES:
        if phrase in lower:
            return False, f"Contains generic phrase: '{phrase}'"

    has_substance = any(re.search(p, text) for p in _SUBSTANCE_PATTERNS)
    if not has_substance:
        return False, "No specific number, amount, or percentage found -- too vague"

    if len(text.strip()) < 60:
        return False, f"Too short ({len(text)} chars) to say anything substantive"

    return True, ""


# ---------------------------------------------------------------------------
# Fallback template (no API)
# ---------------------------------------------------------------------------

def _fallback_template(item: CandidateItem) -> str:
    if isinstance(item, RaiseItem):
        amt = f"${item.amount:.0f}M" if item.amount else "an undisclosed amount"
        return f"{item.name} raised {amt} ({item.round_name}). Worth watching."
    if isinstance(item, TvlMoverItem):
        direction = "up" if item.change_pct > 0 else "down"
        return f"{item.name} TVL {direction} {abs(item.change_pct):.1f}% in 24h. On-chain flows don't lie."
    return f"{item.title[:220]}."


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate(
    item: CandidateItem,
    portfolio: dict,
    recent_formats: list[str],
    x_conversation: Optional[str] = None,
) -> Optional[str]:
    """
    Generate tweet text for `item`.

    Returns a validated string ready to post, or None if the generated
    text fails quality checks (caller should skip rather than post garbage).
    Falls back to a template only if the API is genuinely unavailable.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        if TEMPLATE_FALLBACK:
            log.warning("ANTHROPIC_API_KEY not set -- using template fallback.")
            return _fallback_template(item)
        raise EnvironmentError("ANTHROPIC_API_KEY is required but not set.")

    topic  = _item_topic(item)
    title  = _item_title(item)

    client        = anthropic.Anthropic(api_key=api_key)
    system_prompt = build_system_prompt(topic=topic, title=title)
    user_prompt   = _user_prompt(item, portfolio, recent_formats, x_conversation)

    try:
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = message.content[0].text.strip()

        # Strip wrapping quotes if Claude added them.
        if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
            text = text[1:-1].strip()

        # Hard character limit.
        if len(text) > 279:
            text = text[:276].rsplit(".", 1)[0] + "."

        # Quality gate -- reject generic output rather than posting slop.
        valid, reason = _validate_quality(text)
        if not valid:
            log.warning("Tweet rejected by quality gate: %s | tweet: %s", reason, text[:80])
            return None

        log.info("Generated tweet (%d chars): %s", len(text), text[:80])
        return text

    except anthropic.APIError as exc:
        log.error("Anthropic API error: %s", exc)
        if TEMPLATE_FALLBACK:
            return _fallback_template(item)
        raise
