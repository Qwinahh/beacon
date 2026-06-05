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
    "significant milestone",
    "exciting development",
    "massive news",
    "the defi space",
    "the crypto space",
    "in the world of",
    "it's worth noting",
    "at the end of the day",
    "paradigm shift",
    "in today's",
    "the latest news",
    "according to reports",
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
    if isinstance(item, FeedItem) and item.kind == "whale":
        return (
            f"Type: whale transaction\n"
            f"Transaction: {item.title}\n"
            f"Context: A large on-chain movement detected by Whale Alert. "
            f"Frame the significance — who is likely moving funds and why, "
            f"what it might signal about sentiment or positioning."
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

import random as _random

_FORMAT_PALETTE = [
    # (format_name, instruction)
    ("data_observation",
     "Write a DATA OBSERVATION post: lead with a specific number or metric, "
     "then state what it actually means for positioning or the narrative. "
     "Example structure: '[Metric] at [number]. [What that implies].'\n"
     "Keep it under 220 chars. Two sentences max."),

    ("contrarian",
     "Write a CONTRARIAN post: push back on a mainstream narrative forming "
     "around this topic. State what the data actually shows vs what people "
     "are saying. Example structure: '[What everyone is saying]. "
     "[What the data actually shows].'\nUnder 200 chars."),

    ("farm_update",
     "Write a FARM/POSITION UPDATE in first-person: share what you're "
     "actually doing with your capital or what you've decided about a farm. "
     "Be specific about the decision and why. Use '(position disclosed)' "
     "if relevant. Example: 'Been LP-ing X for N weeks. [Specific observation]. "
     "[Decision based on it].'\nUnder 200 chars."),

    ("short_take",
     "Write a SHORT PUNCHY TAKE under 150 characters — one sentence that "
     "captures the most important implication. No explanation, no buildup. "
     "Just the sharpest version of the observation. "
     "Example: 'EigenLayer has 50 AVSs now. Fee revenue is still basically zero.'"),

    ("question",
     "Write a QUESTION post that prompts your audience to think or share "
     "their own experience. Must be grounded in the specific data, not vague. "
     "Example: 'MET unlock hits in 48h. How many of you are adjusting LP "
     "positions before it? Curious whether the pool incentive thesis holds.'\n"
     "Under 200 chars."),

    ("pattern_recognition",
     "Write a PATTERN RECOGNITION post: connect this event to a historical "
     "pattern you've seen before. Shows experience. Example: 'New protocol "
     "doing $500M TVL in a week on points. Seen this before. Check where "
     "the TVL goes when points end.'\nUnder 220 chars."),

    ("callout",
     "Write a CALLOUT post: call out something that's being spun, overhyped, "
     "or misrepresented. Be direct but not aggressive. Cite the specific "
     "detail that doesn't add up. Example: Protocol announced 'fair launch' "
     "with 40% to team at TGE. 'Fair' is doing a lot of work there.\n"
     "Under 200 chars."),
]


def _pick_format(recent_formats: list[str]) -> tuple[str, str]:
    """Pick a format not used in the last 2 posts."""
    recent = set((recent_formats or [])[-2:])
    options = [(n, i) for n, i in _FORMAT_PALETTE if n not in recent]
    if not options:
        options = _FORMAT_PALETTE
    return _random.choice(options)


def _user_prompt(
    item: CandidateItem,
    portfolio: dict,
    format_name: str,
    format_instruction: str,
    x_conversation: Optional[str] = None,
) -> str:
    topic  = _item_topic(item)
    title  = _item_title(item)

    item_block      = _build_item_summary(item)
    portfolio_block = _build_portfolio_context(portfolio)
    context_block   = build_writer_context(topic, title, x_conversation)

    parts: list[str] = []

    if context_block:
        parts += [context_block, "---"]

    parts += [
        "## Event to write about",
        "",
        item_block,
    ]

    if portfolio_block:
        parts += ["", portfolio_block]

    parts += [
        "",
        f"## Format directive: {format_name.upper().replace('_', ' ')}",
        "",
        format_instruction,
        "",
        "## Hard constraints (tweet rejected if any are broken)",
        "1. Must contain at least one specific number, dollar amount, percentage, or named mechanic.",
        "2. Must express a take — not just describe what happened.",
        "3. No banned phrases: 'worth watching', 'game changer', 'bullish signal', 'exciting', 'huge'.",
        "4. Under 270 characters. No hashtags. No URLs.",
        "5. Output ONLY the tweet text. No intro, no label, no quotes around it.",
        "",
        "## Real-voice examples (study the tone, not the content)",
        "",
        "GOOD — data observation:",
        "  Hyperliquid OI up 40% to $4.2B in 2 weeks. HLP hasn't blown out. Model holding under real stress.",
        "",
        "GOOD — contrarian:",
        "  Everyone calling Kaito S2 a layup. Engagement-to-point ratio is 3x worse than S1. Farm is crowded.",
        "",
        "GOOD — farm update:",
        "  Been LP'ing Meteora for 6 weeks. MET unlock hits in 48h — watching pool incentives before I adjust. (position disclosed)",
        "",
        "GOOD — short take:",
        "  EigenLayer has 50 AVSs now. Fee revenue still basically zero.",
        "",
        "GOOD — callout:",
        "  Protocol announced 'fair launch' with 40% to team at TGE. 'Fair' is doing a lot of work there.",
        "",
        "BAD (never write like these):",
        "  Hyperliquid is looking really strong right now, worth keeping an eye on.",
        "  DeFi TVL is up this week. Exciting times for the space.",
        "  This raise could be a game changer for the sector.",
        "  The latest developments in the crypto space are very promising.",
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
) -> tuple[Optional[str], Optional[str]]:
    """
    Generate tweet text for `item`.

    Returns (text, format_name) — text is None if the quality gate rejected it.
    Caller should record format_name in state regardless of whether text is None.
    Falls back to (template_text, "fallback") if the API is unavailable.
    """
    # Pick format before any API calls so we can return it even on failure.
    format_name, _format_instruction = _pick_format(recent_formats)

    topic  = _item_topic(item)
    title  = _item_title(item)

    system_prompt = build_system_prompt(topic=topic, title=title)
    user_prompt   = _user_prompt(item, portfolio, format_name, _format_instruction, x_conversation)

    # Use the unified LLM layer: Groq → Cerebras → OpenRouter → Anthropic
    from bot.brain.llm import complete as llm_complete, get_active_provider
    log.debug("LLM provider: %s", get_active_provider())

    text = llm_complete(
        system=system_prompt,
        user=user_prompt,
        max_tokens=CLAUDE_MAX_TOKENS,
        temperature=0.85,
    )

    if text is None:
        log.error("All LLM providers failed — using template fallback")
        if TEMPLATE_FALLBACK:
            return _fallback_template(item), "fallback"
        return None, format_name

    text = text.strip()

    # Strip wrapping quotes if the model added them.
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        text = text[1:-1].strip()

    # Hard character limit.
    if len(text) > 279:
        text = text[:276].rsplit(".", 1)[0] + "."

    # Quality gate -- reject generic output rather than posting slop.
    valid, reason = _validate_quality(text)
    if not valid:
        log.warning("Tweet rejected by quality gate: %s | tweet: %s", reason, text[:80])
        return None, format_name

    log.info("Generated tweet (%d chars) [%s]: %s", len(text), format_name, text[:80])
    return text, format_name
