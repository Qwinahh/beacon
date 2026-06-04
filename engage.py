"""
Engagement entry point.

Three jobs per run:
  1. Reply to any new @mentions.
  2. Proactive outbound engagement -- replies to curated accounts and keyword search.
  3. Strategic following -- strictly gated, only high-quality accounts in focus topics.

All three work on the X Free API tier:
  - READING  (finding tweets, mentions, candidates) -> twscrape cookie-based scraping
  - WRITING  (posting replies, following)           -> official X API (Free tier)

Requires: X_SCRAPER_COOKIES secret set in GitHub for reading.
          X_API_KEY / X_API_SECRET / X_ACCESS_TOKEN / X_ACCESS_SECRET for writing.

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

    state.save()  # Always persist -- reply tracking, mention cursor, engaged accounts

    log.info(
        "Engagement run complete — "
        "mention replies: %d | outbound replies: %d | follows: %d",
        mention_replies, trend_replies, follows,
    )


if __name__ == "__main__":
    main()
