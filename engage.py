"""
Engagement entry point.

Three jobs per run:
  1. Reply to any new @mentions.
  2. Proactive outbound engagement — replies to curated accounts and keyword search.
  3. Strategic following — strictly gated, only high-quality accounts in focus topics.

All three require X API Basic tier. Each exits cleanly if the tier is too low
or if the quality gate finds nothing worth acting on.

Usage:
    python engage.py
"""
from __future__ import annotations

import logging

from bot.state import State
from bot.x.engage import run as run_mentions
from bot.x.follow import run_follow_cycle
from bot.x.trend import run as run_trends

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def main() -> None:
    state = State()
    state.load()

    mention_replies = run_mentions(state)
    trend_replies   = run_trends(state)
    follows         = run_follow_cycle(state)

    if mention_replies + trend_replies > 0:
        state.save()

    log.info(
        "Engagement run complete — "
        "mention replies: %d | outbound replies: %d | follows: %d",
        mention_replies, trend_replies, follows,
    )


if __name__ == "__main__":
    main()
