"""
Alpha posting entry point.

Runs every 2 hours and checks for urgency-3 alpha signals — things that
are happening right now and worth posting about regardless of the normal
posting window. If nothing is urgent, it exits cleanly.

This is separate from post.py (the regular schedule) so that the normal
daily cap still applies. An alpha post counts toward your 5-per-day limit.

Usage:
    python alpha_post.py
"""
from __future__ import annotations

import logging
import sys
import time

from bot.brain import writer
from bot.config import MAX_POSTS_PER_DAY, MIN_HOURS_BETWEEN_POSTS
from bot.portfolio.tracker import load_portfolio
from bot.sources.alpha import AlphaSignal, detect_all
from bot.sources.rss import FeedItem
from bot.sources.defillama import RaiseItem, TvlMoverItem
from bot.state import State
from bot.x.client import post_tweet

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def _signal_to_synthetic_item(signal: AlphaSignal):
    """
    Convert an AlphaSignal to a RaiseItem/FeedItem-compatible object
    so the writer module can handle it uniformly.
    """
    # We fake a FeedItem — the writer only needs .title, .source, .topic, .kind
    return FeedItem(
        source=signal.source,
        title=signal.title,
        url=signal.url,
        published_ts=signal.published_ts,
        topic=signal.topic,
        kind=signal.kind,
        meta=signal.meta,
    )


def main() -> None:
    state = State()
    state.load()

    # Respect daily cap.
    if state.posts_today() >= MAX_POSTS_PER_DAY:
        log.info("Daily cap reached. Skipping alpha check.")
        sys.exit(0)

    # Respect minimum spacing.
    hours_since = (time.time() - state.last_post_timestamp()) / 3600.0
    if state.last_post_timestamp() and hours_since < MIN_HOURS_BETWEEN_POSTS:
        log.info("Too soon since last post (%.1fh). Skipping alpha check.", hours_since)
        sys.exit(0)

    signals = detect_all()
    urgent  = [s for s in signals if s.urgency == 3]

    if not urgent:
        log.info("No urgency-3 alpha signals. Exiting cleanly.")
        sys.exit(0)

    portfolio = load_portfolio()
    signal    = urgent[0]   # Take the highest-priority signal.

    # Deduplicate.
    title_fp = state.fingerprint(signal.title.lower())
    if state.has_seen(title_fp):
        log.info("Alpha signal already posted. Exiting.")
        sys.exit(0)

    item      = _signal_to_synthetic_item(signal)
    text      = writer.generate(item, portfolio, state.recent_formats())

    if not text:
        log.warning("Writer returned empty text.")
        sys.exit(0)

    text_fp = state.fingerprint(text.lower())
    if state.has_seen(text_fp):
        log.info("Generated text is a duplicate. Exiting.")
        sys.exit(0)

    tweet_id = post_tweet(text)
    if not tweet_id:
        log.warning("Alpha post failed.")
        sys.exit(1)

    state.mark_seen(title_fp)
    state.mark_seen(text_fp)
    state.record_topic(signal.topic)
    state.record_format("alpha")
    state.increment_post_count()
    state.set_last_post_timestamp(time.time())
    state.save()

    log.info(
        "Alpha post sent [urgency=%d, kind=%s]: %s",
        signal.urgency, signal.kind, signal.title[:70],
    )


if __name__ == "__main__":
    main()
