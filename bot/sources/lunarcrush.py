"""
Lunarcrush data source — X/crypto social context.

Wraps the Lunarcrush public API to fetch recent X posts about a given topic.
This gives the Scout visibility into what the crypto X community is already
discussing, so the writer can add an angle that isn't already saturated.

Requires: LUNARCRUSH_API_KEY environment variable.
If not set, all functions return empty results silently.

API docs: https://lunarcrush.com/developers/api/endpoints
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional

log = logging.getLogger(__name__)

_BASE_URL = "https://lunarcrush.com/api4/public"


def _get_api_key() -> Optional[str]:
    return os.environ.get("LUNARCRUSH_API_KEY")


def _get(endpoint: str, params: dict) -> Optional[dict]:
    """Make an authenticated GET request to the Lunarcrush API."""
    api_key = _get_api_key()
    if not api_key:
        return None

    try:
        import urllib.request
        import urllib.parse
        import json as _json

        query = urllib.parse.urlencode(params)
        url   = f"{_BASE_URL}{endpoint}?{query}"

        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            return _json.loads(resp.read())
    except Exception as exc:
        log.warning("Lunarcrush API error for %s: %s", endpoint, exc)
        return None


def fetch_topic_posts(topic: str, limit: int = 8) -> list[dict]:
    """
    Fetch recent X posts about `topic` from Lunarcrush.

    Returns a list of dicts with keys: text, creator, engagement, url.
    Returns an empty list if the API key is absent or the call fails.
    """
    data = _get("/topic/posts/v1", {"topic": topic, "limit": limit})
    if not data:
        return []

    posts = data.get("data", [])
    out = []
    for p in posts:
        text = p.get("body") or p.get("text") or ""
        if not text:
            continue
        out.append({
            "text":        text[:280],
            "creator":     p.get("creator_name") or p.get("screen_name") or "unknown",
            "engagement":  p.get("interactions_24h", 0),
            "url":         p.get("url") or p.get("post_link") or "",
            "posted_at":   p.get("post_created") or p.get("time", 0),
        })

    # Sort by engagement descending so the most resonant posts appear first.
    out.sort(key=lambda x: x["engagement"], reverse=True)
    return out[:limit]


def fetch_topic_summary(topic: str) -> Optional[str]:
    """
    Return a plain-English summary of what's being said about `topic` on X.

    This is a convenience wrapper that formats the top posts into a short
    paragraph the writer can use directly. Returns None if no data available.
    """
    posts = fetch_topic_posts(topic, limit=5)
    if not posts:
        return None

    lines = [f"Top X posts about '{topic}' right now:"]
    for i, p in enumerate(posts, 1):
        eng = p["engagement"]
        eng_str = f" ({eng:,} interactions)" if eng else ""
        lines.append(f"{i}. @{p['creator']}{eng_str}: {p['text'][:200]}")

    return "\n".join(lines)
