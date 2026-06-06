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
from bot.sources.dropstab import UnlockItem
from bot.sources.rss import FeedItem
from bot.sources.whale_alert import WhaleItem

log = logging.getLogger(__name__)

CandidateItem = Union[FeedItem, RaiseItem, TvlMoverItem, WhaleItem, UnlockItem]

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
    # AI-sounding phrases
    "worth noting that",
    "it is worth noting",
    "as we can see",
    "as mentioned",
    "this is significant",
    "this represents a significant",
    "the broader",
    "the overall",
    "in the realm of",
    "the landscape",
    "this highlights",
    "this underscores",
    "this demonstrates",
    "plays a crucial role",
    "moving forward",
    "going forward",
    "it remains to be seen",
    "only time will tell",
    "the fact remains",
    "it is important to note",
    "needless to say",
    "it goes without saying",
]

# AI-sounding openers — reject if the tweet starts with any of these
_REJECT_OPENERS = [
    "as ",           # "As funding rates..."
    "in light of",
    "given that",
    "it's worth",
    "it is worth",
    "with the recent",
    "following the recent",
    "amid growing",
    "amid the",
    "in the wake of",
    "building on",
]


def _has_bad_opener(text: str) -> bool:
    """Return True if the tweet starts with an AI-sounding opener."""
    lower = text.lower().strip()
    return any(lower.startswith(opener) for opener in _REJECT_OPENERS)


