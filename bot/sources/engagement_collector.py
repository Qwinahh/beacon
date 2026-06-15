"""
Collect engagement metrics on our own recent posts via twscrape.
Runs on Free tier — no X API required, just X_SCRAPER_COOKIES.

Writes to data/growth/metrics.json so format_weights.py can analyse what's working.
Metrics collected per tweet: likes, replies, retweets, quote_tweets.
Also records format and topic from pending.json so we know WHAT kind of post
earned WHAT engagement.

Called from engage.py at the start of every run (every 30 min).
Tweets are collected once they are at least 2 hours old — enough time to
accumulate meaningful engagement without waiting the full 24h.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_GROWTH_DIR    = Path("data/growth")
_PENDING_FILE  = _GROWTH_DIR / "pending.json"
_METRICS_FILE  = _GROWTH_DIR / "metrics.json"
_COOKIES_ENV   = "X_SCRAPER_COOKIES"
_MIN_AGE_SECS  = 2 * 3600   # 2 hours
_MAX_METRICS   = 200


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def _load_pending() -> list:
    if not _PENDING_FILE.exists():
        return []
    try:
        data = json.loads(_PENDING_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _load_metrics() -> dict:
    if not _METRICS_FILE.exists():
        return {}
    try:
        data = json.loads(_METRICS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_json(path: Path, data) -> None:
    _GROWTH_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# twscrape helpers
# ---------------------------------------------------------------------------

async def _make_api():
    try:
        from twscrape import API

        from bot.x import twscrape_patch  # noqa: F401
    except ImportError:
        return None
    cookies = os.environ.get(_COOKIES_ENV, "").strip()
    if not cookies:
        return None
    api = API(os.path.join(tempfile.gettempdir(), "twscrape_pool.db"))
    try:
        await api.pool.add_account(
            username="beacon_collector_scraper",
            password="placeholder",
            email="placeholder@placeholder.com",
            email_password="placeholder",
            cookies=cookies,
        )
    except Exception as exc:
        log.debug("engagement_collector twscrape setup: %s", exc)
        return None
    return api


async def _fetch_tweet_async(tweet_id: str) -> Optional[dict]:
    """Fetch a single tweet's current engagement via twscrape."""
    api = await _make_api()
    if not api:
        return None
    try:
        tweet = await api.tweet_by_id(int(tweet_id))
        if not tweet:
            return None
        return {
            "likes":        getattr(tweet, "likeCount",    0) or 0,
            "replies":      getattr(tweet, "replyCount",   0) or 0,
            "retweets":     getattr(tweet, "retweetCount", 0) or 0,
            "quote_tweets": getattr(tweet, "quoteCount",   0) or 0,
        }
    except Exception as exc:
        log.debug("Tweet fetch error for %s: %s", tweet_id, exc)
        return None


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(coro)
    except Exception as exc:
        log.debug("Async runner error (collector): %s", exc)
        return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def collect_pending() -> int:
    """
    Fetch engagement for pending tweets that are at least 2 hours old.
    Writes results to metrics.json, removes collected entries from pending.json.
    Returns number of tweets collected. Fails silently.
    """
    try:
        return _collect()
    except Exception as exc:
        log.warning("engagement_collector failed (non-fatal): %s", exc)
        return 0


def _collect() -> int:
    pending = _load_pending()
    if not pending:
        return 0

    now = time.time()
    still_pending = []
    metrics = _load_metrics()
    collected = 0

    for entry in pending:
        tweet_id  = entry.get("tweet_id", "")
        posted_ts = entry.get("posted_ts", now)

        if not tweet_id:
            continue

        # Not old enough yet
        if now - posted_ts < _MIN_AGE_SECS:
            still_pending.append(entry)
            continue

        # Already collected
        if tweet_id in metrics:
            continue

        engagement = _run_async(_fetch_tweet_async(tweet_id))

        if engagement is None:
            # twscrape unavailable — still move out of pending to avoid infinite retries
            engagement = {"likes": 0, "replies": 0, "retweets": 0, "quote_tweets": 0}

        metrics[tweet_id] = {
            "tweet_id":    tweet_id,
            "text":        entry.get("text", "")[:140],
            "format":      entry.get("format", "unknown"),
            "topic":       entry.get("topic", ""),
            "posted_at":   posted_ts,
            "collected_at": now,
            **engagement,
        }
        collected += 1
        log.info(
            "Collected metrics for %s — likes:%d replies:%d rt:%d",
            tweet_id,
            engagement["likes"],
            engagement["replies"],
            engagement["retweets"],
        )

    # Trim to max entries (oldest first)
    if len(metrics) > _MAX_METRICS:
        sorted_ids = sorted(metrics, key=lambda k: metrics[k].get("posted_at", 0))
        for old_id in sorted_ids[:len(metrics) - _MAX_METRICS]:
            del metrics[old_id]

    _save_json(_METRICS_FILE, metrics)
    _save_json(_PENDING_FILE, still_pending)

    if collected:
        log.info("engagement_collector: collected %d tweet(s).", collected)

    return collected
