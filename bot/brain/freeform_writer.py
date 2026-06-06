"""
Freeform writer — generates authentic opinion posts without a data item.

Called ~30% of the time by the orchestrator instead of the normal
data-driven pipeline. Reads vault context (narratives, recent events,
projects) and generates a hot take, personal observation, or market
commentary that sounds like a person thinking out loud.

This is how top crypto accounts actually post. Most of their content
isn't tied to a specific news event — it's opinions and observations
from people who live in the space.
"""
from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import Optional

from bot.brain.llm import complete as llm_complete
from bot.config import CLAUDE_MAX_TOKENS

log = logging.getLogger(__name__)

_FREEFORM_FORMATS = [
    ("market_observation",
     "Write a MARKET OBSERVATION — something you've noticed about the current "
     "state of DeFi/perps/crypto that most people haven't articulated yet. "
     "No specific news event needed. Just what you're seeing. First person or third person. "
     "Example: 'Everyone is talking about L2 TVL but the real story is that L2 fee revenue "
     "is still basically zero. TVL without fees is just locked capital looking for an exit.'\n"
     "Under 220 chars. Must be an observation, not a summary."),

    ("personal_take",
     "Write a PERSONAL TAKE — your actual current thinking on a DeFi/crypto topic. "
     "What are you watching, what are you skeptical about, what surprised you recently. "
     "First person throughout. Specific. Willing to be wrong. "
     "Example: 'Been watching restaking yield compress for 3 months. "
     "When it drops below native ETH staking yield, that's when you'll see the unwind. "
     "Not there yet but closer than people think.'\nUnder 220 chars."),

    ("space_pattern",
     "Write a PATTERN you've noticed repeating in crypto — something that's happened "
     "before and is happening again. Historical context makes this valuable. "
     "Example: 'This is the 3rd time in 4 years a new DEX has launched with "
     "'zero fees forever' as the pitch. First two ended the same way. "
     "Watch when the grant runs out.'\nUnder 200 chars."),

    ("contrarian_view",
     "Write a CONTRARIAN VIEW on a consensus narrative in DeFi/crypto right now. "
     "Pick a widely held belief and push back with specific reasoning. "
     "Don't be contrarian for its own sake — only if you actually disagree. "
     "Example: 'The 'DeFi is back' narrative is running ahead of the data. "
     "Protocol revenue is up but it's concentrated in 3 protocols. "
     "Everything else is still bleeding users.'\nUnder 220 chars."),

    ("honest_admission",
     "Write something HONEST AND SPECIFIC about the current market — "
     "something that shows you're actually paying attention rather than cheerleading. "
     "Could be something you got wrong, something that surprised you, or a nuance "
     "the market is missing. Authenticity is the entire value here. "
     "Example: 'Held my Meteora LP position through the last SOL drawdown. "
     "IL was worse than I modelled. Still positive EV but I sized it wrong.'\nUnder 200 chars."),
]

_FREEFORM_SYSTEM = """\
You write short, authentic posts for @Qwinahh — a DeFi trader who farms airdrops,
trades perps, and moves into protocols early.

You have NO specific news event to write about. You are generating a post based
purely on Quin's current views, what he's been watching, and what he's thinking.

This is the hardest type of post to write well. The bad version sounds generic.
The good version sounds like a real person who lives in this space and has
specific views formed from actual experience.

WHAT MAKES THESE POSTS WORK:
- They reveal something the writer actually thinks, not something they summarised
- They contain a specific observation that requires being close to the space to notice
- They make a reader feel like "yes, someone else sees this too" or "I hadn't thought of it that way"
- They are the kind of thing you'd say to a friend who also trades DeFi, not to a general audience

VOICE: Direct. Opinionated. Specific. No hedging. No "this could be".
Sounds like someone who has actual money in these protocols and is thinking out loud.

HARD RULES:
- Under 240 characters. One idea only.
- No hashtags. No emojis.
- No "the crypto space" or "the DeFi ecosystem" — you ARE in this space, speak from inside it.
- No generic takes. If you can't be specific, respond with SKIP.
- No price predictions. No "to the moon" or equivalent.

OUTPUT FORMAT:
REASON: [one sentence — what specific value does this give someone actually in DeFi]
[post text]

Or: SKIP
"""


def _load_vault_context() -> str:
    context_parts = []

    log_dir = Path("data/vault/log")
    if log_dir.exists():
        log_files = sorted(log_dir.glob("*.md"), reverse=True)[:2]
        for lf in log_files:
            try:
                content = lf.read_text(encoding="utf-8")[:600]
                context_parts.append(f"Recent activity ({lf.stem}):\n{content}")
            except Exception:
                pass

    narratives_dir = Path("data/vault/narratives")
    if narratives_dir.exists():
        for nf in narratives_dir.glob("*.md"):
            try:
                content = nf.read_text(encoding="utf-8")[:400]
                context_parts.append(f"Narrative — {nf.stem}:\n{content}")
            except Exception:
                pass

    projects_dir = Path("data/vault/projects")
    if projects_dir.exists():
        for pf in sorted(projects_dir.glob("*.md"))[:3]:
            try:
                content = pf.read_text(encoding="utf-8")[:300]
                context_parts.append(f"Project — {pf.stem}:\n{content}")
            except Exception:
                pass

    return "\n\n---\n\n".join(context_parts) if context_parts else ""


def generate_freeform(recent_formats: list[str], recent_topics: list[str]) -> Optional[str]:
    """
    Generate an authentic opinion post without a specific data item.

    Returns tweet text if successful, None if the LLM SKIPs or quality fails.
    Never raises.
    """
    try:
        recent = set((recent_formats or [])[-2:])
        options = [(n, i) for n, i in _FREEFORM_FORMATS if n not in recent]
        if not options:
            options = _FREEFORM_FORMATS
        format_name, format_instruction = random.choice(options)

        vault_context = _load_vault_context()
        recent_topics_str = ", ".join(recent_topics[-5:]) if recent_topics else "none"

        context_block = (
            f"Context from your recent tracking:\n{vault_context}\n\n---\n\n"
            if vault_context else ""
        )

        user_prompt = (
            f"You are writing a freeform post — no specific news event, just your current thinking.\n\n"
            f"{context_block}"
            f"Format to use: {format_name.upper().replace('_', ' ')}\n"
            f"{format_instruction}\n\n"
            f"Recent topics you've posted about (avoid repeating): {recent_topics_str}\n\n"
            f"Write something worth reading. If you can't — SKIP."
        )

        raw = llm_complete(
            system=_FREEFORM_SYSTEM,
            user=user_prompt,
            max_tokens=CLAUDE_MAX_TOKENS,
            temperature=0.9,
        )

        if not raw:
            return None

        raw = raw.strip()
        if raw.upper().startswith("SKIP"):
            log.debug("Freeform writer: SKIP")
            return None

        # Parse REASON: ...\n[tweet]
        lines = [line.strip() for line in raw.split("\n") if line.strip()]
        tweet_lines = [line for line in lines if not line.upper().startswith("REASON:")]
        if not tweet_lines:
            return None

        tweet = " ".join(tweet_lines).strip()

        if len(tweet) < 20 or len(tweet) > 280:
            return None

        bad_openers = [
            "breaking:", "just in:", "announcement:", "new:", "update:",
            "according to", "reports say", "sources say",
        ]
        if any(tweet.lower().startswith(b) for b in bad_openers):
            log.debug("Freeform: rejected news-summary opener")
            return None

        log.info("Freeform writer (%s): %s", format_name, tweet[:70])
        return tweet

    except Exception as exc:
        log.warning("Freeform writer failed: %s", exc)
        return None
