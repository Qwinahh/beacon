"""
bot/sources/reddit.py — Reddit community signal ingestion.

Uses PRAW (Python Reddit API Wrapper) with read-only access.
Requires: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET env vars (free, no user login needed).

IMPORTANT: Reddit posts are Tier 3 (community sentiment).
They are NEVER written to vault as confirmed facts.
They are used only as:
  - Sentiment context for writer prompts
  - Signal that a narrative is heating up
  - Community concern detection (e.g., rug fears, exploit rumours)
"""

from __future__ import annotations

import os
import logging
import time
from typing import Optional

log = logging.getLogger(__name__)

# Subreddits to monitor
_SUBREDDITS = [
    "CryptoCurrency",
    "defi",
    "ethfinance",
    "solana",
    "ethereum",
    "Bitcoin",
    "airdrops",
    "HyperliquidTrading",
    "kaito_ai",
    "layer2",
]

_MAX_POSTS = 5          # per subreddit
_MIN_UPVOTES = 20       # filter noise
_SORT = "hot"           # hot | top | new


def _get_reddit():
    """Lazy-import praw and initialise read-only Reddit client."""
    try:
        import praw  # type: ignore
    except ImportError:
        log.warning("praw not installed — Reddit ingestion disabled. Run: pip install praw")
        return None

    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")

    if not client_id or not client_secret:
        log.warning("REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET not set — Reddit disabled")
        return None

    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent="beacon-bot/1.0 (crypto alpha bot, read-only)",
            ratelimit_seconds=60,
        )
        # Verify connection
        _ = reddit.subreddit("CryptoCurrency").id
        return reddit
    except Exception as e:
        log.error("Reddit init failed: %s", e)
        return None


def fetch_hot_posts(
    subreddits: Optional[list[str]] = None,
    limit: int = _MAX_POSTS,
    min_upvotes: int = _MIN_UPVOTES,
) -> list[dict]:
    """
    Fetch hot posts from crypto subreddits.
    Returns list of dicts with: title, score, url, subreddit, created_utc, selftext_snippet.
    All returned data is Tier 3 — community sentiment only.
    """
    reddit = _get_reddit()
    if not reddit:
        return []

    subs = subreddits or _SUBREDDITS
    results = []

    for sub_name in subs:
        try:
            sub = reddit.subreddit(sub_name)
            for post in sub.hot(limit=limit * 3):  # fetch more, filter down
                if post.score < min_upvotes:
                    continue
                if post.stickied:
                    continue
                results.append({
                    "title": post.title,
                    "score": post.score,
                    "url": f"https://reddit.com{post.permalink}",
                    "subreddit": sub_name,
                    "created_utc": post.created_utc,
                    "selftext_snippet": (post.selftext or "")[:300],
                    "source_tier": 3,
                    "source": f"reddit/r/{sub_name}",
                })
                if len([r for r in results if r["subreddit"] == sub_name]) >= limit:
                    break
        except Exception as e:
            log.warning("Reddit fetch failed for r/%s: %s", sub_name, e)
            continue

    return results


def search_reddit(query: str, limit: int = 10) -> list[dict]:
    """
    Search Reddit for a specific topic.
    Useful when researcher agent wants Reddit context on a specific protocol.
    """
    reddit = _get_reddit()
    if not reddit:
        return []

    results = []
    try:
        sub = reddit.subreddit("+".join(_SUBREDDITS))
        for post in sub.search(query, limit=limit, sort="relevance", time_filter="week"):
            results.append({
                "title": post.title,
                "score": post.score,
                "url": f"https://reddit.com{post.permalink}",
                "subreddit": post.subreddit.display_name,
                "created_utc": post.created_utc,
                "selftext_snippet": (post.selftext or "")[:300],
                "source_tier": 3,
                "source": f"reddit/r/{post.subreddit.display_name}",
            })
    except Exception as e:
        log.error("Reddit search failed for '%s': %s", query, e)

    return results


def build_reddit_context(topic: str, limit: int = 5) -> str:
    """
    Build a community sentiment summary string for the writer context.
    Clearly marked as community sentiment, not confirmed information.
    """
    posts = search_reddit(topic, limit=limit)
    if not posts:
        return ""

    lines = [f"REDDIT COMMUNITY SIGNALS (sentiment only, not confirmed facts) for '{topic}':"]
    for p in posts[:limit]:
        lines.append(f"  - r/{p['subreddit']} [{p['score']} upvotes]: {p['title']}")

    return "\n".join(lines)
