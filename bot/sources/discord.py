"""
bot/sources/discord.py — Discord community signal ingestion.

Uses Discord Bot API (read-only) to scrape public/accessible server channels.
Requires: DISCORD_BOT_TOKEN env var.
Bot must be added to each server — use public servers only or servers you're in.

IMPORTANT: Discord signals are Tier 3 (community sentiment).
They are NEVER written to vault as confirmed facts.
Used only for: narrative trend detection, community concern signals, sentiment context.

Setup:
  1. Go to discord.com/developers/applications
  2. Create a new application → Bot tab → Reset Token → copy token
  3. Enable "Message Content Intent" under Privileged Gateway Intents
  4. Generate invite URL with scopes: bot + permissions: Read Messages/View Channels
  5. Add bot to relevant servers
  6. Set DISCORD_BOT_TOKEN in GitHub Secrets
"""

from __future__ import annotations

import asyncio
import os
import logging
import time
from typing import Optional

log = logging.getLogger(__name__)

# Channel IDs to monitor (format: server_name:channel_id)
# Add real channel IDs after bot is set up in target servers
_CHANNEL_CONFIGS = [
    # Example format — replace with real IDs after bot setup
    # {"name": "hyperliquid-general", "id": "1234567890"},
    # {"name": "kaito-alpha", "id": "0987654321"},
]

_MAX_MESSAGES = 15
_MAX_HOURS_OLD = 12


async def _fetch_discord_async(channel_configs: list[dict], limit: int, max_hours: int) -> list[dict]:
    """Fetch messages from Discord channels using discord.py."""
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        log.warning("DISCORD_BOT_TOKEN not set — Discord ingestion disabled")
        return []

    try:
        import discord  # type: ignore
    except ImportError:
        log.warning("discord.py not installed — Discord disabled. Run: pip install discord.py")
        return []

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    results = []

    @client.event
    async def on_ready():
        nonlocal results
        cutoff = time.time() - (max_hours * 3600)
        for config in channel_configs:
            try:
                channel = client.get_channel(int(config["id"]))
                if not channel:
                    continue
                async for msg in channel.history(limit=limit * 3):
                    if msg.created_at.timestamp() < cutoff:
                        break
                    if not msg.content or msg.author.bot:
                        continue
                    results.append({
                        "text": msg.content[:500],
                        "author": str(msg.author),
                        "channel": config["name"],
                        "date": msg.created_at.isoformat(),
                        "source_tier": 3,
                        "source": f"discord/{config['name']}",
                    })
                    if len([r for r in results if r["channel"] == config["name"]]) >= limit:
                        break
            except Exception as e:
                log.warning("Discord channel fetch failed for %s: %s", config.get("name"), e)

        await client.close()

    try:
        await client.start(token)
    except Exception as e:
        log.error("Discord client error: %s", e)

    return results


def fetch_channel_messages(
    channel_configs: Optional[list[dict]] = None,
    limit: int = _MAX_MESSAGES,
    max_hours: int = _MAX_HOURS_OLD,
) -> list[dict]:
    """
    Public sync API. Fetch messages from configured Discord channels.
    Returns list of dicts. All Tier 3 — community sentiment only.
    Falls back to empty list gracefully if bot not configured.
    """
    configs = channel_configs or _CHANNEL_CONFIGS
    if not configs:
        log.debug("No Discord channels configured — skipping")
        return []

    try:
        return asyncio.run(_fetch_discord_async(configs, limit, max_hours))
    except Exception as e:
        log.error("Discord fetch error: %s", e)
        return []


def build_discord_context(topic: str, limit: int = 5) -> str:
    """
    Build community sentiment from Discord for writer context.
    Clearly marked as unconfirmed community signal.
    """
    messages = fetch_channel_messages()
    if not messages:
        return ""

    topic_lower = topic.lower()
    relevant = [m for m in messages if topic_lower in m["text"].lower()][:limit]
    if not relevant:
        return ""

    lines = [f"DISCORD COMMUNITY SIGNALS (sentiment only, not confirmed facts) for '{topic}':"]
    for m in relevant:
        lines.append(f"  - [{m['channel']}]: {m['text'][:150].strip()}")

    return "\n".join(lines)


def add_channel(name: str, channel_id: str) -> None:
    """
    Helper to add a new Discord channel to monitor.
    Call this once to add channels, then update _CHANNEL_CONFIGS directly.
    """
    entry = {"name": name, "id": channel_id}
    if entry not in _CHANNEL_CONFIGS:
        _CHANNEL_CONFIGS.append(entry)
        log.info("Added Discord channel: %s (%s)", name, channel_id)
