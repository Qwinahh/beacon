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
    # AI-sounding additions
    "worth noting that",
    "it is worth noting",
    "as we can see",
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
    "it is important to note",
    "needless to say",
    "it goes without saying",
]

# AI-sounding openers — reject if the tweet starts with any of these.
_REJECT_OPENERS = [
    "as ",           # "As funding rates rise..."
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

    ("mistake_admission",
     "Write a MISTAKE ADMISSION — be specific about what you got wrong, the cost, "
     "and what you learned. Genuine, first-person, no self-pity. "
     "These perform extremely well because authenticity is rare on CT. "
     "Example: 'Got the Kaito farm timing wrong. Held into S2 which pays 3x worse. "
     "Net positive but barely. Should have rotated earlier.'\n"
     "Under 180 chars. Must reference a specific decision, not vague regret."),

    ("prediction",
     "Write a PREDICTION — a specific, testable, time-stamped call based on the data. "
     "Predictions create future engagement when they land (or don't). "
     "Be specific: name the protocol, give a timeframe, and state what you expect. "
     "Example: 'Calling it: [Protocol] TVL halves within 45 days of incentives ending.'\n"
     "Under 180 chars. Must be falsifiable. No vague 'watch this space' hedging."),
]


# Authentic examples per format — injected into every LLM call as few-shot anchors.
# Match the VOICE, not the content. Two examples per format.
_FORMAT_EXAMPLES: dict[str, list[str]] = {
    "data_observation": [
        "HL OI $4.2B but HLP util at 34%. More parked capital than traders to absorb it. Spreads stay wide.",
        "ETH funding negative on perps while spot holds. Someone's hedging something large. Not a direction call — just unusual.",
    ],
    "contrarian": [
        "Everyone pointing at Hyperliquid volume. Not seeing anyone talk about the HLP composition risk if OI spikes again.",
        "Restaking narrative is running 6 months ahead of actual AVS demand. TVL without buyers on the other side is just a timer.",
    ],
    "hot_take": [
        "Perp DEXs have been saying CEXs are finished for 3 years. Hyperliquid is the first one making it actually true.",
        "Points farming is just an unregulated ICO with extra steps. The SEC figured this out eventually with ICOs.",
    ],
    "farm_update": [
        "Been wrong on Kaito timing. S2 rewards 3x worse per engagement than S1. Should have sized down earlier. Still net positive, barely.",
        "6 weeks LP on Meteora. IL worse than I modelled but fee income covering it so far. Holding unless pool incentives change.",
    ],
    "pattern_recognition": [
        "New protocol doing $500M TVL in a week on points. Seen this. Check where TVL goes when points end.",
        "This is the 3rd time this cycle a new DEX launched with 'zero fees forever'. Both previous ones ended the same way.",
    ],
    "question": [
        "HL OI at ATH but retail sentiment still cautious. Who's taking the other side right now?",
        "How many of you are actually profitable net of IL on Meteora positions this year? Genuinely curious.",
    ],
    "callout": [
        "Protocol announced 'fair launch' with 40% to team at TGE. 'Fair' is doing a lot of work in that sentence.",
        "The TVL number everyone is citing includes $800M of their own protocol incentives. Strip that and it's a different story.",
    ],
    "alpha_tip": [
        "If you're farming Meteora, the high-volume pairs are generating 2-3x the fees of the incentivised ones. Check the actual APR not the listed one.",
        "Hyperliquid referral slots reset monthly. Most people aren't checking. Leaving points on the table.",
    ],
    "thread_hook": [
        "Hyperliquid just processed $200B in volume with 12 employees. Here's what that actually means for every other perp DEX",
        "I've been farming DeFi for 3 years. The protocols that are still here all have one thing in common",
    ],
    "short_take": [
        "The number of 'Hyperliquid killers' is inversely correlated with their actual volume.",
        "Airdrop meta is just: farm early, exit before the crowd realises the math doesn't work. Repeat.",
    ],
    "mistake_admission": [
        "Got the Kaito timing wrong. Held too long into S2. Rewards 3x worse than S1. Net positive but barely.",
        "Sized into the farm too late. TVL was already 3x what makes the math work. Down net after gas. Moving on.",
    ],
    "prediction": [
        "Calling it: this protocol's TVL halves within 60 days of incentives ending. Marking the date.",
        "This farm is 6 weeks from being too crowded to be worth entering. Noting it now.",
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

    if context_block:
        parts += [context_block, "---"]

    parts += [
        "## Event to write about",
        "",
        item_block,
    ]

    if portfolio_block:
        parts += ["", portfolio_block]

    # Inject few-shot voice examples for the chosen format
    examples = _FORMAT_EXAMPLES.get(format_name, [])
    if examples:
        ex_lines = "\n".join(f'  "{ex}"' for ex in examples)
        parts += [
            "",
            f"## Voice examples for {format_name.upper().replace('_', ' ')} (match tone, not content)",
            ex_lines,
        ]

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
    3. Contains at least one specific number or data point (skipped for opinion formats).
    4. Minimum length (a post under 60 chars can't say anything substantive).

    Opinion formats (hot_take, short_take, thread_hook, comparison, prediction)
    express views and don't need a number — skipping the substance gate for them
    prevents the quality filter from silently preferring TVL/data posts.
    """
    # Formats where a pure opinion is valid — no number required.
    _OPINION_FORMATS = {
        "hot_take", "short_take", "thread_hook",
        "comparison", "prediction", "contrarian",
        "callout", "question", "mistake_admission",
    }

    lower = text.lower()

    for phrase in _REJECT_PHRASES:
        if phrase in lower:
            return False, f"Contains generic phrase: '{phrase}'"

    if _has_bad_opener(text):
        return False, "AI-sounding opener — start with the fact or implication"

    if _is_headline(text):
        return False, "Reads like a news headline — add angle or implication"

    if format_name not in _OPINION_FORMATS:
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
    valid, reject_reason = _validate_quality(text, format_name=format_name)
    if not valid:
        log.warning("Tweet rejected by quality gate: %s | tweet: %s", reject_reason, text[:80])
        return None, format_name

    # Authenticity gate — second LLM pass to catch AI-sounding output.
    try:
        from bot.brain.authenticity_judge import passes as judge_passes
        ok, judge_result = judge_passes(text, content_type="post")
        if not ok:
            feedback = judge_result.get("feedback", "")
            if feedback and feedback.upper() != "NONE":
                log.info("Authenticity failed — retrying with feedback: %s", feedback)
                retry_prompt = user_prompt + (
                    f"\n\nIMPORTANT: The previous draft failed the authenticity check.\n"
                    f"Specific fix needed: {feedback}\n"
                    f"Rewrite to fix this. Keep it under 220 chars."
                )
                retry_raw = llm_complete(
                    system=system_prompt,
                    user=retry_prompt,
                    max_tokens=CLAUDE_MAX_TOKENS,
                    temperature=0.88,
                )
                if retry_raw:
                    retry_raw = retry_raw.strip()
                    if not retry_raw.upper().startswith("SKIP"):
                        retry_lines = retry_raw.splitlines()
                        if retry_lines and retry_lines[0].upper().startswith("REASON:"):
                            retry_raw = "\n".join(retry_lines[1:]).strip()
                        if len(retry_raw) >= 2 and retry_raw[0] == '"' and retry_raw[-1] == '"':
                            retry_raw = retry_raw[1:-1].strip()
                        if retry_raw and len(retry_raw) > 30:
                            ok2, _ = judge_passes(retry_raw, content_type="post")
                            if ok2:
                                log.info("Retry passed authenticity judge")
                                text = retry_raw
                            else:
                                log.info("Retry also failed authenticity — skipping")
                                return None, format_name
                        else:
                            return None, format_name
                    else:
                        return None, format_name
                else:
                    return None, format_name
            else:
                log.info("Post failed authenticity judge (no feedback) — skipping")
                return None, format_name
    except Exception as exc:
        log.warning("Authenticity judge raised: %s — proceeding without it", exc)

    log.info("Generated tweet (%d chars) [%s]: %s", len(text), format_name, text[:80])
    return text, format_name


# ---------------------------------------------------------------------------
# Thread continuation
# ---------------------------------------------------------------------------

_THREAD_SYSTEM = """You are writing the continuation tweets of a thread for @Qwinahh -- a crypto
account that trades perps, farms airdrops, and moves into DeFi protocols
before narratives form.

The first tweet (the hook) has already been posted. Your job: write 2-3
follow-up tweets that deliver the promised substance.

THREAD RULES:
- Each tweet must be a self-contained insight, not just a sentence fragment
- The thread should read: hook -> data/context -> implication/takeaway
- Number them: start each with the tweet number (2/, 3/, 4/)
- Under 260 chars each
- No hashtags, no emojis (thread emoji was already used in the hook)
- The last tweet should have a concrete takeaway or opinion

OUTPUT FORMAT (exactly):
2/ [second tweet]
3/ [third tweet]
4/ [fourth tweet if needed]

Two tweets minimum, three maximum. Do not include the first tweet.
"""


def generate_thread_continuation(
    hook_text: str,
    item: CandidateItem,
    portfolio: dict,
) -> list[str]:
    """
    Given the already-posted hook tweet, generate 2-3 continuation tweets.

    Returns a list of tweet strings (not including the hook).
    Returns empty list on failure -- thread stops at hook.
    """
    topic  = _item_topic(item)
    title  = _item_title(item)
    item_summary = _build_item_summary(item)

    user_prompt = (
        f"Hook tweet already posted:\n\n\"{hook_text}\"\n\n"
        f"The item that triggered this thread:\n{item_summary}\n\n"
        f"Topic: {topic} | Title: {title}\n\n"
        "Write 2-3 follow-up tweets (numbered 2/, 3/, 4/) that deliver the substance "
        "promised by the hook. Each tweet must give a DeFi trader or airdrop farmer "
        "a specific, actionable insight. Under 260 chars each."
    )

    from bot.brain.llm import complete as llm_complete
    try:
        raw = llm_complete(
            system=_THREAD_SYSTEM,
            user=user_prompt,
            max_tokens=400,
            temperature=0.80,
        )
    except Exception as exc:
        log.warning("Thread continuation LLM call failed: %s", exc)
        return []

    if not raw:
        return []

    # Parse numbered tweets
    tweets: list[str] = []
    for line in raw.strip().splitlines():
        line = line.strip()
        # Match "2/ ...", "3/ ...", "4/ ..."
        if len(line) >= 3 and line[0].isdigit() and line[1] == "/":
            tweet_text = line[2:].strip()
            if 20 <= len(tweet_text) <= 280:
                tweets.append(tweet_text)

    log.info("Thread continuation: %d follow-up tweets generated.", len(tweets))
    return tweets[:3]  # Hard cap at 3 follow-ups


# ---------------------------------------------------------------------------
# Standalone thread generation (no specific news item)
# ---------------------------------------------------------------------------

_FULL_THREAD_SYSTEM = """You write a complete thread (3-5 tweets) for @Qwinahh -- a DeFi
trader who farms airdrops, trades perps, and moves into protocols early.

There is no specific news event driving this thread. Pick ONE thing from your
current thinking (a thesis, a pattern, a mistake, a metric) and walk through it
properly -- something that needs more than 280 characters to land.

THREAD STRUCTURE:
- Tweet 1 is the HOOK: state a specific observation or tension that demands
  explanation. End it with a thread emoji (this one time only).
- Tweets 2-4 deliver the substance: data/context, then the implication or
  takeaway. Each tweet must be a self-contained insight, not a fragment.
- The last tweet should land on a concrete takeaway or opinion -- not "stay tuned"
  or a call to follow.

HARD RULES:
- 3-5 tweets total.
- Each tweet under 260 characters.
- No hashtags. No emojis except the single thread emoji on tweet 1.
- No generic takes. If you don't have something specific enough for a thread, SKIP.

OUTPUT FORMAT (exactly, one line per tweet):
1/ [hook]
2/ [tweet]
3/ [tweet]
4/ [tweet, optional]
5/ [tweet, optional]

Or: SKIP
"""


def generate_thread(
    item: Optional[CandidateItem],
    portfolio: dict,
    recent_formats: list[str],
) -> list[str]:
    """
    Generate a complete 3-5 tweet thread with no specific news item driving it.

    Returns a list of tweet strings (hook first), or an empty list if the
    LLM SKIPs, fails, or the output doesn't parse into at least 3 tweets.
    Never raises -- caller falls through to freeform/normal pipeline on [].
    """
    try:
        from bot.brain.freeform_writer import _load_vault_context
        from bot.brain.llm import complete as llm_complete

        vault_context = _load_vault_context()
        portfolio_context = _build_portfolio_context(portfolio)
        recent = ", ".join((recent_formats or [])[-5:]) or "none"

        context_block = (
            f"Context from your vault:\n{vault_context}\n\n---\n\n"
            if vault_context else ""
        )
        portfolio_block = (
            f"{portfolio_context}\n\n---\n\n" if portfolio_context else ""
        )

        user_prompt = (
            f"{context_block}"
            f"{portfolio_block}"
            f"Recent formats you've used (avoid repeating the angle): {recent}\n\n"
            "Write a complete 3-5 tweet thread per the rules. If nothing in your "
            "context is substantial enough for a thread -- SKIP."
        )

        raw = llm_complete(
            system=_FULL_THREAD_SYSTEM,
            user=user_prompt,
            max_tokens=CLAUDE_MAX_TOKENS * 2,
            temperature=0.85,
        )
    except Exception as exc:
        log.warning("Thread generation failed: %s", exc)
        return []

    if not raw:
        return []

    raw = raw.strip()
    if raw.upper().startswith("SKIP"):
        log.debug("Thread generation: SKIP")
        return []

    tweets: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        # Match "1/ ...", "2/ ...", ... "5/ ..."
        if len(line) >= 3 and line[0].isdigit() and line[1] == "/":
            tweet_text = line[2:].strip()
            if 20 <= len(tweet_text) <= 280:
                tweets.append(tweet_text)

    if len(tweets) < 3:
        log.debug("Thread generation: only %d tweets parsed -- discarding.", len(tweets))
        return []

    log.info("Thread generated (%d tweets): %s", len(tweets), tweets[0][:70])
    return tweets[:5]

