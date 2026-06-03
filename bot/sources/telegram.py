"""
bot/sources/telegram.py — Telegram channel signal ingestion.

Uses Telethon (MTProto API) to scrape public crypto Telegram channels.
Requires: TELEGRAM_API_ID and TELEGRAM_API_HASH from my.telegram.org
(free — just register an app).

IMPORTANT: Telegram signals are Tier 3 (community sentiment).
They are NEVER written to vault as confirmed facts.
They are used only as sentiment context and narrative trend detection.

Channels monitored are public channels only — no private groups.
"""

from __future__ import annotations

import asyncio
import os
import logging
import time
from typing import Optional

log = logging.getLogger(__name__)

# Public Telegram channels to monitor
_CHANNELS = [
    "deFi_Made_Here",        # DeFi alpha
    "on_chain_lens",         # On-chain analysis
    "CryptoRankNews",        # Crypto news aggregator
    "AirdropHunterAlpha",    # Airdrop signals
    "HyperliquidAlpha",      # Hyperliquid community
    "kaitoai_official",      # Kaito official
    "arbitrum_official",     # Arbitrum
    "ZkSyncCommunity",       # zkSync
    "solana_official",       # Solana
    "DeFiPulse",             # DeFi updates
]

_MAX_MESSAGES = 10     # per channel
_MAX_HOURS_OLD = 24    # only fetch messages from last 24 hours


async def _fetch_channel_messages(client, channel: str, limit: int, max_hours: int) -> list[dict]:
    """Fetch recent messages from a single Telegram channel."""
    try:
        from telethon import errors  # type: ignore
        entity = await client.get_entity(channel)
        cutoff = time.time() - (max_hours * 3600)
        messages = []
        async for msg in client.iter_messages(entity, limit=limit * 3):
            if not msg.text:
                continue
            if msg.date.timestamp() < cutoff:
                break
            messages.append({
                "text": msg.text[:500],
                "date": msg.date.isoformat(),
                "channel": channel,
                "views": getattr(msg, "views", 0) or 0,
                "source_tier": 3,
                "source": f"telegram/{channel}",
            })
            if len(messages) >= limit:
                break
        return messages
    except Exception as e:
        log.warning("Telegram fetch failed for %s: %s", channel, e)
        return []


async def _fetch_all_async(
    channels: list[str],
    limit: int,
    max_hours: int,
) -> list[dict]:
    """Async fetch from all channels."""
    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")

    if not api_id or not api_hash:
        log.warning("TELEGRAM_API_ID / TELEGRAM_API_HASH not set — Telegram disabled")
        return []

    try:
        from telethon import TelegramClient  # type: ignore
        from telethon.sessions import StringSession  # type: ignore
    except ImportError:
        log.warning("telethon not installed — Telegram ingestion disabled. Run: pip install telethon")
        return []

    session_string = os.environ.get("TELEGRAM_SESSION_STRING", "")
    client = TelegramClient(
        StringSession(session_string),
        int(api_id),
        api_hash,
    )

    results = []
    try:
        await client.start()
        tasks = [_fetch_channel_messages(client, ch, limit, max_hours) for ch in channels]
        channel_results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in channel_results:
            if isinstance(r, list):
                results.extend(r)
    except Exception as e:
        log.error("Telegram client error: %s", e)
    finally:
        await client.disconnect()

    return results


def fetch_channel_messages(
    channels: Optional[list[str]] = None,
    limit: int = _MAX_MESSAGES,
    max_hours: int = _MAX_HOURS_OLD,
) -> list[dict]:
    """
    Public sync API. Fetches recent messages from public Telegram channels.
    Returns list of dicts. All are Tier 3 — community sentiment only.
    """
    chs = channels or _CHANNELS
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context — use thread executor
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    _fetch_all_async(chs, limit, max_hours)
                )
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(_fetch_all_async(chs, limit, max_hours))
    except Exception as e:
        log.error("Telegram fetch error: %s", e)
        return []


def search_channels(query: str, channels: Optional[list[str]] = None, limit: int = 5) -> list[dict]:
    """
    Filter fetched messages by keyword query.
    Simple keyword search — not API search.
    """
    all_messages = fetch_channel_messages(channels=channels, limit=50, max_hours=48)
    query_lower = query.lower()
    return [
        m for m in all_messages
        if query_lower in m["text"].lower()
    ][:limit]


def build_telegram_context(topic: str, limit: int = 5) -> str:
    """
    Build community sentiment summary from Telegram for writer context.
    Clearly marked as unconfirmed community signal.
    """
    messages = search_channels(topic, limit=limit)
    if not messages:
        return ""

    lines = [f"TELEGRAM COMMUNITY SIGNALS (sentiment only, not confirmed facts) for '{topic}':"]
    for m in messages[:limit]:
        lines.append(f"  - [{m['channel']}]: {m['text'][:150].strip()}")

    return "\n".join(lines)
