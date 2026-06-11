"""
bot/sources/portfolio_diary.py — Personal trade diary posts

WHY THIS EXISTS:
  The highest-engagement content on CT isn't news reactions — it's personal reality.
  @0xSisyphus gets 7k+ likes saying "Hyperliquid" (one word). @Gainzy222 gets 1.7k
  likes posting a single loss update with no data. @Route2FI wins on "here's what
  I'm actually farming."

  This source converts the bot's portfolio.json into personal diary-style posts that
  feel authentic rather than scripted:
    - "just sized into X because Y, watching for W"
    - "still farming X — snapshot criteria is [A, B, C]"
    - "cut my X position. looking at Y now"
    - "been watching X for 3 weeks — finally making my move"

HOW IT WORKS:
  1. Load portfolio.json (positions, airdrops, watching)
  2. Hash the content — compare to last saved hash in state
  3. If changed → diary post about what changed (position added/removed/changed)
  4. If unchanged + 8h since last diary post → post a "what I'm farming" update
     about a randomly chosen active item
  5. Max 1 diary post per day from this source (managed via state)

WHEN PORTFOLIO IS EMPTY:
  Returns None silently — the bot should not pretend to have positions it doesn't.
  As Quin populates portfolio.json with real trades, this source activates.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Optional

from bot.brain.llm import complete as llm_complete
from bot.config import CLAUDE_MAX_TOKENS

log = logging.getLogger(__name__)

_PORTFOLIO_PATH = Path(__file__).parent.parent.parent / "data" / "portfolio.json"

_DIARY_MAX_PER_DAY = 1
_DIARY_MIN_GAP_HOURS = 8.0

_DIARY_SYSTEM = """\
You write personal portfolio diary posts for @Qwinahh — a crypto account that
trades perps on Hyperliquid, farms airdrops with discipline, and gets into DeFi
protocols before narratives form.

WHAT MAKES A GREAT DIARY POST:
  - Specific, not vague. "Sized into HYPE perps at 22.3x funding" > "bought crypto"
  - Shows thinking, not just the trade. "cutting X — funding went negative, thesis broken"
  - Feels like a real person posting, not a bot announcement
  - Under 260 characters — these aren't threads, they're updates

FORMATS THAT WORK:
  A. Position update: "just [action] [asset] [position] — [reasoning]. watching for [signal]"
  B. Farming update: "still farming [protocol] — [what criteria looks like]. [1 honest observation]"
  C. Watch list share: "been watching [project] for [time]. [why interesting]. [what would make me move]"
  D. Exit note: "cut [asset]. [reason]. moving into [next thing] or [staying cash and why]"

HARD RULES:
  - Under 260 characters
  - No hashtags, no emojis, no "GM"
  - Sounds like the account owner typed it on their phone
  - If given multiple items, pick ONE — the most interesting or recent
  - Never fabricate specific numbers you weren't given
  - If nothing compelling to say: respond with SKIP

