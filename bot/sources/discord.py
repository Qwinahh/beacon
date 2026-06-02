"""
Discord community signal ingestion.

Reads messages from Discord channels via the Discord Bot API (v10).
Requires DISCORD_BOT_TOKEN (GitHub Secret) and DISCORD_CHANNEL_IDS
(comma-separated numeric channel IDs).

The bot must be in the server and have Read Messages permission.

Community signals — tier 3. Never written as confirmed facts.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

log = logging.getLogger(__name__)

_BASE = "https://discord.com/api/v10"


@dataclass
class DiscordSignal:
    channel_id: str
    author: str
    text: str
    message_id: str
    date_ts: float
    tier: str = "community"
    kind: str = "discord"
    meta: dict = field(default_factory=dict)

    @property
    def age_hours(self) -> float:
        return (time.time() - self.date_ts) / 3600.0


def _get_token() -> Optional[str]:
    return os.environ.get("DISCORD_BOT_TOKEN")


def _get_channel_ids() -> list[str]:
    raw = os.environ.get("DISCORD_CHANNEL_IDS", "")
    return [c.strip() for c in raw.split(",") if c.strip()]


def _snowflake_to_ts(snowflake: int) -> float:
    """Convert Discord snowflake ID to Unix timestamp."""
    return ((snowflake >> 22) + 1420070400000) / 1000.0


def fetch_channel_messages(channel_id: str, limit: int = 20) -> list[DiscordSignal]:
    """Fetch recent messages from a Discord channel."""
    token = _get_token()
    if not token:
        return []

    signals: list[DiscordSignal] = []
    try:
        headers = {"Authorization": f"Bot {token}"}
        resp = requests.get(
            f"{_BASE}/channels/{channel_id}/messages",
            headers=headers,
            params={"limit": limit},
            timeout=10,
        )
        if resp.status_code == 403:
            log.warning("Discord: no access to channel %s (403 Forbidden)", channel_id)
            return []
        resp.raise_for_status()

        for msg in resp.json():
            content = msg.get("content", "").strip()
            # Skip empty messages, system messages, and bot messages.
            if not content or msg.get("type", 0) != 0:
                continue
            author = msg.get("author", {})
            if author.get("bot"):
                continue
            msg_id = msg.get("id", "0")
            ts     = _snowflake_to_ts(int(msg_id)) if msg_id != "0" else time.time()
            signals.append(DiscordSignal(
                channel_id=channel_id,
                author=author.get("username", "unknown"),
                text=content[:500],
                message_id=msg_id,
                date_ts=ts,
                meta={"channel_id": channel_id, "author": author.get("username", "")},
            ))
    except Exception as exc:
        log.warning("Discord fetch failed for channel %s: %s", channel_id, exc)
    return signals


def fetch_all_signals(limit: int = 20) -> list[DiscordSignal]:
    """Fetch signals from all configured Discord channels."""
    channel_ids = _get_channel_ids()
    if not channel_ids:
        return []
    signals: list[DiscordSignal] = []
    for ch in channel_ids:
        signals.extend(fetch_channel_messages(ch, limit=limit))
    signals.sort(key=lambda x: x.date_ts, reverse=True)
    log.info("Discord: %d signals from %d channels.", len(signals), len(channel_ids))
    return signals
