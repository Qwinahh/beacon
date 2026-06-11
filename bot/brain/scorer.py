"""
Item scoring and candidate selection.

The scorer assigns a numeric score to each candidate item and selects
the best one for posting, applying topic-variety and deduplication guards.
"""
from __future__ import annotations

import logging
import time
from typing import Union

from bot.config import (
    FOCUS_KEYWORDS,
    JUNK_PHRASES,
    MAX_TOPIC_REPEAT,
    POST_SCORE_THRESHOLD,
)
from bot.sources.defillama import RaiseItem, TvlMoverItem
from bot.sources.rss import FeedItem
from bot.state import State

log = logging.getLogger(__name__)

CandidateItem = Union[FeedItem, RaiseItem, TvlMoverItem]


def _contains_focus(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in FOCUS_KEYWORDS)


def _contains_junk(text: str) -> bool:
    t = text.lower()
    return any(ph in t for ph in JUNK_PHRASES)


def _title(item: CandidateItem) -> str:
    if isinstance(item, RaiseItem):
        amt = f"${item.amount:.0f}M" if item.amount else "undisclosed amount"
        return f"{item.name} raises {amt} ({item.round_name})"
    if isinstance(item, TvlMoverItem):
        direction = "up" if item.change_pct > 0 else "down"
        return f"{item.name} TVL {direction} {abs(item.change_pct):.1f}% in 24h"
    return item.title


def score(item: CandidateItem) -> int:
    """
    Return a relevance score.  Higher = more likely to post.
    Scoring is deterministic — no randomness here.
    """
    points = 0
    title_text = _title(item)

    # --- Freshness ---
    age = item.age_hours
    if age <= 1:
        points += 30
    elif age <= 3:
        points += 22
    elif age <= 6:
        points += 14
    elif age <= 8:
        points += 7
    else:
        points += 2

    # --- Source trust ---
    if isinstance(item, FeedItem):
        source_bonuses = {
            "the defiant": 12,
            "the block":   10,
            "blockworks":  10,
            "coindesk":    8,
            "dl news":     8,
        }
        for name, bonus in source_bonuses.items():
            if name in item.source.lower():
                points += bonus
                break

    if isinstance(item, RaiseItem):
        points += 14  # Raises are concrete, specific signals.

    if isinstance(item, TvlMoverItem):
        points += 10
        if abs(item.change_pct) >= 30:
            points += 8
        if abs(item.change_pct) >= 50:
            points += 6

    # --- TVL penalty — generic TVL movement posts are lowest-value content ---
    is_tvl = isinstance(item, TvlMoverItem) or getattr(item, "kind", "") == "tvl"
    if is_tvl and not any(k in title_text.lower() for k in [
        "exploit", "hack", "attack", "drain", "rug",
        "launch", "new", "first",
    ]):
        points = int(points * 0.6)
        log.debug("Scorer: TVL penalty applied to '%s'", title_text[:40])

    # --- Relevance to focus areas ---
    if _contains_focus(title_text):
        points += 20

    # --- High-value catalyst keywords ---
    catalysts = [
        "airdrop", "points program", "leaderboard", "tge", "token launch",
        "listing", "listed on", "raises", "funding", "incentive",
        "mainnet", "v2 launch", "protocol launch",
    ]
    if any(c in title_text.lower() for c in catalysts):
        points += 18

    # --- Junk penalty ---
    if _contains_junk(title_text):
        points -= 20

    # --- Minimum title quality ---
    if len(title_text) < 30:
        points -= 10

    return points


def select_candidate(
    pool: list[CandidateItem],
    state: State,
) -> tuple[CandidateItem | None, int]:
    """
    Score all items, apply deduplication and variety guards,
    and return (best_item, score) or (None, 0) if nothing qualifies.
    """
    scored: list[tuple[int, CandidateItem]] = []
    for item in pool:
        s = score(item)
        if s >= POST_SCORE_THRESHOLD:
            scored.append((s, item))

    scored.sort(key=lambda x: x[0], reverse=True)

    recent_topics = state.recent_topics()

    for s, item in scored:
        title_fp = state.fingerprint(_title(item).lower())
        if state.has_seen(title_fp):
            log.debug("Skipping (seen): %s", _title(item)[:60])
            continue

        if recent_topics.count(item.topic) >= MAX_TOPIC_REPEAT:
            log.debug("Skipping (topic saturation, %s): %s", item.topic, _title(