"""
DropsTab token unlock data source.

DropsTab provides structured token unlock data via REST API.
Free Builders Program: signup at dropstab.com/about/builders-program
Set DROPSTAB_API_KEY in GitHub Secrets after signup.

Returns upcoming unlocks for the next 7 days — high-value post material
because unlock events reliably generate CT discussion and price moves.

Falls back to empty list if no API key or request fails.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

log = logging.getLogger(__name__)

_API_KEY_ENV     = "DROPSTAB_API_KEY"
_API_BASE        = "https://api.dropstab.com/api"
_MIN_UNLOCK_USD  = 5_000_000
_LOOKAHEAD_DAYS  = 7


@dataclass
class UnlockItem:
    project:       str
    symbol:        str
    unlock_ts:     float
    amount_tokens: float
    amount_usd:    Optional[float]
    recipient:     str
    unlock_type:   str
    published_ts:  float = field(default_factory=time.time)
    topic:         str = "unlock"
    kind:          str = "unlock"

    @property
    def days_until(self) -> float:
        return (self.unlock_ts - time.time()) / 86400

    @property
    def age_hours(self) -> float:
        return (time.time() - self.published_ts) / 3600.0

    def summary(self) -> str:
        usd = f" (~${self.amount_usd / 1_000_000:.1f}M)" if self.amount_usd else ""
        days = f"{self.days_until:.1f}d"
        return (
            f"{self.project} ({self.symbol}): {self.amount_tokens:,.0f} tokens{usd} "
            f"unlock in {days} — recipient: {self.recipient}"
        )


def get_upcoming_unlocks() -> list[UnlockItem]:
    """
    Return upcoming token unlocks in the next LOOKAHEAD_DAYS days.
    Sorted by unlock time ascending (soonest first).
    Always returns a list — fails silently.
    """
    api_key = os.environ.get(_API_KEY_ENV, "").strip()
    if not api_key:
        log.debug("No DROPSTAB_API_KEY set — token unlock data unavailable")
        return []

    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        resp = requests.get(
            f"{_API_BASE}/unlocks/upcoming",
            headers=headers,
            params={"days": _LOOKAHEAD_DAYS, "limit": 50},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        log.warning("DropsTab API error: %s", exc)
        return []

    items = []
    now = time.time()

    for entry in data.get("data", data if isinstance(data, list) else []):
        try:
            amount_usd = float(entry.get("valueUsd") or entry.get("amount_usd") or 0)
            if amount_usd and amount_usd < _MIN_UNLOCK_USD:
                continue

            unlock_ts_raw = entry.get("date") or entry.get("unlockDate") or entry.get("timestamp")
            if not unlock_ts_raw:
                continue
            if isinstance(unlock_ts_raw, (int, float)):
                unlock_ts = float(unlock_ts_raw)
            else:
                from dateutil import parser as dateparser
                unlock_ts = dateparser.parse(str(unlock_ts_raw)).timestamp()

            if unlock_ts < now:
                continue

            items.append(UnlockItem(
                project       = entry.get("project") or entry.get("name") or "Unknown",
                symbol        = (entry.get("symbol") or entry.get("ticker") or "?").upper(),
                unlock_ts     = unlock_ts,
                amount_tokens = float(entry.get("amount") or entry.get("tokens") or 0),
                amount_usd    = amount_usd or None,
                recipient     = entry.get("category") or entry.get("recipient") or "unknown",
                unlock_type   = entry.get("type") or entry.get("unlockType") or "vesting",
            ))
        except Exception as exc:
            log.debug("Skipping unlock entry: %s", exc)
            continue

    items.sort(key=lambda x: x.unlock_ts)
    log.debug("DropsTab: %d upcoming unlocks in next %dd", len(items), _LOOKAHEAD_DAYS)
    return items[:15]
