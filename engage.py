"""
Engagement entry point.

Two jobs per run:
  1. Reply to any new mentions using Claude-generated responses.
  2. Find trending crypto conversations and add genuine commentary.

Both require X API Basic tier. If the tier is too low, each function
exits cleanly with a log warning — no errors, no crashes.

Usage:
    python engage.py
"""
from __future__ import annotations

import logging
import sys

from bot.state import State
from bot.x.engage import run as run_mentions
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

    total = mention_replies + trend_replies
    if total > 0:
        state.save()

    log.info(
        "Engagement run complete. Mention replies: %d, Trend replies: %d.",
        mention_replies,
        trend_replies,
    )


if __name__ == "__main__":
    main()