# Patterns that look like press-release headlines — reject these.
_HEADLINE_PATTERNS = [
    r"^[A-Z][^.!?]*raises \$",       # "[Project] raises $X"
    r"^[A-Z][^.!?]*launches ",        # "[Project] launches [thing]"
    r"^[A-Z][^.!?]*announces ",       # "[Project] announces [thing]"
    r"^[A-Z][^.!?]*partners with ",   # "[Project] partners with [X]"
    r"^breaking:",                     # "Breaking:"
    r"^just in:",                      # "Just in:"
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
    if isinstance(item, WhaleItem):
        return (
            f"Type: whale transaction\n"
            f"Summary: {item.summary()}\n"
            f"Chain: {item.chain}\n"
            f"Amount: ${item.amount_usd / 1_000_000:.1f}M USD\n"
            f"From: {item.from_name or item.from_type}\n"
            f"To: {item.to_name or item.to_type}"
        )
    if isinstance(item, UnlockItem):
        usd_str = f" (~${item.amount_usd / 1_000_000:.1f}M)" if item.amount_usd else ""
        return (
            f"Type: token unlock event\n"
            f"Project: {item.project} ({item.symbol})\n"
            f"Amount: {item.amount_tokens:,.0f} tokens{usd_str}\n"
            f"Unlocks in: {item.days_until:.1f} days\n"
            f"Recipient: {item.recipient}\n"
            f"Type: {item.unlock_type}"
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

    ("hot_take",
     "Write a HOT TAKE: your actual opinion on what this means for the space, "
     "traders, or protocol users. First person. Specific. Willing to be wrong. "
     "Example: 'Everyone is bullish on EigenLayer restaking but the AVS demand "
     "side is still basically zero. Restaking a yield with no actual users is "
     "just a longer-dated risk.'\nUnder 220 chars. Must be a take, not a fact."),

    ("alpha_tip",
     "Write an ALPHA TIP: what someone should actually DO based on this information. "
     "Specific action, specific timing, specific reasoning. First person or second person. "
     "Example: 'If you're farming Hyperliquid, check your open referral slots — "
     "they reset monthly and most people are leaving points on the table.'\n"
     "Under 200 chars. Must be actionable, not just observational."),

    ("thread_hook",
     "Write a THREAD HOOK — the first tweet of a thread that makes people want "
     "to read more. End with a thread emoji (this one time only — threads justify it). "
     "State a specific observation or tension that demands explanation. "
     "Example: 'Hyperliquid just did $200B in monthly volume. It has 12 employees. "
     "Here's what that actually means for every other perp DEX'\n"
     "Under 200 chars. Must create genuine curiosity about what comes next."),
]


_FORMAT_EXAMPLES: dict[str, list[str]] = {
    "data_observation": [
        "HL OI $4.2B but HLP util at 34%. More parked capital than traders to absorb it. Spreads stay wide.",
        "ETH funding negative on perps while spot holds. Someone's hedging something large. Not a direction call — just unusual.",
        "Meteora pool emissions down 40% this week. Starting to see some TVL rotate. Worth watching if you're LP-ing.",
    ],
    "contrarian": [
        "Everyone pointing at Hyperliquid volume. Not seeing anyone talk about the HLP composition risk if OI spikes again.",
        "Restaking narrative is running 6 months ahead of actual AVS demand. TVL without buyers on the other side is just a timer.",
        "The 'DeFi is back' posts are real but the revenue is concentrated in 3 protocols. Everything else is still bleeding users.",
    ],
    "farm_update": [
        "Been wrong on Kaito timing. S2 rewards 3x worse per engagement than S1. Should have sized down earlier. Still net positive, barely.",
        "6 weeks LP on Meteora. IL worse than I modelled but fee income covering it so far. Holding unless pool incentives change.",
        "Exiting my EigenLayer position. AVS revenue still basically zero and the unlock pressure is getting real.",
    ],
    "short_take": [
        "The number of 'Hyperliquid killers' is inversely correlated with their actual volume.",
        "Airdrop meta is just: farm early, exit before the crowd realises the math doesn't work. Repeat.",
        "Most DeFi TVL is protocol-owned liquidity dressed up as organic demand. Know the difference.",
    ],
    "question": [
        "HL OI at ATH but retail sentiment still cautious. Who's taking the other side right now?",
        "How many of you are actually profitable net of IL on Meteora positions this year? Genuinely curious.",
        "Restaking TVL up but no AVS is generating meaningful fees. At what point does the narrative need revenue to survive?",
    ],
    "pattern_recognition": [
        "New protocol doing $500M TVL in a week on points. Seen this. Check where TVL goes when points end.",
        "This is the 3rd time this cycle a new DEX launched with 'zero fees forever'. Both previous ones ended the same way.",
        "Airdrop criteria leaked 2 weeks before snapshot. Farm getting crowded fast. This is how S1 Kaito played out.",
    ],
    "callout": [
        "Protocol announced 'fair launch' with 40% to team at TGE. 'Fair' is doing a lot of work in that sentence.",
        "The TVL number everyone is citing includes $800M of their own protocol incentives. Strip that and it's a different story.",
        "Airdrop eligibility criteria changed 3 times this month. The criteria that gets announced isn't always the one that matters.",
    ],
}


def _pick_format(recent_formats: list[str]) -> tuple[str, str]:
    """Pick a format, weighted by past engagement. Avoids last 2 used."""
    from bot.brain.format_weights import get_weights
    recent = set((recent_formats or [])[-2:])
    options = [(n, i) for n, i in _FORMAT_PALETTE if n not in recent]
    if not options:
        options = _FORMAT_PALETTE
    weights = get_weights()
    w = [weights.get(n, 1.0) for n, _ in options]
    return _random.choices(options, weights=w, k=1)[0]


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

    # Inject few-shot examples for the selected format
    examples = _FORMAT_EXAMPLES.get(format_name, [])
    if examples:
        example_lines = "\n".join(f'  "{ex}"' for ex in examples[:2])
        parts.append(
            f"Examples of GOOD {format_name.upper().replace('_', ' ')} posts "
            f"(match this voice exactly — do not copy content, copy tone):\n"
            f"{example_lines}"
        )

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
        "## Your task",
        "",
        "1. Run the editorial test from the system prompt.",
        "   -- If there is a valid reason (A-F) to post this, state it on line 1.",
        "   -- If not, respond with exactly: SKIP",
        "",
        f"2. If posting, use this format style: {format_name.upper().replace('_', ' ')}",
        f"   {format_instruction}",
        "",
        "## Output format (two lines only)",
        "REASON: [A/B/C/D/E/F] -- [one sentence: what specific value does this give the reader]",
        "[tweet text]",
        "",
        "Or: SKIP",
        "",
        "## Hard constraints on the tweet",
        "- Must contain at least one specific number, percentage, dollar amount, or named mechanic",
        "- Must express a take -- not just describe what happened",
        "- Under 270 characters. No hashtags. No URLs. No quotes around the output.",
        "",
        "## Examples of the output format",
        "",
        "REASON: B -- Hyperliquid OI is up 40% but HLP utilisation is low, giving traders an edge on timing",
        "Hyperliquid OI up 40% to $4.2B. HLP utilisation still at 34%. More capital than flow to absorb it.",
        "",
        "REASON: C -- Kaito S2 farm math is 3x worse than S1 so people farming blind are wasting capital",
        "Everyone calling Kaito S2 a layup. Engagement-to-point ratio is 3x worse than S1. Farm is crowded.",
        "",
        "REASON: E -- MET unlock in 48h is time-sensitive for anyone currently LP-ing Meteora",
        "Been LP'ing Meteora 6 weeks. MET unlock in 48h -- watching pool incentive changes before I adjust. (position disclosed)",
        "",
        "REASON: F -- EigenLayer AVS count vs zero fee revenue is a contrarian data point vs the hype",
        "EigenLayer has 50 AVSs now. Fee revenue still basically zero.",
        "",
        "SKIP",
        "(used when: generic news, no specific implication, nothing that changes how someone would position)",
    ]

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Quality validation
# ---------------------------------------------------------------------------

