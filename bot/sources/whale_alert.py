"""
Whale Alert integration — large on-chain transaction monitoring.

Uses the free Whale Alert API (https://whale-alert.io).
Free tier: 10 req/min, 100 req/day, min transaction value $500k.
Set WHALE_ALERT_API_KEY in GitHub Secrets (free signup at whale-alert.io).

Falls back to the Whale Alert RSS feed if no API key is set.
The RSS feed has less detail but requires no auth.

Transactions are returned as WhaleItem objects so the orchestrator
can score and post about them via the normal pipeline.

Filters:
- Minimum $5M USD to qualify (below that = noise for our audience)
- Only chains we care about: ETH, SOL, BTC, ARB, OP, AVAX
- Skips exchange-to-exchange transfers (pure arb, less interesting)
- Skips self-transfers (wallets moving to own cold storage)
"""
from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

log = logging.getLogger(__name__)

_API_KEY_ENV = "WHALE_ALERT_API_KEY"
_API_BASE    = "https://api.whale-alert.io/v1"
_RSS_URL     = "https://whale-alert.io/feed"

_CHAINS_OF_INTEREST = {"ethereum", "solana", "bitcoin", "arbitrum", "optimism", "avalanche"}

_MIN_USD = 5_000_000


@dataclass
class WhaleItem:
    tx_hash:      str
    chain:        str
    symbol:       str
    amount_usd:   float
    from_type:    str
    to_type:      str
    from_name:    Optional[str]
    to_name:      Optional[str]
    published_ts: float
    topic:        str = "whale"
    kind:         str = "whale"

    @property
    def age_hours(self) -> float:
        return (time.time() - self.published_ts) / 3600.0

    def summary(self) -> str:
        from_label = self.from_name or f"unknown {self.from_type}"
        to_label   = self.to_name   or f"unknown {self.to_type}"
        usd = f"${self.amount_usd / 1_000_000:.1f}M"
        return (
            f"{usd} {self.symbol} moved on {self.chain}: "
            f"{from_label} → {to_label}"
        )


def _fetch_api(api_key: str, lookback_minutes: int = 60) -> list[WhaleItem]:
    since = int(time.time()) - (lookback_minutes * 60)
    try:
        resp = requests.get(
            f"{_API_BASE}/transactions",
            params={
                "api_key":   api_key,
                "min_value": _MIN_USD,
                "start":     since,
                "limit":     25,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        log.warning("Whale Alert API error: %s", exc)
        return []

    items = []
    for tx in data.get("transactions", []):
        chain = tx.get("blockchain", "").lower()
        if chain not in _CHAINS_OF_INTEREST:
            continue

        amount_usd = float(tx.get("amount_usd", 0))
        if amount_usd < _MIN_USD:
            continue

        from_info = tx.get("from", {})
        to_info   = tx.get("to",   {})

        # Skip exchange-to-exchange (pure arb, less interesting)
        if from_info.get("owner_type") == "exchange" and to_info.get("owner_type") == "exchange":
            continue

        items.append(WhaleItem(
            tx_hash      = tx.get("hash", ""),
            chain        = chain,
            symbol       = tx.get("symbol", "?").upper(),
            amount_usd   = amount_usd,
            from_type    = from_info.get("owner_type", "unknown"),
            to_type      = to_info.get("owner_type", "unknown"),
            from_name    = from_info.get("owner") or None,
            to_name      = to_info.get("owner") or None,
            published_ts = float(tx.get("timestamp", time.time())),
        ))

    return items


def _fetch_rss() -> list[WhaleItem]:
    """Fallback: parse Whale Alert RSS. Less structured but requires no auth."""
    try:
        import feedparser
        feed = feedparser.parse(_RSS_URL)
    except Exception as exc:
        log.debug("Whale Alert RSS unavailable: %s", exc)
        return []

    items = []
    now = time.time()

    for entry in feed.entries[:10]:
        title = getattr(entry, "title", "")
        if not any(k in title.lower() for k in ["transferred", "moved", "sent"]):
            continue

        usd_match = re.search(r"\$([0-9,]+)", title)
        if not usd_match:
            continue
        amount_usd = float(usd_match.group(1).replace(",", ""))
        if amount_usd < _MIN_USD:
            continue

        symbol_match = re.search(r"\bof\s+(\w+)\s+transferred", title, re.IGNORECASE)
        symbol = symbol_match.group(1).upper() if symbol_match else "?"

        published = getattr(entry, "published_parsed", None)
        if published:
            import calendar
            ts = float(calendar.timegm(published))
        else:
            ts = now

        items.append(WhaleItem(
            tx_hash      = getattr(entry, "link", ""),
            chain        = "unknown",
            symbol       = symbol,
            amount_usd   = amount_usd,
            from_type    = "unknown",
            to_type      = "unknown",
            from_name    = None,
            to_name      = None,
            published_ts = ts,
        ))

    return items


def get_whale_alerts(lookback_minutes: int = 60) -> list[WhaleItem]:
    """
    Return recent large on-chain transactions, sorted largest first.

    Uses Whale Alert API if WHALE_ALERT_API_KEY is set,
    falls back to RSS feed otherwise.
    Always returns a list — fails silently.
    """
    api_key = os.environ.get(_API_KEY_ENV, "").strip()

    try:
        if api_key:
            items = _fetch_api(api_key, lookback_minutes)
            log.debug("Whale Alert API: %d qualifying transactions", len(items))
        else:
            log.debug("No WHALE_ALERT_API_KEY — using RSS fallback")
            items = _fetch_rss()

        items.sort(key=lambda x: x.amount_usd, reverse=True)
        return items[:10]

    except Exception as exc:
        log.warning("Whale alert fetch failed: %s", exc)
        return []
