"""
RSS feed ingestion.

Fetches multiple feeds in parallel and returns normalised Item objects
sorted newest-first.
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import feedparser
from dateutil import parser as dateparser

from bot.config import RSS_FEEDS, RSS_ITEMS_PER_FEED, RSS_MAX_AGE_HOURS

log = logging.getLogger(__name__)


@dataclass
class FeedItem:
    source: str
    title: str
    url: Optional[str]
    published_ts: float  # Unix timestamp
    topic: str = "general"
    kind: str = "rss"
    meta: dict = field(default_factory=dict)

    @property
    def age_hours(self) -> float:
        return (time.time() - self.published_ts) / 3600.0


def _classify_topic(text: str) -> str:
    t = text.lower()
    rules = [
        ("hype",     ["hyperliquid", " hype "]),
        ("kaito",    ["kaito"]),
        ("meteora",  ["meteora"]),
        ("lighter",  ["lighter.xyz", "lighter protocol"]),
        ("farming",  ["airdrop", "points program", "leaderboard", "farm "]),
        ("listing",  ["listing", "listed on", "coinbase", "binance", "kraken"]),
        ("raise",    ["raised", "raise", "funding round", "seed round", "series a", "series b"]),
        ("agents",   ["ai agent", "autonomous agent", "virtuals", "virtual protocol"]),
        ("perps",    ["perpetual", "perp ", "perps", "futures exchange"]),
        ("defi",     ["defi", "tvl", "liquidity", "amm", "yield", "vault"]),
        ("layer2",   ["arbitrum", "optimism", "base ", "zksync", "starknet", "polygon"]),
    ]
    for topic, patterns in rules:
        if any(p in t for p in patterns):
            return topic
    return "general"


def _parse_timestamp(entry: feedparser.FeedParserDict) -> float:
    for attr in ("published", "updated", "created"):
        raw = getattr(entry, attr, None)
        if raw:
            try:
                dt = dateparser.parse(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.timestamp()
            except Exception:
                pass
    return time.time()


def _fetch_one_feed(source: str, url: str) -> list[FeedItem]:
    items: list[FeedItem] = []
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": "CryptoBot/2.0"})
        for entry in feed.entries[:RSS_ITEMS_PER_FEED]:
            title = (getattr(entry, "title", "") or "").strip()
            link  = (getattr(entry, "link",  "") or "").strip() or None
            if not title or len(title) < 20:
                continue
            ts = _parse_timestamp(entry)
            items.append(FeedItem(
                source=source,
                title=title,
                url=link,
                published_ts=ts,
                topic=_classify_topic(title),
            ))
    except Exception as exc:
        log.warning("Feed '%s' failed: %s", source, exc)
    return items


def fetch_all(max_age_hours: float = RSS_MAX_AGE_HOURS) -> list[FeedItem]:
    """
    Fetch all configured RSS feeds concurrently and return items younger
    than `max_age_hours`, sorted newest-first.
    """
    results: list[FeedItem] = []
    with ThreadPoolExecutor(max_workers=len(RSS_FEEDS)) as pool:
        futures = {pool.submit(_fetch_one_feed, src, url): src for src, url in RSS_FEEDS}
        for future in as_completed(futures):
            results.extend(future.result())

    fresh = [item for item in results if item.age_hours <= max_age_hours]
    fresh.sort(key=lambda x: x.published_ts, reverse=True)
    log.info("RSS: %d total items, %d within %gh.", len(results), len(fresh), max_age_hours)
    return fresh
