"""
Persistent state management.

State is stored in data/state.json and committed back to the git repo
after every run. This gives durable memory without an external database.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from bot.config import (
    FINGERPRINT_MEMORY_SIZE,
    STATE_PATH,
    TOPIC_MEMORY_SIZE,
)

log = logging.getLogger(__name__)


def _load() -> dict[str, Any]:
    path = Path(STATE_PATH)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Failed to read state file: %s — starting fresh.", exc)
        return {}


def _save(state: dict[str, Any]) -> None:
    path = Path(STATE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


class State:
    """
    Thin wrapper around the JSON state file.

    Call `load()` at the start of a run and `save()` at the end.
    All mutations happen in-memory and are written in a single flush.
    """

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def load(self) -> None:
        self._data = _load()
        log.debug("State loaded: %d keys.", len(self._data))

    def save(self) -> None:
        _save(self._data)
        log.debug("State saved.")

    # ------------------------------------------------------------------
    # Daily post counter
    # ------------------------------------------------------------------

    def _today(self) -> str:
        return date.today().isoformat()

    def posts_today(self) -> int:
        return self._data.get("daily_counts", {}).get(self._today(), 0)

    def increment_post_count(self) -> None:
        self._data.setdefault("daily_counts", {})
        key = self._today()
        self._data["daily_counts"][key] = self._data["daily_counts"].get(key, 0) + 1

    # ------------------------------------------------------------------
    # Last post timestamp
    # ------------------------------------------------------------------

    def last_post_timestamp(self) -> float:
        return float(self._data.get("last_post_ts", 0))

    def set_last_post_timestamp(self, ts: float) -> None:
        self._data["last_post_ts"] = ts

    # ------------------------------------------------------------------
    # Fingerprint deduplication
    # ------------------------------------------------------------------

    @staticmethod
    def fingerprint(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:20]

    def has_seen(self, fp: str) -> bool:
        return fp in self._data.get("seen", [])

    def mark_seen(self, fp: str) -> None:
        seen: list[str] = self._data.setdefault("seen", [])
        if fp not in seen:
            seen.append(fp)
        # Trim to memory limit — remove oldest entries from the front.
        if len(seen) > FINGERPRINT_MEMORY_SIZE:
            self._data["seen"] = seen[-FINGERPRINT_MEMORY_SIZE:]

    # ------------------------------------------------------------------
    # Recent topics (for variety enforcement)
    # ------------------------------------------------------------------

    def recent_topics(self) -> list[str]:
        return self._data.get("recent_topics", [])

    def record_topic(self, topic: str) -> None:
        topics: list[str] = self._data.setdefault("recent_topics", [])
        topics.append(topic)
        if len(topics) > TOPIC_MEMORY_SIZE:
            self._data["recent_topics"] = topics[-TOPIC_MEMORY_SIZE:]

    def topic_count(self, topic: str) -> int:
        return self.recent_topics().count(topic)

    # ------------------------------------------------------------------
    # Recent formats (for format variety)
    # ------------------------------------------------------------------

    def recent_formats(self) -> list[str]:
        return self._data.get("recent_formats", [])

    def record_format(self, fmt: str) -> None:
        fmts: list[str] = self._data.setdefault("recent_formats", [])
        fmts.append(fmt)
        self._data["recent_formats"] = fmts[-20:]

    # ------------------------------------------------------------------
    # Engagement tracking
    # ------------------------------------------------------------------

    def last_replied_to(self) -> set[str]:
        return set(self._data.get("replied_to", []))

    def mark_replied(self, tweet_id: str) -> None:
        replied: list[str] = self._data.setdefault("replied_to", [])
        if tweet_id not in replied:
            replied.append(tweet_id)
        self._data["replied_to"] = replied[-200:]

    # ------------------------------------------------------------------
    # Portfolio event tracking
    # ------------------------------------------------------------------

    def posted_portfolio_keys(self) -> set[str]:
        return set(self._data.get("portfolio_posted", []))

    def mark_portfolio_posted(self, key: str) -> None:
        posted: list[str] = self._data.setdefault("portfolio_posted", [])
        if key not in posted:
            posted.append(key)
