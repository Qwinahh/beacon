"""
Telegram community signal ingestion.

Reads messages from public Telegram channels via the Bot API.
Requires TELEGRAM_BOT_TOKEN (GitHub Secret) and TELEGRAM_CHANNEL_IDS
(comma-separated channel usernames, e.g. "@channel1,@channel2").

The bot must be added as an admin/member to each channel to read posts.

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

_BASE = "https://api.telegram.org"


@dataclass
class TelegramSignal:
    channel: str
    text: str
    message_id: int
    date_ts: float
    views: int = 0
    tier: str = "community"
    kind: str = "telegram"
    meta: dict = field(default_factory=dict)

    @property
    def age_hours(self) -> float:
        return (time.time() - self.date_ts) / 3600.0


def _get_token() -> Optional[str]:
    return os.environ.get("TELEGRAM_BOT_TOKEN")


def _get_channels() -> list[str]:
    raw = os.environ.get("TELEGRAM_CHANNEL_IDS", "")
    return [c.strip() for c in raw.split(",") if c.strip()]


def fetch_channel_messages(channel: str, limit: int = 10) -> list[TelegramSignal]:
    """
    Fetch recent channel_post updates for a channel the bot is a member of.

    Telegram's Bot API only delivers updates for channels where the bot
    has been added. Use getUpdates filtered to channel_post.
    """
    token = _get_token()
    if not token:
        return []

    signals: list[TelegramSignal] = []
    try:
        # Verify we can see the channel.
        chat_resp = requests.get(
            f"{_BASE}/bot{token}/getChat",
            params={"chat_id": channel},
            timeout=8,
        )
        if not chat_resp.ok:
            log.warning("Telegram: cannot access channel '%s'", channel)
            return []

        updates_resp = requests.get(
            f"{_BASE}/bot{token}/getUpdates",
            params={"limit": 100, "allowed_updates": ["channel_post"]},
            timeout=10,
        )
        updates_resp.raise_for_status()
        updates = updates_resp.json().get("result", [])

        channel_username = channel.lstrip("@")
        for upd in updates[-limit:]:
            post = upd.get("channel_post") or upd.get("message")
            if not post:
                continue
            chat = post.get("chat", {})
            if chat.get("username") != channel_username:
                continue
            text = post.get("text") or post.get("caption") or ""
            if not text.strip():
                continue
            signals.append(TelegramSignal(
                channel=channel,
                text=text[:500],
                message_id=post.get("message_id", 0),
                date_ts=float(post.get("date", time.time())),
                views=post.get("views", 0),
                meta={"channel": channel, "message_id": post.get("message_id", 0)},
            ))
    except Exception as exc:
        log.warning("Telegram fetch failed for %s: %s", channel, exc)
    return signals


def fetch_all_signals(limit: int = 10) -> list[TelegramSignal]:
    """Fetch signals from all configured Telegram channels."""
    channels = _get_channels()
    if not channels:
        return []
    signals: list[TelegramSignal] = []
    for ch in channels:
        signals.extend(fetch_channel_messages(ch, limit=limit))
    signals.sort(key=lambda x: x.date_ts, reverse=True)
    log.info("Telegram: %d signals from %d channels.", len(signals), len(channels))
    return signals
