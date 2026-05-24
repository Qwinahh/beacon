"""
cryptocurrency.cv news API source.

Fetches crypto news from the cryptocurrency.cv free REST API, which aggregates
200+ sources (CoinDesk, The Block, Decrypt, Blockworks, DL News, and more),
deduplicates entries, and ranks by freshness. No API key required.

This supplements (and over time can replace) direct RSS scraping, giving the
Scout access to far more signal without maintaining individual feed URLs.

Reference: https://github.com/nirholas/cryptocurrency.cv
API docs:  https://cryptocurrency.cv/api/news
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

from bot.sources.rss import FeedItem, _classify_topic  # reuse topic classifier

log = logging.getLogger(__name__)

_API_URL    = "https://cryptocurrency.cv/api/news"
_TIMEOUT_S  = 8
_MAX_ITEMS  = 30


@dataclass
class NewsItem:
    title:        str
    source:       str
    url:          Optional[str]
    published_ts: float
    topic:        str
    kind:         str = "rss"

    @property
    def age_hours(self) -> float:
        return (time.time() - self.published_ts) / 3600.0


def _to_feed_item(item: NewsItem) -> FeedItem:
    """Convert to FeedItem so the Scout can treat it identically to RSS items."""
    return FeedItem(
        source=item.source,
        title=item.title,
        url=item.url,
        published_ts=item.published_ts,
        topic=item.topic,
        kind=item.kind,
    )


def fetch_news(max_age_hours: float = 8.0, limit: int = _MAX_ITEMS) -> list[FeedItem]:
    """
    Fetch recent crypto news from cryptocurrency.cv.

    Returns a list of FeedItem objects (same type as bot.sources.rss.fetch_all)
    so the Scout can treat them identically. Falls back gracefully on any error.

    Args:
        max_age_hours: Discard items older than this.
        limit:         Maximum items to return.
    """
    try:
        req = urllib.request.Request(
            _API_URL,
            headers={"User-Agent": "qwinahh-crypto-bot/1.0"},
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
            data = json.loads(resp.read())
    except urllib.error.URLError as exc:
        log.warning("cryptocurrency.cv fetch failed: %s", exc)
        return []
    except Exception as exc:
        log.warning("cryptocurrency.cv unexpected error: %s", exc)
        return []

    articles = data if isinstance(data, list) else data.get("data", data.get("articles", []))
    cutoff   = time.time() - max_age_hours * 3600
    out: list[FeedItem] = []

    for article in articles[:limit * 2]:  # over-fetch then filter
        try:
            title = article.get("title") or article.get("headline") or ""
            if not title:
                continue

            source = article.get("source") or article.get("publisher") or "unknown"
            url    = article.get("url") or article.get("link") or None

            # Parse timestamp -- API returns ISO strings or unix timestamps.
            raw_ts = article.get("published_at") or article.get("publishedAt") or article.get("date")
            if isinstance(raw_ts, (int, float)):
                pub_ts = float(raw_ts)
            elif isinstance(raw_ts, str):
                from email.utils import parsedate_to_datetime
                try:
                    pub_ts = parsedate_to_datetime(raw_ts).timestamp()
                except Exception:
                    import datetime
                    try:
                        pub_ts = datetime.datetime.fromisoformat(
                            raw_ts.replace("Z", "+00:00")
                        ).timestamp()
                    except Exception:
                        pub_ts = time.time() - 3600  # assume 1h old if unparseable
            else:
                pub_ts = time.time() - 3600

            if pub_ts < cutoff:
                continue

            topic = _classify_topic(title)
            out.append(FeedItem(
                source=source,
                title=title,
                url=url,
                published_ts=pub_ts,
                topic=topic,
                kind="rss",
            ))

            if len(out) >= limit:
                break

        except Exception as exc:
            log.debug("Skipping article due to parse error: %s", exc)
            continue

    log.info("cryptocurrency.cv: fetched %d items (age <= %.0fh)", len(out), max_age_hours)
    return out
