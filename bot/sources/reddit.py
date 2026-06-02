"""
Reddit community signal ingestion.

Polls hot posts from crypto-focused subreddits via the public JSON API.
No auth required for public subreddits.

Community signals are NEVER treated as confirmed facts. They feed the
community tier (tier 3) of the verifier and are never written as facts.
"""
from __future__ import annotations

import logging
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

import requests

log = logging.getLogger(__name__)

_SUBREDDITS = [
    "CryptoCurrency",
    "defi",
    "ethfinance",
    "solana",
    "HyperliquidTrading",
]

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "CryptoSignalBot/1.0 (research only)"})


@dataclass
class RedditSignal:
    subreddit: str
    title: str
    score: int
    comments: int
    url: str
    created_ts: float
    tier: str = "community"
    kind: str = "reddit"
    meta: dict = field(default_factory=dict)

    @property
    def age_hours(self) -> float:
        return (time.time() - self.created_ts) / 3600.0


def fetch_hot(subreddit: str, limit: int = 10) -> list[RedditSignal]:
    """Fetch hot posts from a single subreddit via the public JSON API."""
    items: list[RedditSignal] = []
    try:
        url  = f"https://www.reddit.com/r/{subreddit}/hot.json"
        resp = _SESSION.get(url, params={"limit": limit}, timeout=10)
        resp.raise_for_status()
        posts = resp.json()["data"]["children"]
        for post in posts:
            d     = post["data"]
            title = d.get("title", "").strip()
            if not title or d.get("stickied"):
                continue
            items.append(RedditSignal(
                subreddit=subreddit,
                title=title,
                score=d.get("score", 0),
                comments=d.get("num_comments", 0),
                url=f"https://reddit.com{d.get('permalink', '')}",
                created_ts=float(d.get("created_utc", time.time())),
                meta={"subreddit": subreddit, "score": d.get("score", 0)},
            ))
    except Exception as exc:
        log.warning("Reddit fetch failed for r/%s: %s", subreddit, exc)
    return items


def fetch_all_signals(
    subreddits: Optional[list[str]] = None,
    limit: int = 8,
) -> list[RedditSignal]:
    """Fetch hot posts across all configured subreddits, sorted by score."""
    subs    = subreddits or _SUBREDDITS
    signals: list[RedditSignal] = []
    for sub in subs:
        signals.extend(fetch_hot(sub, limit=limit))
    signals.sort(key=lambda x: x.score, reverse=True)
    log.info("Reddit: %d signals from %d subreddits.", len(signals), len(subs))
    return signals


_STOPWORDS = {
    "that", "this", "with", "from", "have", "will", "just", "been",
    "about", "more", "what", "your", "their", "there", "here", "when",
    "than", "into", "which", "been",
}


def top_topics(n: int = 5) -> list[str]:
    """Return the top n recurring words across hot Reddit posts."""
    signals = fetch_all_signals()
    words: Counter[str] = Counter()
    for s in signals:
        for w in re.findall(r"\b[a-zA-Z]{4,}\b", s.title.lower()):
            if w not in _STOPWORDS:
                words[w] += 1
    return [w for w, _ in words.most_common(n)]