def _is_headline(text: str) -> bool:
    """Return True if the tweet reads like a press-release headline."""
    for pattern in _HEADLINE_PATTERNS:
        if re.match(pattern, text.strip(), re.IGNORECASE):
            return True
    return False


def _validate_quality(text: str, format_name: str = "") -> tuple[bool, str]:
    """
    Returns (is_valid, reason_if_rejected).

    Checks:
    1. No generic low-value phrases.
    2. Not a press-release headline.
    3. Contains at least one specific number or data point.
       (Skipped for format_name="thread_hook" — hooks are questions/claims, not data dumps.)
    4. Minimum length (a post under 60 chars can't say anything substantive).
    """
    lower = text.lower()

    for phrase in _REJECT_PHRASES:
        if phrase in lower:
            return False, f"Contains generic phrase: '{phrase}'"

    if _has_bad_opener(text):
        return False, "AI-sounding opener"

    if _is_headline(text):
        return False, "Reads like a news headline — add angle or implication"

    if format_name != "thread_hook":
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
        lead = f" Lead: {item.category}." if item.category else ""
        return f"{item.name} raised {amt} ({item.round_name}).{lead}"
    if isinstance(item, TvlMoverItem):
        direction = "up" if item.change_pct > 0 else "down"
        return f"{item.name} TVL {direction} {abs(item.change_pct):.1f}% in 24h to ${item.tvl_usd/1e6:.0f}M."
    if isinstance(item, WhaleItem):
        return item.summary()
    if isinstance(item, UnlockItem):
        return item.summary()
    return f"{item.title[:240]}"


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

    # Handle editorial SKIP -- model decided there's no reason to post this.
    if text.upper().startswith("SKIP"):
        log.info("Writer editorial test: no valid reason to post this item. Skipping.")
        return None, format_name

    # Parse two-line output: "REASON: X -- explanation\ntweet text"
    lines = text.splitlines()
    if lines and lines[0].upper().startswith("REASON:"):
        reason_line = lines[0]
        # Extract letter and explanation for logging
        reason_part = reason_line[len("REASON:"):].strip()
        log.info("Editorial reason: %s", reason_part[:80])
        # The tweet is everything after the REASON line
        text = "\n".join(lines[1:]).strip()
    else:
        # Model didn't follow the format -- treat the whole output as the tweet
        log.debug("Writer did not output REASON line -- using full output as tweet.")

    # Strip wrapping quotes if the model added them.
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        text = text[1:-1].strip()

    if not text:
        log.warning("Writer returned empty tweet after parsing.")
        return None, format_name

    # Hard character limit.
    if len(text) > 279:
        text = text[:276].rsplit(".", 1)[0] + "."

    # Quality gate -- reject generic output rather than posting slop.
    valid, reject_reason = _validate_quality(text)
    if not valid:
        log.warning("Tweet rejected by quality gate: %s | tweet: %s", reject_reason, text[:80])
        return None, format_name

    # AUTHENTICITY GATE — second-pass LLM check for AI-sounding content.
    from bot.brain.authenticity_judge import passes as judge_passes
    ok, judge_result = judge_passes(text, content_type="post")
    if not ok:
        feedback = judge_result.get("feedback", "")
        if feedback and feedback != "NONE":
            log.info("Retrying with judge feedback: %s", feedback)
            retry_prompt = user_prompt + f"\n\nIMPORTANT FIX NEEDED: {feedback}\nRewrite to fix this specifically."
            retry_raw = llm_complete(
                system=system_prompt,
                user=retry_prompt,
                max_tokens=CLAUDE_MAX_TOKENS,
                temperature=0.85,
            )
            if retry_raw:
                retry_text = retry_raw.strip()
                if len(retry_text) >= 2 and retry_text[0] == '"' and retry_text[-1] == '"':
                    retry_text = retry_text[1:-1].strip()
                if len(retry_text) > 279:
                    retry_text = retry_text[:276].rsplit(".", 1)[0] + "."
                retry_valid, _ = _validate_quality(retry_text)
                if retry_valid:
                    ok2, _ = judge_passes(retry_text, content_type="post")
                    if ok2:
                        log.info("Retry passed authenticity judge")
                        return retry_text, format_name
        log.info("Post failed authenticity judge after retry — skipping")
        return None, format_name

    log.info("Generated tweet (%d chars) [%s]: %s", len(text), format_name, text[:80])
    return text, format_name


