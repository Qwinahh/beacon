"""
bot/sources/fear_greed.py — Crypto Fear & Greed Index

Source: Alternative.me (https://alternative.me/crypto/fear-and-greed-index/)
API: https://api.alternative.me/fng/
Cost: Completely FREE. No API key. No rate limits mentioned.

Returns 0-100 index updated daily:
  0-24   = Extreme Fear
  25-49  = Fear
  50     = Neutral
  51-74  = Greed
  75-100 = Extreme Greed

HOW THE BOT USES THIS:
  - Writer gets the current F&G value injected as context
  - Helps calibrate tone: don't post bullish takes during extreme greed (crowded),
    don't post neutral takes during extreme fear (missed opportunity for conviction)
  - Enables posts like: "F&G at 12 (extreme fear). Last time it was here was
    the FTX bottom. Not saying that's the floor but..."
  - Scout uses it to flag when sentiment extremes are worth posting about directly
"""

from __future__ import annotations

import logging
import time
import urllib.request
import json
from typing import Optional

log = logging.getLogger(__name__)

_API_URL = "https://api.alternative.me/fng/?limit=7&format=json"
_CACHE: dict = {}
_CACHE_TTL = 3600  # 1 hour — index only updates daily


def _fetch_raw() -> Optional[dict]:
    """Fetch raw F&G data from Alternative.me. Returns None on failure."""
    now = time.time()
    if _CACHE.get("ts", 0) + _CACHE_TTL > now:
        return _CACHE.get("data")

    try:
        with urllib.request.urlopen(_API_URL, timeout=8) as resp:
            data = json.loads(resp.read())
        _CACHE["data"] = data
        _CACHE["ts"] = now
        return data
    except Exception as e:
        log.warning("Fear & Greed fetch failed: %s", e)
        return None


def get_current() -> Optional[dict]:
    """
    Get current Fear & Greed reading.
    Returns dict with: value (int), classification (str), timestamp (str)
    Returns None if API unavailable.
    """
    raw = _fetch_raw()
    if not raw or not raw.get("data"):
        return None
    entry = raw["data"][0]
    return {
        "value": int(entry["value"]),
        "classification": entry["value_classification"],
        "timestamp": entry["timestamp"],
    }


def get_history(days: int = 7) -> list[dict]:
    """Get last N days of F&G readings."""
    raw = _fetch_raw()
    if not raw or not raw.get("data"):
        return []
    return [
        {
            "value": int(e["value"]),
            "classification": e["value_classification"],
            "timestamp": e["timestamp"],
        }
        for e in raw["data"][:days]
    ]


def get_trend() -> str:
    """
    Returns a one-line trend description: rising/falling/stable + direction.
    E.g. "Rising from Fear (32) → Greed (61) over 7 days"
    """
    history = get_history(7)
    if len(history) < 2:
        return ""
    oldest = history[-1]["value"]
    newest = history[0]["value"]
    delta = newest - oldest
    direction = "rising" if delta > 5 else "falling" if delta < -5 else "stable"
    return (
        f"{direction.title()} from {history[-1]['classification']} ({oldest}) "
        f"→ {history[0]['classification']} ({newest}) over 7 days"
    )


def build_context() -> str:
    """
    Build a one-line context string for injection into writer prompts.
    Empty string if unavailable.
    """
    current = get_current()
    if not current:
        return ""

    v = current["value"]
    c = current["classification"]
    trend = get_trend()

    # Contextual note for extreme readings
    note = ""
    if v <= 20:
        note = " — historically a strong contrarian buy signal"
    elif v >= 80:
        note = " — historically when retail gets wrecked chasing tops"
    elif v <= 35:
        note = " — market skewing cautious"
    elif v >= 65:
        note = " — market skewing greedy"

    line = f"Market Sentiment: Fear & Greed Index = {v}/100 ({c}){note}"
    if trend:
        line += f". Trend: {trend}"
    return line


def should_post_about_fg() -> tuple[bool, str]:
    """
    Returns (should_post, reason) — whether F&G is extreme enough to
    be worth posting about directly as a market sentiment observation.
    Threshold: <20 (extreme fear) or >80 (extreme greed).
    """
    current = get_current()
    if not current:
        return False, ""

    v = current["value"]
    if v <= 20:
        return True, f"Extreme Fear at {v} — contrarian signal worth calling out"
    if v >= 80:
        return True, f"Extreme Greed at {v} — worth warning about crowded positioning"
    return False, ""


def detect_mood_swing() -> Optional[dict]:
    """
    Detect sharp 24h movements in the Fear & Greed index.

    Returns a signal dict if any of the following are true:
      - Index moved >=15 points in 24h (big swing)
      - Index crossed into Extreme Fear (<20) from above
      - Index crossed into Extreme Greed (>80) from below

    Returns None if no significant movement or data unavailable.

    Dict keys:
      today (int), yesterday (int), delta (int),
      today_label (str), yesterday_label (str),
      crossed_extreme (bool), swing_magnitude (str),
      description (str)
    """
    history = get_history(7)
    if len(history) < 2:
        return None

    today_v = history[0]["value"]
    yesterday_v = history[1]["value"]
    today_label = history[0]["classification"]
    yesterday_label = history[1]["classification"]
    delta = today_v - yesterday_v

    crossed_extreme_fear = yesterday_v > 20 and today_v <= 20
    crossed_extreme_greed = yesterday_v < 80 and today_v >= 80
    large_swing = abs(delta) >= 15

    if not (crossed_extreme_fear or crossed_extreme_greed or large_swing):
        return None

    direction = "rising" if delta > 0 else "falling"
    if crossed_extreme_fear:
        desc = (f"F&G dropped into Extreme Fear: {yesterday_v} ({yesterday_label}) -> "
                f"{today_v} ({today_label}). Historically strong contrarian buy zone.")
    elif crossed_extreme_greed:
        desc = (f"F&G hit Extreme Greed: {yesterday_v} ({yesterday_label}) -> "
                f"{today_v} ({today_label}). Retail FOMO zone -- historically where longs get wrecked.")
    else:
        desc = (f"F&G swung {delta:+d} points in 24h: {yesterday_v} ({yesterday_label}) -> "
                f"{today_v} ({today_label}). Sentiment {direction} fast.")

    return {
        "today":          today_v,
        "yesterday":      yesterday_v,
        "delta":          delta,
        "today_label":    today_label,
        "yesterday_label": yesterday_label,
        "crossed_extreme": crossed_extreme_fear or crossed_extreme_greed,
        "swing_magnitude": "large" if large_swing else "moderate",
        "description":    desc,
    }
