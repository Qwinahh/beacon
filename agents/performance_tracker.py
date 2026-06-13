"""
Performance tracker — closes the learning feedback loop on posted tweets.

What it does: reads data/performance/post_log.json (written by the
orchestrator after every post), fetches X metrics for posts older than
24h that still have null metrics, computes derived rates (engagement,
reply, bookmark), and rewrites data/vault/knowledge/performance-log.md
as a human/bot-readable weekly performance report.

When it runs: daily at 06:00 UTC via .github/workflows/track.yml,
before the first posting window of the day.

Reads:  data/performance/post_log.json, X API v2 (GET /2/tweets)
Writes: data/performance/post_log.json (metrics filled in),
        data/vault/knowledge/performance-log.md

Key design decisions:
- non_public_metrics (impressions) require OAuth 1.0a user context — we
  reuse the same tweepy client the bot posts with (bot/x/client.py), so
  no new secrets are needed.
- Metrics are fetched in batches of up to 100 ids per request to stay
  inside rate limits.
- 403/404 on a tweet (too old for non-public metrics, deleted, protected)
  is handled by falling back to public_metrics or marking the entry
  "metrics_unavailable" — the tracker never crashes the workflow.
- Degrades gracefully: with no API access at all, it still regenerates
  the report from whatever metrics already exist.
"""
from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from bot.config import POST_LOG_PATH, PERFORMANCE_LOG_MD_PATH

log = logging.getLogger(__name__)

# Wait this long after posting before fetching metrics.
METRICS_DELAY_SECONDS = 24 * 3600

# X API v2 allows up to 100 ids per /2/tweets lookup.
BATCH_SIZE = 100


# ---------------------------------------------------------------------------
# Post log IO
# ---------------------------------------------------------------------------

def _load_post_log() -> list[dict]:
    path = Path(POST_LOG_PATH)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as exc:
        log.error("Could not parse %s: %s", path, exc)
        return []


