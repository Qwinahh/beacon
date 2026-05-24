"""
Token unlock monitor.

Checks for large upcoming token unlocks using the Token Unlocks public API
and DeFiLlama's unlocks endpoint. A large unlock coming within 48 hours is
worth posting about -- it's the kind of forward-looking signal that makes
the account look ahead of the news rather than behind it.

Signal threshold: >$10M unlocking in the next 48 hours.
Urgency: 2 (schedule post on next window, no rush).
If >$50M: urgency 3 (post ASAP, this moves markets).
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Optional

from bot.sources.alpha import AlphaSignal

log = logging.getLogger(__name__)

# DeFiLlama unlocks endpoint.
_DEFILLAMA_UNLOCKS_URL = "https://defillama.com/unlocks/download.json"

# Minimum USD unlock value to trigger a signal.
MIN_UNLOCK_USD   = 10_000_000   # $10M
URGENT_UNLOCK_USD = 50_000_000  # $50M -- urgency-3

# Window: look for unlocks happening within this many hours from now.
UNLOCK_WINDOW_HOURS = 48


def _fetch_json(url: str, timeout: int = 8) -> Optional[list]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "qwinahh-bot/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        log.warning("Unlock fetch failed for %s: %s", url, exc)
        return None


def fetch_unlock_signals() -> list[AlphaSignal]:
    """
    Fetch upcoming token unlocks and return alpha signals for large ones.
    """
    data = _fetch_json(_DEFILLAMA_UNLOCKS_URL)
    if not data:
        return []

    signals: list[AlphaSignal] = []
    now    = time.time()
    cutoff = now + UNLOCK_WINDOW_HOURS * 3600

    for entry in data:
        try:
            # DeFiLlama unlock entry shape (approximate -- schema varies).
            unlock_ts = entry.get("unlockTimestamp") or entry.get("date")
            if isinstance(unlock_ts, str):
                from email.utils import parsedate_to_datetime
                try:
                    unlock_ts = parsedate_to_datetime(unlock_ts).timestamp()
                except Exception:
                    import datetime
                    unlock_ts = datetime.datetime.fromisoformat(
                        unlock_ts.replace("Z", "+00:00")
                    ).timestamp()

            if not isinstance(unlock_ts, (int, float)):
                continue

            # Only care about unlocks happening in the future within the window.
            if unlock_ts < now or unlock_ts > cutoff:
                continue

            usd_value = float(entry.get("totalLocked") or entry.get("usdValue") or 0)
            if usd_value < MIN_UNLOCK_USD:
                continue

            name    = entry.get("name") or entry.get("symbol") or "Unknown"
            ticker  = entry.get("symbol") or ""
            hours_until = (unlock_ts - now) / 3600

            urgency = 3 if usd_value >= URGENT_UNLOCK_USD else 2
            usd_str = f"${usd_value/1e6:.0f}M"

            signals.append(AlphaSignal(
                title=(
                    f"{name} ({ticker}) unlocking {usd_str} in ~{hours_until:.0f}h"
                ),
                kind="alpha",
                source="defillama-unlocks",
                topic=f"{name.lower()} unlock",
                urgency=urgency,
                age_hours=0.0,
                url=entry.get("url") or f"https://defillama.com/unlocks",
                meta={
                    "name":        name,
                    "ticker":      ticker,
                    "usd_value":   usd_value,
                    "hours_until": round(hours_until, 1),
                    "unlock_ts":   unlock_ts,
                    "signal":      "token_unlock",
                },
            ))

        except Exception as exc:
            log.debug("Skipping unlock entry: %s", exc)
            continue

    log.info("Unlock monitor: %d signals found.", len(signals))
    return signals