# ---------------------------------------------------------------------------
# Thread writer
# ---------------------------------------------------------------------------

_THREAD_WRITER_SYSTEM = """\
You write Twitter threads for @Qwinahh — a crypto account that trades perps,
farms airdrops, and moves into DeFi protocols before narratives form.
The audience: people who are actively farming, trading, or watching the same protocols.

EDITORIAL TEST — before writing, ask: does this topic have enough substance to fill
3 meaningful, non-repetitive tweets? Valid reasons to thread:

  A. A multi-part argument that loses its logic when compressed to one tweet.
  B. Data with 3+ distinct implications — each worth its own sentence.
  C. Pattern + historical parallel + what to watch now — each a separate tweet.
  D. A contrarian view that needs evidence tweets to be credible, not just asserted.

If the topic can be said in one tweet: SKIP.

THREAD STRUCTURE:
- Tweet 1 (HOOK): A specific question, contrarian claim, or surprising fact.
  Under 180 chars. Creates tension. Must make someone want to read the rest.
  NOT a data dump. A thread emoji (🧵) is allowed here if it fits naturally.
- Tweets 2-4 (ARGUMENT): One specific point per tweet. Numbers, mechanics, implications.
  Each under 270 chars. First person where it adds credibility.
  Each tweet must add something the previous didn't say — no restatement.
- Last tweet (CONCLUSION): The implication or what to watch next.
  A soft CTA is fine ("watching X this week", "will update when..."). Under 270 chars.

VOICE: Direct. Specific. Opinionated. No "the DeFi ecosystem", no "it's worth noting",
no hedged opinions ("could be", "might mean"). You have money in these protocols.
Write like it.

OUTPUT FORMAT:
REASON: [A/B/C/D] -- [why this warrants a thread, not just one tweet]
1. [hook — under 180 chars]
2. [argument — under 270 chars]
3. [argument — under 270 chars]
4. [conclusion — under 270 chars]

Or: SKIP
"""


def _thread_user_prompt(
    item: Optional[CandidateItem],
    portfolio: dict,
    x_conversation: Optional[str] = None,
) -> str:
    portfolio_block = _build_portfolio_context(portfolio)

    if item is not None:
        topic  = _item_topic(item)
        title  = _item_title(item)
        data_section = "## Event to build a thread about\n\n" + _build_item_summary(item)
        context_block = build_writer_context(topic, title, x_conversation)
    else:
        # Freeform thread — no specific event, draw from current thinking and vault context
        data_section = (
            "## Thread topic\n\n"
            "No specific event. Write from your current observations about DeFi, "
            "perps, airdrops, or the protocols you're tracking. Pick the topic "
            "that has the most substance right now."
        )
        context_block = build_writer_context("", "", x_conversation)

    parts: list[str] = []
    if context_block:
        parts += [context_block, "---"]

    parts.append(data_section)

    if portfolio_block:
        parts += ["", portfolio_block]

    parts += [
        "",
        "## Hard constraints on every tweet in the thread",
        "- No hashtags. No URLs. No quotes around output.",
        "- Tweets 2+ must contain at least one specific number, percentage, "
        "dollar amount, or named mechanic.",
        "- Hook under 180 chars. All other tweets under 270 chars.",
        "- Thread emoji on tweet 1 is the ONLY emoji allowed in the whole thread.",
        "- If the topic can be said in one tweet, respond with SKIP.",
    ]

    return "\n".join(parts)


def _parse_thread_tweets(raw: str) -> list[str]:
    """
    Parse numbered tweets from thread LLM output.

    Handles: "1. text", "1/ text", "Tweet 1: text", "1) text"
    Skips REASON: lines and SKIP responses.
    Joins continuation lines (non-numbered lines after a numbered one).
    """
    tweets: list[str] = []
    current: list[str] = []

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.upper().startswith(("REASON:", "SKIP")):
            continue

        m = re.match(r'^(?:tweet\s*)?\d+\s*[./:)]\s*', line, re.IGNORECASE)
        if m:
            if current:
                tweets.append(" ".join(current).strip())
                current = []
            rest = line[m.end():].strip()
            if rest:
                current.append(rest)
        elif current:
            # Continuation of the current numbered tweet
            current.append(line)

    if current:
        tweets.append(" ".join(current).strip())

    return [t for t in tweets if t]