def _save_post_log(entries: list[dict]) -> None:
    path = Path(POST_LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def _parse_posted_at(entry: dict) -> float:
    """Return posted_at as a unix timestamp (0 on failure)."""
    raw = entry.get("posted_at", "")
    if isinstance(raw, (int, float)):
        return float(raw)
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Metric fetching (tweepy, OAuth 1.0a user context)
# ---------------------------------------------------------------------------

def _fetch_metrics_batch(tweet_ids: list[str]) -> dict[str, dict]:
    """
    Fetch public + non-public metrics for a batch of tweet ids.
    Returns {tweet_id: metrics_dict}. Missing ids mean unavailable.
    """
    results: dict[str, dict] = {}
    if not tweet_ids:
        return results

    try:
        from bot.x.client import get_client
        client = get_client()
    except Exception as exc:
        log.warning("X client unavailable (%s) — skipping metric fetch.", exc)
        return results

    fields_attempts = [
        ["public_metrics", "non_public_metrics"],  # full (needs user context, <30d old)
        ["public_metrics"],                        # fallback (no impressions)
    ]

    for fields in fields_attempts:
        try:
            resp = client.get_tweets(
                ids=tweet_ids,
                tweet_fields=fields,
                user_auth=True,
            )
        except Exception as exc:
            # 403 here usually means non_public_metrics isn't allowed for
            # one of the tweets (too old) or the access tier — retry public-only.
            log.info("get_tweets(%s) failed: %s", "+".join(fields), exc)
            continue

        for tweet in (resp.data or []):
            pub = tweet.public_metrics or {}
            non_pub = getattr(tweet, "non_public_metrics", None) or {}
            results[str(tweet.id)] = {
                "impressions":  non_pub.get("impression_count", pub.get("impression_count")),
                "likes":        pub.get("like_count", 0),
                "replies":      pub.get("reply_count", 0),
                "retweets":     pub.get("retweet_count", 0),
                "quote_tweets": pub.get("quote_count", 0),
                "bookmarks":    pub.get("bookmark_count", 0),
            }
        # Deleted/protected tweets come back in resp.errors — mark them.
        for err in (resp.errors or []):
            missing_id = str(err.get("resource_id") or err.get("value") or "")
            if missing_id and missing_id not in results:
                results[missing_id] = {"metrics_unavailable": True}
        return results

    return results


def _derive_rates(entry: dict) -> None:
    """Compute engagement_rate / reply_rate / bookmark_rate in place."""
    imp = entry.get("impressions") or 0
    if not imp:
        entry["engagement_rate"] = None
        entry["reply_rate"] = None
        entry["bookmark_rate"] = None
        return
    likes = entry.get("likes") or 0
    replies = entry.get("replies") or 0
    bookmarks = entry.get("bookmarks") or 0
    entry["engagement_rate"] = round((likes + replies + bookmarks) / imp, 5)
    entry["reply_rate"] = round(replies / imp, 5)
    entry["bookmark_rate"] = round(bookmarks / imp, 5)


def update_post_metrics() -> dict:
    """
    Fetch metrics for all eligible posts (>24h old, metrics still null).
    Returns a summary dict.
    """
    entries = _load_post_log()
    if not entries:
        log.info("post_log.json is empty — nothing to track yet.")
        return {"updated": 0, "pending": 0, "total": 0}

    now = time.time()
    eligible = [
        e for e in entries
        if e.get("tweet_id")
        and e.get("impressions") is None
        and not e.get("metrics_unavailable")
        and (now - _parse_posted_at(e)) >= METRICS_DELAY_SECONDS
    ]

    updated = 0
    for i in range(0, len(eligible), BATCH_SIZE):
        batch = eligible[i:i + BATCH_SIZE]
        fetched = _fetch_metrics_batch([e["tweet_id"] for e in batch])
        for e in batch:
            m = fetched.get(e["tweet_id"])
            if not m:
                continue
            if m.get("metrics_unavailable"):
                e["metrics_unavailable"] = True
                continue
            e.update(m)
            _derive_rates(e)
            updated += 1

    if updated:
        _save_post_log(entries)
    log.info("Metrics updated for %d posts (%d eligible, %d total).",
             updated, len(eligible), len(entries))
    return {"updated": updated, "pending": len(eligible) - updated, "total": len(entries)}


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _fmt_pct(value: Optional[float]) -> str:
    return f"{value * 100:.2f}%" if value else "—"


def _top5(entries: list[dict], key: str) -> list[str]:
    ranked = sorted(
        (e for e in entries if e.get(key)),
        key=lambda e: e[key], reverse=True,
    )[:5]
    return [
        f"| {_fmt_pct(e.get(key))} | {e.get('format_used', '?')} | "
        f"{(e.get('tweet_text') or '')[:70].replace('|', '/')} |"
        for e in ranked
    ]


def _avg_by(entries: list[dict], group_key: str, value_key: str) -> list[tuple[str, float, int]]:
    groups: dict[str, list[float]] = defaultdict(list)
    for e in entries:
        v = e.get(value_key)
        if v is not None:
            groups[str(e.get(group_key) or "unknown")].append(v)
    out = [(k, sum(v) / len(v), len(v)) for k, v in groups.items()]
    return sorted(out, key=lambda x: -x[1])


def write_performance_report() -> None:
    """Regenerate data/vault/knowledge/performance-log.md from post_log.json."""
    entries = _load_post_log()
    now = time.time()
    week = [e for e in entries if now - _parse_posted_at(e) <= 7 * 86400]
    prev_week = [e for e in entries if 7 * 86400 < now - _parse_posted_at(e) <= 14 * 86400]
    measured = [e for e in week if e.get("impressions")]

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        "---",
        "title: Performance Log",
        "type: knowledge",
        "topic: performance",
        "tags: [knowledge, performance, auto-generated]",
        f"last_updated: {today}",
        f"updated: {today}",
        "---",
        "",
        "# Performance Log",
        "",
        "*Auto-generated daily by `agents/performance_tracker.py`. Do not edit "
        "— changes are overwritten. Source data: `data/performance/post_log.json`.*",
        "",
        f"Tracked posts: {len(entries)} total, {len(week)} in the last 7 days, "
        f"{len(measured)} with measured impressions.",
        "",
    ]

    header = "| rate | format | post |\n|---|---|---|"
    for title, key in [
        ("Top 5 this week — engagement rate", "engagement_rate"),
        ("Top 5 this week — reply rate", "reply_rate"),
        ("Top 5 this week — bookmark rate", "bookmark_rate"),
    ]:
        rows = _top5(week, key)
        lines += [f"## {title}", ""]
        lines += [header] + rows + [""] if rows else ["No measured posts yet.", ""]

    lines += ["## Average engagement rate by format", ""]
    fmt_rows = _avg_by(week, "format_used", "engagement_rate")
    if fmt_rows:
        lines += ["| format | avg engagement | n |", "|---|---|---|"]
        lines += [f"| {f} | {_fmt_pct(v)} | {n} |" for f, v, n in fmt_rows]
    else:
        lines += ["No data yet."]
    lines += [""]

    lines += ["## Average engagement rate by topic", ""]
    topic_rows = _avg_by(week, "topic", "engagement_rate")
    if topic_rows:
        lines += ["| topic | avg engagement | n |", "|---|---|---|"]
        lines += [f"| {t} | {_fmt_pct(v)} | {n} |" for t, v, n in topic_rows]
    else:
        lines += ["No data yet."]
    lines += [""]

    lines += ["## Average impressions by hour of day (UTC)", ""]
    by_hour: dict[int, list[float]] = defaultdict(list)
    for e in entries:
        imp = e.get("impressions")
        ts = _parse_posted_at(e)
        if imp and ts:
            by_hour[datetime.fromtimestamp(ts, tz=timezone.utc).hour].append(imp)
    if by_hour:
        lines += ["| hour (UTC) | avg impressions | n |", "|---|---|---|"]
        lines += [
            f"| {h:02d}:00 | {sum(v) / len(v):,.0f} | {len(v)} |"
            for h, v in sorted(by_hour.items())
        ]
    else:
        lines += ["No data yet."]
    lines += [""]

    lines += ["## Week-over-week", ""]
    def _week_avg(rows: list[dict]) -> Optional[float]:
        vals = [e["engagement_rate"] for e in rows if e.get("engagement_rate")]
        return sum(vals) / len(vals) if vals else None
    cur, prev = _week_avg(week), _week_avg(prev_week)
    if cur is not None and prev is not None and prev > 0:
        delta = (cur - prev) / prev * 100
        lines += [f"Avg engagement rate: {_fmt_pct(cur)} this week vs {_fmt_pct(prev)} "
                  f"last week ({delta:+.0f}%)."]
    elif cur is not None:
        lines += [f"Avg engagement rate this week: {_fmt_pct(cur)}. "
                  "No prior-week baseline yet."]
    else:
        lines += ["Not enough measured data for a trend yet."]
    lines += ["", "---", "", "→ [[index]] · [[knowledge/post-structure-science]] · [[knowledge/x-algorithm-2026]]", ""]

    path = Path(PERFORMANCE_LOG_MD_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    log.info("Performance report written to %s.", path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    summary = update_post_metrics()
    write_performance_report()
    log.info("Performance tracker done: %s", summary)


if __name__ == "__main__":
    main()
