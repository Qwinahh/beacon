"""
Schedule optimizer — auto-tunes the bot's posting hours from real performance.

Runs weekly (the `retime` job). Reads the post log, computes average impressions
per UTC hour over a trailing window, picks the best-performing hours, and writes
data/growth/posting_schedule.json. post.py reads that file as a gate, so the bot
gradually shifts toward the hours that actually land.

Guardrails (so it can never drift to bad times):
  - Only ever selects hours inside the allowed window (08-22 UTC).
  - Keeps a fixed number of slots (MAX_POSTS_PER_DAY).
  - Enforces a minimum gap between slots (respects the post cooldown, avoids
    clustering and audience fatigue).
  - Falls back to the default windows when there isn't enough measured data.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from bot.config import POST_LOG_PATH, MAX_POSTS_PER_DAY

log = logging.getLogger(__name__)

SCHEDULE_PATH = Path("data/growth/posting_schedule.json")

# ---- Guardrails -----------------------------------------------------------
ALLOWED_START, ALLOWED_END = 8, 22          # inclusive UTC hours posting may happen
DEFAULT_HOURS = [8, 11, 14, 17, 20, 22]     # safe fallback (the seeded windows)
TRAILING_DAYS = 28                          # how far back to learn from
MIN_MEASURED_POSTS = 10                     # need this much signal before tuning at all
MIN_GAP_HOURS = 2                           # spacing between chosen slots


def _load_post_log() -> list[dict]:
    p = Path(POST_LOG_PATH)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _posted_ts(entry: dict) -> float:
    raw = entry.get("posted_at", "")
    if isinstance(raw, (int, float)):
        return float(raw)
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def _avg_impressions_by_hour(entries: list[dict]) -> tuple[dict[int, float], int]:
    now = datetime.now(timezone.utc).timestamp()
    cutoff = now - TRAILING_DAYS * 86400
    buckets: dict[int, list[float]] = {}
    measured = 0
    for e in entries:
        imp = e.get("impressions")
        ts = _posted_ts(e)
        if not imp or ts < cutoff:
            continue
        hour = datetime.fromtimestamp(ts, timezone.utc).hour
        buckets.setdefault(hour, []).append(float(imp))
        measured += 1
    averages = {h: sum(v) / len(v) for h, v in buckets.items()}
    return averages, measured


def _pick_hours(averages: dict[int, float]) -> list[int]:
    """Greedy: best avg first, keeping slots >= MIN_GAP_HOURS apart, within window."""
    ranked = sorted(
        ((h, a) for h, a in averages.items() if ALLOWED_START <= h <= ALLOWED_END),
        key=lambda x: x[1],
        reverse=True,
    )
    chosen: list[int] = []
    for h, _ in ranked:
        if len(chosen) >= MAX_POSTS_PER_DAY:
            break
        if all(abs(h - c) >= MIN_GAP_HOURS for c in chosen):
            chosen.append(h)
    # Backfill from defaults if the gap constraint left us short.
    for d in DEFAULT_HOURS:
        if len(chosen) >= MAX_POSTS_PER_DAY:
            break
        if d not in chosen and all(abs(d - c) >= MIN_GAP_HOURS for c in chosen):
            chosen.append(d)
    return sorted(chosen)


def optimize() -> dict:
    averages, measured = _avg_impressions_by_hour(_load_post_log())

    if measured < MIN_MEASURED_POSTS:
        hours = DEFAULT_HOURS
        source = f"default ({measured} measured posts, need {MIN_MEASURED_POSTS} to tune)"
    else:
        hours = _pick_hours(averages)
        source = f"tuned from {measured} measured posts (trailing {TRAILING_DAYS}d)"

    payload = {
        "active_hours_utc": hours,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": source,
        "avg_impressions_by_hour": {str(h): round(a) for h, a in sorted(averages.items())},
        "guardrails": {
            "allowed_window_utc": [ALLOWED_START, ALLOWED_END],
            "slots": MAX_POSTS_PER_DAY,
            "min_gap_hours": MIN_GAP_HOURS,
        },
    }
    SCHEDULE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    log.info("Posting schedule -> %s (%s)", hours, source)
    return payload


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
    optimize()
