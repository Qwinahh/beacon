"""
Compute format performance weights from collected engagement data.

Returns a dict: {format_name: weight_float} where weight > 1.0 means
this format outperforms average, < 1.0 means it underperforms.

Weights are used by _pick_format() in writer.py to bias toward what works.
Falls back to equal weights if insufficient data (< 3 posts per format).

Scoring: (replies * 3 + likes + retweets * 2) / post_count
Replies weighted highest — X algorithm cares most about replies.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

log = logging.getLogger(__name__)

_METRICS_FILE   = Path("data/growth/metrics.json")
_CACHE_TTL_SECS = 3600   # re-read file at most once per hour
_MIN_DATA_POINTS = 3     # minimum posts before a format gets a real weight

_cache: dict = {}
_cache_ts: float = 0.0


def _load_metrics() -> dict:
    if not _METRICS_FILE.exists():
        return {}
    try:
        data = json.loads(_METRICS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_weights() -> dict[str, float]:
    """
    Return format weights, re-computed at most once per hour.
    Always returns a dict — callers can safely call .get(name, 1.0).
    """
    global _cache, _cache_ts
    now = time.time()
    if _cache and now - _cache_ts < _CACHE_TTL_SECS:
        return _cache

    try:
        weights = _compute_weights()
    except Exception as exc:
        log.debug("format_weights computation failed: %s", exc)
        weights = {}

    _cache    = weights
    _cache_ts = now
    return weights


def _compute_weights() -> dict[str, float]:
    metrics = _load_metrics()
    if not metrics:
        return {}

    # Group scores by format
    by_format: dict[str, list[float]] = {}
    for record in metrics.values():
        fmt      = record.get("format", "unknown")
        likes    = record.get("likes",    0) or 0
        replies  = record.get("replies",  0) or 0
        retweets = record.get("retweets", 0) or 0
        score    = replies * 3 + likes + retweets * 2
        by_format.setdefault(fmt, []).append(float(score))

    if not by_format:
        return {}

    # Average score per format
    avg_by_format: dict[str, float] = {
        fmt: sum(scores) / len(scores)
        for fmt, scores in by_format.items()
    }

    # Overall average across all formats (for normalisation)
    all_avgs = list(avg_by_format.values())
    global_avg = sum(all_avgs) / len(all_avgs) if all_avgs else 1.0

    if global_avg == 0:
        return {}

    # Normalise: weight = format_avg / global_avg
    # Formats with < MIN_DATA_POINTS get weight 1.0 (neutral)
    weights: dict[str, float] = {}
    for fmt, scores in by_format.items():
        if len(scores) < _MIN_DATA_POINTS:
            weights[fmt] = 1.0
        else:
            weights[fmt] = avg_by_format[fmt] / global_avg

    log.debug(
        "format_weights: %s",
        ", ".join(f"{k}={v:.2f}" for k, v in sorted(weights.items(), key=lambda x: -x[1])),
    )
    return weights


# ---------------------------------------------------------------------------
# Topic weights — which subject keywords drove real engagement
# ---------------------------------------------------------------------------

_topic_cache: dict = {}
_topic_cache_ts: float = 0.0


def get_topic_weights() -> dict[str, float]:
    """
    Return per-topic keyword weights derived from metrics.json engagement data.
    Each key is a lowercase word from the post's topic field; value is the
    normalised engagement weight (>1.0 = above average, <1.0 = below average).

    Used by orchestrator._analyze_candidates() to bias candidate scoring
    toward topics that have historically driven replies and profile visits.
    Falls back to {} with no data (callers must handle missing keys).
    """
    global _topic_cache, _topic_cache_ts
    now = time.time()
    if _topic_cache and now - _topic_cache_ts < _CACHE_TTL_SECS:
        return _topic_cache

    try:
        weights = _compute_topic_weights()
    except Exception as exc:
        log.debug("get_topic_weights failed: %s", exc)
        weights = {}

    _topic_cache    = weights
    _topic_cache_ts = now
    return weights


def _compute_topic_weights() -> dict[str, float]:
    metrics = _load_metrics()
    if not metrics:
        return {}

    by_topic: dict[str, list[float]] = {}
    for record in metrics.values():
        raw_topic = (record.get("topic") or "").lower().strip()
        if not raw_topic or raw_topic == "unknown":
            continue
        likes    = record.get("likes",    0) or 0
        replies  = record.get("replies",  0) or 0
        retweets = record.get("retweets", 0) or 0
        score    = replies * 3 + likes + retweets * 2
        # Split multi-word topics so "hyperliquid perps" registers under both words
        for word in raw_topic.replace("-", " ").split():
            if len(word) >= 4:  # skip short noise words
                by_topic.setdefault(word, []).append(float(score))

    if not by_topic:
        return {}

    avg_by_topic = {
        kw: sum(scores) / len(scores)
        for kw, scores in by_topic.items()
    }
    all_avgs  = list(avg_by_topic.values())
    global_avg = sum(all_avgs) / len(all_avgs) if all_avgs else 1.0
    if global_avg == 0:
        return {}

    return {
        kw: avg_by_topic[kw] / global_avg
        for kw, scores in by_topic.items()
        if len(scores) >= _MIN_DATA_POINTS
    }