OUTPUT: Just the tweet text. No preamble, no "here's your tweet:"
"""


def _load_portfolio() -> dict:
    """Load and return portfolio.json, or empty structure on failure."""
    try:
        with open(_PORTFOLIO_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"positions": [], "airdrops": [], "watching": []}
    except json.JSONDecodeError as e:
        log.warning("portfolio.json parse error: %s", e)
        return {"positions": [], "airdrops": [], "watching": []}


def _portfolio_hash(portfolio: dict) -> str:
    """Stable hash of portfolio content for change detection."""
    canonical = json.dumps(portfolio, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _has_content(portfolio: dict) -> bool:
    """Return True if portfolio has any non-empty sections."""
    return bool(
        portfolio.get("positions")
        or portfolio.get("airdrops")
        or portfolio.get("watching")
    )


def _build_portfolio_context(portfolio: dict) -> str:
    """
    Build a human-readable context block describing current portfolio state.
    Used as LLM input.
    """
    lines = []

    positions = portfolio.get("positions", [])
    if positions:
        lines.append("ACTIVE POSITIONS:")
        for p in positions:
            name = p.get("name") or p.get("asset") or p.get("token", "?")
            size = p.get("size") or p.get("amount", "")
            direction = p.get("direction") or p.get("side", "")
            entry = p.get("entry") or p.get("entry_price", "")
            note = p.get("note") or p.get("thesis", "")
            parts = [f"  - {name}"]
            if direction:
                parts[0] += f" ({direction})"
            if size:
                parts[0] += f" — size: {size}"
            if entry:
                parts[0] += f" @ {entry}"
            if note:
                parts.append(f"    note: {note}")
            lines.extend(parts)

    airdrops = portfolio.get("airdrops", [])
    if airdrops:
        lines.append("FARMING / AIRDROPS:")
        for a in airdrops:
            name = a.get("name") or a.get("protocol", "?")
            criteria = a.get("criteria") or a.get("tasks", "")
            status = a.get("status", "active")
            note = a.get("note", "")
            line = f"  - {name} ({status})"
            if criteria:
                if isinstance(criteria, list):
                    line += f" — criteria: {', '.join(str(c) for c in criteria)}"
                else:
                    line += f" — criteria: {criteria}"
            if note:
                line += f" | {note}"
            lines.append(line)

    watching = portfolio.get("watching", [])
    if watching:
        lines.append("WATCHING (not yet entered):")
        for w in watching:
            name = w.get("name") or w.get("asset", "?")
            why = w.get("why") or w.get("reason", "")
            trigger = w.get("trigger") or w.get("entry_trigger", "")
            line = f"  - {name}"
            if why:
                line += f" — why: {why}"
            if trigger:
                line += f" | entry trigger: {trigger}"
            lines.append(line)

    return "\n".join(lines) if lines else ""


def _generate_diary_post(portfolio: dict, change_context: Optional[str] = None) -> Optional[str]:
    """
    Generate a diary-style post from portfolio content.
    Returns tweet text, or None if skipped / generation failed.
    """
    portfolio_ctx = _build_portfolio_context(portfolio)
    if not portfolio_ctx:
        return None

    if change_context:
        prompt_intro = (
            f"Something in the portfolio just changed:\n{change_context}\n\n"
            f"Current portfolio state:\n{portfolio_ctx}\n\n"
            "Write a brief, personal update about what changed and why."
        )
    else:
        # Periodic update — pick the most interesting thing
        all_items = (
            portfolio.get("positions", [])
            + portfolio.get("airdrops", [])
            + portfolio.get("watching", [])
        )
        # Randomly pick a single item to feature
        featured = random.choice(all_items) if all_items else None
        featured_ctx = ""
        if featured:
            featured_ctx = f"\nFEATURED ITEM:\n{json.dumps(featured, indent=2)}\n"

        prompt_intro = (
            f"Current portfolio:\n{portfolio_ctx}"
            f"{featured_ctx}\n\n"
            "Write a personal update about what you're watching or farming right now. "
            "Focus on ONE item — the most compelling or timely one."
        )

    user_prompt = (
        f"{prompt_intro}\n\n"
        "Under 260 chars. Sounds like a human update, not a bot announcement. "
        "No hashtags. No emojis."
    )

    try:
        raw = llm_complete(
            system=_DIARY_SYSTEM,
            user=user_prompt,
            max_tokens=CLAUDE_MAX_TOKENS,
            temperature=0.80,
        )
    except Exception as exc:
        log.warning("Portfolio diary generation failed: %s", exc)
        return None

    if not raw:
        return None

    raw = raw.strip()
    if raw.upper().startswith("SKIP"):
        log.info("Diary writer chose SKIP.")
        return None

    # Strip any preamble lines
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    tweet = lines[-1] if lines else raw
    # Use the last non-empty line in case the model prefixed anything
    for line in lines:
        if len(line) > 20 and not line.lower().startswith(("here", "sure", "tweet", "of course")):
            tweet = line
            break

    if len(tweet) > 280:
        tweet = tweet[:277] + "..."

    return tweet


def maybe_diary_post(state) -> Optional[dict]:
    """
    Check if conditions are met for a portfolio diary post.
    Returns a result dict (same shape as run_post_cycle output) or None.

    Conditions:
      - Portfolio.json has at least one non-empty section
      - Max 1 diary post per day
      - Min 8h gap since last diary post

    Called from orchestrator.run_post_cycle() as Step 0b.
    """
    # Rate limiting
    diary_today = state._data.get("diary_posts_today", 0)
    if diary_today >= _DIARY_MAX_PER_DAY:
        log.debug("Diary: already posted today (%d/%d)", diary_today, _DIARY_MAX_PER_DAY)
        return None

    last_diary_ts = state._data.get("last_diary_ts", 0)
    if time.time() - last_diary_ts < _DIARY_MIN_GAP_HOURS * 3600:
        log.debug("Diary: too soon since last diary post.")
        return None

    # Load portfolio
    portfolio = _load_portfolio()
    if not _has_content(portfolio):
        log.debug("Diary: portfolio is empty — skipping.")
        return None

    # Check for portfolio changes since last run
    current_hash = _portfolio_hash(portfolio)
    last_hash = state._data.get("portfolio_hash", "")
    change_context = None

    if last_hash and last_hash != current_hash:
        # Portfolio changed — trigger a diary post about the change
        log.info("Diary: portfolio changed (hash %s → %s)", last_hash[:8], current_hash[:8])
        # Build a simple change description (new vs old isn't available, just note it changed)
        change_context = "Portfolio was updated since the last check."

    elif not last_hash:
        # First time seeing the portfolio — just note it's the initial state
        log.info("Diary: first portfolio snapshot.")

    # Generate the diary post
    log.info("Diary: generating post (change=%s)", bool(change_context))
    tweet_text = _generate_diary_post(portfolio, change_context=change_context)

    if not tweet_text:
        log.info("Diary: no post generated.")
        # Still update hash so we don't spam on the next run
        state._data["portfolio_hash"] = current_hash
        state.save()
        return None

    # Post it
    from bot.x.client import post_tweet
    tweet_id = post_tweet(tweet_text)
    if not tweet_id:
        log.warning("Diary: post_tweet failed.")
        return None

    # Update state
    state.increment_post_count()
    state.set_last_post_timestamp(time.time())
    state._data["portfolio_hash"] = current_hash
    state._data["diary_posts_today"] = diary_today + 1
    state._data["last_diary_ts"] = time.time()
    state.mark_seen(state.fingerprint(tweet_text.lower()))
    state.save()

    log.info("Diar