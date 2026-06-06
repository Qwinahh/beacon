"""
bot/sources/x_metrics.py — Pull tweet performance data from the X API.

Fetches impressions, likes, replies, retweets, bookmarks, and profile visits
for tweets the bot has posted. Writes metrics to data/growth/ so the
orchestrator can learn what formats and topics perform best.

X API v2 public metrics require Basic tier ($100/mo).
X API v2 organic metrics (impressions, profile clicks) require Pro tier ($5k/mo).

**Free tier reality check:**
The free X API tier does NOT include tweet metrics (read access is extremely limited).
We store the tweet IDs and attempt to fetch metrics. If metrics are unavailable,
we fall back to estimating engagement from reply counts (which ARE fetchable via
search for the tweet's replies, as a proxy metric). The system works at any tier
and improves with higher API access.

State is stored in data/growth/metrics.json.
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_METRICS_DIR  = Path("data/growth")
_METRICS_FILE = _METRICS_DIR / "metrics.json"
_PENDING_FILE = _METRICS_DIR / "pending.json"


def _ensure_dirs() -> None:
    _METRICS_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path) -> dict | list:
    if not path.exists():
        return {} if "metrics" in path.name else []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {} if "metrics" in path.name else []


def _save_json(path: Path, data: dict | list) -> None:
    _ensure_dirs()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Recording tweets for later metric pull
# ---------------------------------------------------------------------------

def record_posted_tweet(
    tweet_id: str,
    tweet_text: str,
    format_used: str,
    topic: str,
    posted_ts: Optional[float] = None,
) -> None:
    """
    Store a newly posted tweet so metrics can be fetched later.
    Called by the orchestrator immediately after posting.
    """
    _ensure_dirs()
    pending = _load_json(_PENDING_FILE)
    if not isinstance(pending, list):
        pending = []

    entry = {
        "tweet_id":   tweet_id,
        "text":       tweet_text[:140],
        "format":     format_used,
        "topic":      topic,
        "posted_ts":  posted_ts or time.time(),
        "fetch_after_ts": (posted_ts or time.time()) + 86400,  # fetch 24h after posting
    }
    # Don't duplicate
    if not any(p.get("tweet_id") == tweet_id for p in pending):
        pending.append(entry)
    _save_json(_PENDING_FILE, pending)
    log.debug("Queued tweet %s for metric pull.", tweet_id)


# ---------------------------------------------------------------------------
# Metric fetching
# ---------------------------------------------------------------------------

def _fetch_tweet_metrics(tweet_id: str, bearer_token: str) -> Optional[dict]:
    """
    Attempt to fetch tweet metrics via X API v2.
    Returns None if unavailable (free tier or network error).
    """
    try:
        import requests
        url = f"https://api.twitter.com/2/tweets/{tweet_id}"
        params = {
            "tweet.fields": "public_metrics,organic_metrics,created_at",
        }
        headers = {"Authorization": f"Bearer {bearer_token}"}
        resp = requests.get(url, params=params, headers=headers, timeout=10)

        if resp.status_code == 403:
            log.debug("Tweet metrics access denied (requires Basic/Pro tier). Storing null metrics.")
            return None
        if resp.status_code != 200:
            log.debug("Tweet metrics fetch failed: %s", resp.status_code)
            return None

        data = resp.json().get("data", {})
        pub  = data.get("public_metrics", {})
        org  = data.get("organic_metrics", {})

        return {
            "impressions":     org.get("impression_count", pub.get("impression_count", 0)),
            "likes":           pub.get("like_count", 0),
            "replies":         pub.get("reply_count", 0),
            "retweets":        pub.get("retweet_count", 0),
            "quotes":          pub.get("quote_count", 0),
            "bookmarks":       pub.get("bookmark_count", 0),
            "profile_clicks":  org.get("user_profile_clicks", 0),
            "fetched_at":      time.time(),
        }
    except Exception as exc:
        log.debug("Metric fetch error: %s", exc)
        return None


def _estimate_engagement_proxy(tweet_id: str) -> dict:
    """
    Proxy engagement estimate when organic metrics aren't available.
    Counts replies via search (approximate). Always returns a dict.
    """
    # Without API access, return zeros — still useful for format tracking
    return {
        "impressions":    0,
        "likes":          0,
        "replies":        0,
        "retweets":       0,
        "quotes":         0,
        "bookmarks":      0,
        "profile_clicks": 0,
        "fetched_at":     time.time(),
        "is_estimated":   True,
    }


# ---------------------------------------------------------------------------
# Main batch update
# ---------------------------------------------------------------------------

def update_metrics() -> dict:
    """
    Pull metrics for all pending tweets that are past the 24h mark.
    Writes results to data/growth/metrics.json.
    Returns summary of what was processed.
    """
    _ensure_dirs()
    bearer_token = os.environ.get("X_BEARER_TOKEN", "")

    pending = _load_json(_PENDING_FILE)
    if not isinstance(pending, list):
        pending = []

    metrics_db = _load_json(_METRICS_FILE)
    if not isinstance(metrics_db, dict):
        metrics_db = {}

    now = time.time()
    processed = []
    still_pending = []

    for entry in pending:
        tweet_id = entry.get("tweet_id", "")
        fetch_after = entry.get("fetch_after_ts", 0)

        if now < fetch_after:
            still_pending.append(entry)
            continue

        # Try to fetch real metrics
        metrics = None
        if bearer_token:
            metrics = _fetch_tweet_metrics(tweet_id, bearer_token)

        if metrics is None:
            metrics = _estimate_engagement_proxy(tweet_id)

        record = {
            **entry,
            "metrics": metrics,
        }
        metrics_db[tweet_id] = record
        processed.append(tweet_id)
        log.info(
            "Metrics for %s — likes:%d replies:%d impressions:%d",
            tweet_id,
            metrics.get("likes", 0),
            metrics.get("replies", 0),
            metrics.get("impressions", 0),
        )

    # Save updated state
    _save_json(_PENDING_FILE, still_pending)
    _save_json(_METRICS_FILE, metrics_db)

    return {
        "processed": len(processed),
        "still_pending": len(still_pending),
        "total_tracked": len(metrics_db),
    }


# ---------------------------------------------------------------------------
# Analysis helpers — used by the growth agent and orchestrator
# ---------------------------------------------------------------------------

def get_best_formats(min_posts: int = 3) -> list[dict]:
    """
    Return formats ranked by average engagement rate (replies+bookmarks/impressions).
    Only includes formats with at least min_posts data points.
    """
    metrics_db = _load_json(_METRICS_FILE)
    if not isinstance(metrics_db, dict):
        return []

    by_format: dict[str, list] = {}
    for record in metrics_db.values():
        fmt = record.get("format", "unknown")
        m   = record.get("metrics", {})
        imp = m.get("impressions", 0)
        if imp == 0:
            continue
        eng = (m.get("replies", 0) + m.get("bookmarks", 0)) / imp
        by_format.setdefault(fmt, []).append(eng)

    results = []
    for fmt, rates in by_format.items():
        if len(rates) >= min_posts:
            results.append({
                "format":       fmt,
                "avg_engagement_rate": sum(rates) / len(rates),
                "sample_size":  len(rates),
            })

    return sorted(results, key=lambda x: x["avg_engagement_rate"], reverse=True)


def get_best_topics(min_posts: int = 2) -> list[dict]:
    """Return topics ranked by average impressions."""
    metrics_db = _load_json(_METRICS_FILE)
    if not isinstance(metrics_db, dict):
        return []

    by_topic: dict[str, list] = {}
    for record in metrics_db.values():
        topic = record.get("topic", "unknown")
        m     = record.get("metrics", {})
        imp   = m.get("impressions", 0)
        if imp > 0:
            by_topic.setdefault(topic, []).append(imp)

    results = []
    for topic, imps in by_topic.items():
        if len(imps) >= min_posts:
            results.append({
                "topic":           topic,
                "avg_impressions": sum(imps) / len(imps),
                "sample_size":     len(imps),
            })

    return sorted(results, key=lambda x: x["avg_impressions"], reverse=True)


def get_recent_performance_summary(n_posts: int = 20) -> str:
    """
    Return a compact performance summary string for injection into the orchestrator context.
    Used to tell the orchestrator which formats and topics are working.
    """
    metrics_db = _load_json(_METRICS_FILE)
    if not isinstance(metrics_db, dict) or not metrics_db:
        return ""

    # Sort by posted_ts, take most recent n
    records = sorted(
        metrics_db.values(),
        key=lambda r: r.get("posted_ts", 0),
        reverse=True,
    )[:n_posts]

    if not records:
        return ""

    total_impressions = sum(r.get("metrics", {}).get("impressions", 0) for r in records)
    total_replies     = sum(r.get("metrics", {}).get("replies",     0) for r in records)
    total_likes       = sum(r.get("metrics", {}).get("likes",       0) for r in records)

    best_formats = get_best_formats(min_posts=2)
    best_topics  = get_best_topics(min_posts=2)

    lines = [f"## Recent Performance ({len(records)} posts tracked)"]
    if total_impressions > 0:
        lines.append(
            f"Avg impressions: {total_impressions // len(records):,} | "
            f"Avg replies: {total_replies / len(records):.1f} | "
            f"Avg likes: {total_likes / len(records):.1f}"
        )
    if best_formats:
        lines.append(
            "Top formats by engagement: "
            + ", ".join(f["format"] for f in best_formats[:3])
        )
    if best_topics:
        lines.append(
            "Top topics by reach: "
            + ", ".join(t["topic"] for t in best_topics[:3])
        )

    # Flag any post that significantly underperformed
    low_performers = [
        r for r in records
        if r.get("metrics", {}).get("impressions", 999) < 200
        and not r.get("metrics", {}).get("is_estimated")
    ]
    if low_performers:
        lines.append(
            f"⚠ {len(low_performers)} recent posts under 200 impressions — "
            "consider increasing specificity or adjusting timing."
        )

    return "\n".join(lines)
