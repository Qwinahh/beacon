"""
X conversation context scraper — free replacement for LunarCrush.

Uses twscrape (vladkens/twscrape) which works via X's GraphQL API.
Requires one or more X account sessions stored in X_SCRAPER_COOKIES env var.

Setup:
1. Get the `ct0` and `auth_token` cookies from your browser while logged into X.
   Open DevTools → Application → Cookies → x.com
   Copy `ct0` and `auth_token` values.

2. Set as a GitHub Secret named X_SCRAPER_COOKIES in this format:
   ct0=abc123; auth_token=xyz789

3. Add to your workflow env block:
   X_SCRAPER_COOKIES: ${{ secrets.X_SCRAPER_COOKIES }}

If the env var is not set or scraping fails, this returns an empty result
gracefully — the writer still functions, just without X context.

The scraper uses search to find recent influential posts about a topic,
filters for engagement (likes + retweets > threshold), and returns a
compact summary for the writer.
"""
from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from typing import Optional

log = logging.getLogger(__name__)

_COOKIES_ENV = "X_SCRAPER_COOKIES"
_MIN_ENGAGEMENT = 10  # likes + reposts minimum to count as influential
_MAX_RESULTS = 8
_SEARCH_LIMIT = 30  # fetch more than needed, then filter by engagement


def _get_cookies() -> Optional[str]:
    return os.environ.get(_COOKIES_ENV, "").strip() or None


async def _scrape(topic: str, limit: int) -> list[dict]:
    """
    Async core — searches X for `topic` and returns recent influential posts.
    Requires twscrape and a valid cookie string in the env.
    """
    try:
        from twscrape import API
    except ImportError:
        log.warning("twscrape not installed — X context unavailable. Run: pip install twscrape")
        return []

    cookies = _get_cookies()
    if not cookies:
        return []

    # Use a temp in-memory db so we don't write files during CI runs.
    api = API(os.path.join(tempfile.gettempdir(), "twscrape_pool.db"))
    try:
        await api.pool.add_account(
            username="beacon_scraper",
            password="placeholder",
            email="placeholder@placeholder.com",
            email_password="placeholder",
            cookies=cookies,
        )
    except Exception as exc:
        log.warning("twscrape account setup failed: %s", exc)
        return []

    results = []
    try:
        # Search latest tab for recency.
        async for tweet in api.search(f"{topic} lang:en", limit=_SEARCH_LIMIT, kv={"product": "Latest"}):
            engagement = (tweet.likeCount or 0) + (tweet.retweetCount or 0)
            if engagement < _MIN_ENGAGEMENT:
                continue
            results.append({
                "user":       tweet.user.username if tweet.user else "unknown",
                "text":       tweet.rawContent or "",
                "likes":      tweet.likeCount or 0,
                "retweets":   tweet.retweetCount or 0,
                "engagement": engagement,
            })
            if len(results) >= limit:
                break
    except Exception as exc:
        log.warning("twscrape search failed for '%s': %s", topic, exc)
        return []

    # Sort by engagement descending.
    results.sort(key=lambda r: r["engagement"], reverse=True)
    return results[:limit]


def _run_scrape(topic: str) -> list[dict]:
    """Run the async scraper in whatever event loop context we're in."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're inside an existing event loop (e.g. Jupyter). Use a thread.
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, _scrape(topic, _MAX_RESULTS))
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(_scrape(topic, _MAX_RESULTS))
    except Exception as exc:
        log.warning("X context scrape error: %s", exc)
        return []


def fetch_topic_posts(topic: str, limit: int = _MAX_RESULTS) -> list[str]:
    """
    Public API — returns a list of influential recent X post texts about `topic`.
    Returns an empty list if scraping is unavailable or fails.
    """
    posts = _run_scrape(topic)
    if not posts:
        return []

    # Return just the text content for the writer context block.
    return [
        f"@{p['user']} ({p['likes']}L/{p['retweets']}RT): {p['text'][:200]}"
        for p in posts[:limit]
    ]


def build_x_context_summary(topic: str) -> str:
    """
    Returns a formatted string of what X is saying about `topic` right now,
    or an empty string if nothing is available.
    Ready to inject directly into the writer context block.
    """
    posts = fetch_topic_posts(topic)
    if not posts:
        return ""
    lines = ["Recent X posts about this topic (engagement-filtered):"]
    lines += [f"  • {p}" for p in posts]
    return "\n".join(lines)
