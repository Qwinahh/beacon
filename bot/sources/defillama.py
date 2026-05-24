"""
DeFiLlama data source.

Provides two datasets:
- Funding rounds (raises), updated daily by the DeFiLlama team.
- TVL movers: protocols whose 24h TVL changed significantly.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import requests
from dateutil import parser as dateparser

from bot.config import (
    DEFILLAMA_PROTOCOLS_URL,
    DEFILLAMA_RAISES_URL,
    RAISES_FETCH_LIMIT,
    TVL_MIN_CHANGE_PCT,
)
from bot.sources.rss import _classify_topic  # reuse the same classifier

log = logging.getLogger(__name__)

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "CryptoBot/2.0"})


@dataclass
class RaiseItem:
    name: str
    amount: Optional[float]   # USD millions
    round_name: str
    category: str
    url: Optional[str]
    published_ts: float
    topic: str = "raise"
    kind: str = "raise"
    meta: dict = field(default_factory=dict)

    @property
    def age_hours(self) -> float:
        return (time.time() - self.published_ts) / 3600.0


@dataclass
class TvlMoverItem:
    name: str
    change_pct: float          # 24h change
    tvl_usd: float
    category: str
    url: Optional[str]
    topic: str = "defi"
    kind: str = "tvl"
    meta: dict = field(default_factory=dict)

    @property
    def age_hours(self) -> float:
        return 0.0  # always "current"


def fetch_raises(limit: int = RAISES_FETCH_LIMIT) -> list[RaiseItem]:
    """Return the most recent funding rounds from DeFiLlama."""
    items: list[RaiseItem] = []
    try:
        resp = _SESSION.get(DEFILLAMA_RAISES_URL, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            data = data.get("raises", data)
        if not isinstance(data, list):
            return []

        for row in data[:limit]:
            name = str(row.get("name", "")).strip()
            if not name:
                continue

            amount = None
            raw_amount = row.get("amount")
            try:
                amount = float(raw_amount) if raw_amount is not None else None
            except (TypeError, ValueError):
                pass

            ts = time.time()
            raw_date = row.get("date")
            if raw_date:
                try:
                    dt = dateparser.parse(str(raw_date))
                    ts = dt.timestamp()
                except Exception:
                    pass

            round_name = str(row.get("round", "")).strip()
            category   = str(row.get("category", "")).strip()
            link       = row.get("link") or row.get("article")

            items.append(RaiseItem(
                name=name,
                amount=amount,
                round_name=round_name,
                category=category,
                url=link if isinstance(link, str) else None,
                published_ts=ts,
                topic=_classify_topic(f"{name} {category} {round_name}"),
                meta={"name": name, "amount": amount, "round": round_name, "category": category},
            ))

        items.sort(key=lambda x: x.published_ts, reverse=True)
        log.info("DeFiLlama raises: %d items fetched.", len(items))
    except Exception as exc:
        log.warning("Failed to fetch DeFiLlama raises: %s", exc)
    return items


def fetch_tvl_movers(min_change_pct: float = TVL_MIN_CHANGE_PCT) -> list[TvlMoverItem]:
    """Return protocols with the largest 24h TVL movements."""
    items: list[TvlMoverItem] = []
    try:
        resp = _SESSION.get(DEFILLAMA_PROTOCOLS_URL, timeout=15)
        resp.raise_for_status()
        protocols = resp.json()
        if not isinstance(protocols, list):
            return []

        for p in protocols:
            name = str(p.get("name", "")).strip()
            if not name:
                continue
            try:
                tvl      = float(p["tvl"])
                change   = float(p["change_1d"])
            except (KeyError, TypeError, ValueError):
                continue

            if abs(change) < min_change_pct or tvl < 1_000_000:
                continue

            category = str(p.get("category", "")).strip()
            slug     = p.get("slug", "")
            url      = f"https://defillama.com/protocol/{slug}" if slug else None

            items.append(TvlMoverItem(
                name=name,
                change_pct=change,
                tvl_usd=tvl,
                category=category,
                url=url,
                topic=_classify_topic(f"{name} {category}"),
                meta={"name": name, "change_pct": change, "tvl_usd": tvl, "category": category},
            ))

        items.sort(key=lambda x: abs(x.change_pct), reverse=True)
        log.info("DeFiLlama TVL movers: %d items above %.0f%% threshold.", len(items), min_change_pct)
    except Exception as exc:
        log.warning("Failed to fetch DeFiLlama protocols: %s", exc)
    return items
