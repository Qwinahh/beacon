"""
Engagement entry point.

Four jobs per run:
  1. Reply to any new @mentions.
  2. Proactive outbound engagement -- replies to curated accounts and keyword search.
  3. Own-thread continuations -- follow-up observations on our recent high-engagement
     posts. X weights "author continues their thread" as one of the highest-value
     quality signals, worth far more than likes or retweets.
  4. Strategic following -- strictly gated, plus an unfollow pass every cycle to
     keep the following:follower ratio clean.

All four work on the X Free API tier:
  - READING  (finding tweets, mentions, candidates) -> twscrape cookie-based scraping
  - WRITING  (posting replies, following, unfollowing) -> official X API (Free tier)

Requires: X_SCRAPER_COOKIES secret set in GitHub for reading.
          X_API_KEY / X_API_SECRET / X_ACCESS_TOKEN / X_ACCESS_SECRET for writing.
          X_USERNAME (optional, defaults to "Qwinahh") for own-thread detection.

Usage:
    python engage.py
"""
from __future__ import annotations

import logging
import os

from bot.state import State
from bot.x.engage import reply_to_own_mentions
from bot.x.engage import run as run_mentions
from bot.x.engage import run_own_thread_replies
from bot.x.engage import run_quote_tweet
from bot.x.engage import update_post_metrics
from bot.x.follow import run_follow_cycle
from bot.x.trend import run as run_trends

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def main() -> None:
    # ---- Cookie gate diagnostics (gatekeeper for all reading operations) ----
    cookies = os.environ.get("X_SCRAPER_COOKIES", "").strip()
    if not cookies:
        log.warning(
            "X_SCRAPER_COOKIES is not set. Mentions, outbound replies, thread replies, "
            "and follow candidate discovery are ALL disabled. "
            "Set this secret in GitHub → Settings → Secrets → Actions. "
            "Get it from browser DevTools → Application → Cookies → x.com: "
            "copy ct0 and auth_token values as: ct0=VALUE; auth_token=VALUE"
        )
    else:
        log.info("X_SCRAPER_COOKIES: set (%d chars)", len(cookies))

    # ---- Account health check (shadowban / suppression detection) ----
    from bot.sources.health_monitor import check_health, is_in_recovery
    check_health()

    if is_in_recovery():
        log.warning(
            "Account is in recovery mode (possible shadowban/suppression detected). "
            "Reducing engagement activity. Check data/growth/health_status.json for details."
        )

    # ---- Collect engagement on our own recent posts (non-fatal) ----
    try:
        from bot.sources.engagement_collector import collect_pending
        collect_pending()
    except Exception as exc:
        log.debug("engagement_collector skipped: %s", exc)

    state = State()
    state.load()

    # ---- Pull engagement metrics for recent posts (feeds format_weights.py) ----
    try:
        update_post_metrics(state)
    except Exception as exc:
        log.debug("update_post_metrics skipped: %s", exc)

    mention_replies      = run_mentions(state)
    post_mention_replies = reply_to_own_mentions(state)
    trend_replies        = run_trends(state)
    quote_tweets         =