def generate_thread(
    item: Optional[CandidateItem],
    portfolio: dict,
    recent_formats: list[str],
    x_conversation: Optional[str] = None,
) -> Optional[list[str]]:
    """
    Generate a 3-5 tweet thread.

    item may be None — in that case the thread draws from vault context
    (freeform mode). When provided, the thread is built around the item.

    Returns a list of 3-5 tweet strings or None if rejected.
    Validates each tweet individually: the hook uses format_name="thread_hook"
    (skips substance gate); body tweets require the full quality gate.
    Runs authenticity judge on tweet 1 only; retries once with feedback.
    """
    from bot.brain.llm import complete as llm_complete, get_active_provider
    log.debug("Thread writer — LLM: %s", get_active_provider())

    system_prompt = _THREAD_WRITER_SYSTEM
    user_prompt   = _thread_user_prompt(item, portfolio, x_conversation)

    raw = llm_complete(
        system=system_prompt,
        user=user_prompt,
        max_tokens=800,
        temperature=0.85,
    )

    if raw is None:
        log.debug("Thread writer: LLM returned None")
        return None

    raw = raw.strip()
    if raw.upper().startswith("SKIP"):
        log.info("Thread writer: editorial SKIP")
        return None

    tweets = _parse_thread_tweets(raw)
    if not tweets or len(tweets) < 3:
        log.debug("Thread writer: only %d tweets parsed — need at least 3", len(tweets) if tweets else 0)
        return None

    tweets = tweets[:5]  # Cap at 5 even if the model went longer

    return _validate_and_judge_thread(tweets, system_prompt, user_prompt)


def _validate_and_judge_thread(
    tweets: list[str],
    system_prompt: str,
    user_prompt: str,
) -> Optional[list[str]]:
    """Validate, length-cap, and judge a parsed tweet list. Returns cleaned list or None."""
    from bot.brain.llm import complete as llm_complete

    # Length-cap every tweet before validation
    capped: list[str] = []
    for t in tweets:
        if len(t) > 279:
            t = t[:276].rsplit(".", 1)[0] + "."
        capped.append(t)

    # Validate hook with substance gate bypassed
    hook_valid, reason = _validate_quality(capped[0], format_name="thread_hook")
    if not hook_valid:
        log.debug("Thread hook failed quality gate: %s | %s", reason, capped[0][:60])
        return None

    # Validate body tweets with full quality gate; stop accumulating on first failure
    validated: list[str] = [capped[0]]
    for i, tweet in enumerate(capped[1:], start=2):
        v, r = _validate_quality(tweet)
        if not v:
            log.debug("Thread tweet %d failed quality: %s | %s", i, r, tweet[:60])
            break
        validated.append(tweet)

    if len(validated) < 3:
        log.debug("Thread: only %d tweets passed quality gate — need 3", len(validated))
        return None

    # Authenticity judge on hook only — hook quality determines the whole thread's fate
    from bot.brain.authenticity_judge import passes as judge_passes
    ok, judge_result = judge_passes(validated[0], content_type="post")
    if not ok:
        feedback = judge_result.get("feedback", "")
        if feedback and feedback != "NONE":
            log.info("Thread hook failed judge — retrying with feedback: %s", feedback)
            retry_prompt = (
                user_prompt
                + f"\n\nIMPORTANT: The hook tweet failed the authenticity check. Fix: {feedback}\n"
                "Rewrite the full thread with a stronger hook."
            )
            retry_raw = llm_complete(
                system=system_prompt,
                user=retry_prompt,
                max_tokens=800,
                temperature=0.85,
            )
            if retry_raw:
                retry_tweets = _parse_thread_tweets(retry_raw.strip())
                if retry_tweets and len(retry_tweets) >= 3:
                    retry_tweets = retry_tweets[:5]
                    retry_capped = []
                    for t in retry_tweets:
                        if len(t) > 279:
                            t = t[:276].rsplit(".", 1)[0] + "."
                        retry_capped.append(t)

                    h_valid, _ = _validate_quality(retry_capped[0], format_name="thread_hook")
                    if h_valid:
                        ok2, _ = judge_passes(retry_capped[0], content_type="post")
                        if ok2:
                            retry_validated = [retry_capped[0]]
                            for tweet in retry_capped[1:]:
                                v, _ = _validate_quality(tweet)
                                if not v:
                                    break
                                retry_validated.append(tweet)
                            if len(retry_validated) >= 3:
                                log.info(
                                    "Thread retry passed judge (%d tweets): %s",
                                    len(retry_validated), retry_validated[0][:70],
                                )
                                return retry_validated

        log.info("Thread hook failed authenticity judge after retry — skipping")
        return None

    log.info("Generated thread (%d tweets): %s", len(validated), validated[0][:70])
    return validated
