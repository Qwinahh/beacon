"""
Alpha signal detection.

Monitors sources for high-value, time-sensitive information that the
account can post on before it reaches broader crypto Twitter. Priority
items are returned with an `is_alpha` flag so the posting engine can
fast-track them regardless of the normal posting window.

Sources:
  - Very fresh RSS items (< 60 minutes old)
  - New protocols listed on DeFiLlama in the past 48h
  - GitHub releases from watched protocol repos (public API, no auth needed)
  - Exceptionally large TVL movements (> 30%)
  - Raises above a size threshold
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

from bot.config import DEFILLAMA_PROTOCOLS_URL, FOCUS_KEYWORDS
from bot.sources.defillama import RaiseItem, TvlMoverItem, fetch_raises, fetch_tvl_movers
from bot.sources.rss import FeedItem, fetch_all as fetch_rss

log = logging.getLogger(__name__)

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "CryptoBot/2.0"})

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

ALPHA_RSS_MAX_AGE_MINUTES: float = 75.0     # Items younger than this are alpha-tier
ALPHA_TVL_THRESHOLD_PCT: float = 30.0       # TVL moves this large = alpha
ALPHA_RAISE_THRESHOLD_M: float = 10.0       # Raises above $10M = alpha
NEW_PROTOCOL_MAX_AGE_DAYS: int = 2          # DeFiLlama protocols added within this window

# GitHub repos to watch for new releases (owner/repo format).
# Add protocol repos here as you expand your focus.
WATCHED_REPOS: list[str] = [
    "hyperliquid-dex/hyperliquid",
    "jito-foundation/jito-solana",
    "meteora-ag/dlmm-sdk",
    "pyth-network/pyth-client",
    "LayerZero-Labs/LayerZero",
]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class AlphaSignal:
    """A high-priority item surfaced by the alpha detector."""
    kind: str                    # "rss_fresh" | "new_protocol" | "tvl_spike" | "big_raise" | "github_release"
    title: str
    source: str
    url: Optional[str]
    published_ts: float
    topic: str
    urgency: int                 # 1–3: 1=watch, 2=post soon, 3=post now
    meta: dict = field(default_factory=dict)

    @property
    def age_hours(self) -> float:
        return (time.time() - self.published_ts) / 3600.0


# ---------------------------------------------------------------------------
# Detection functions
# ---------------------------------------------------------------------------

def _fresh_rss_alpha(max_age_minutes: float = ALPHA_RSS_MAX_AGE_MINUTES) -> list[AlphaSignal]:
    """Surface RSS items published within the last hour."""
    signals: list[AlphaSignal] = []
    for item in fetch_rss(max_age_hours=max_age_minutes / 60.0):
        t = item.title.lower()
        # Only alpha if it hits a focus keyword or a major catalyst
        catalysts = ["airdrop", "launch", "tge", "raise", "listing", "exploit", "hack", "upgrade"]
        is_relevant = any(k in t for k in FOCUS_KEYWORDS) or any(c in t for c in catalysts)
        if not is_relevant:
            continue
        urgency = 3 if item.age_hours < 0.5 else 2
        signals.append(AlphaSignal(
            kind="rss_fresh",
            title=item.title,
            source=item.source,
            url=item.url,
            published_ts=item.published_ts,
            topic=item.topic,
            urgency=urgency,
        ))
    return signals


def _new_defillama_protocols(max_age_days: int = NEW_PROTOCOL_MAX_AGE_DAYS) -> list[AlphaSignal]:
    """
    Find protocols that appeared on DeFiLlama recently.
    DeFiLlama doesn't expose a creation date, so we use very low TVL
    combined with a TVL spike as a proxy for 'newly listed'.
    """
    signals: list[AlphaSignal] = []
    try:
        resp = _SESSION.get(DEFILLAMA_PROTOCOLS_URL, timeout=15)
        resp.raise_for_status()
        protocols = resp.json()
        if not isinstance(protocols, list):
            return []

        cutoff = time.time() - (max_age_days * 86400)
        for p in protocols:
            # DeFiLlama includes a listedAt timestamp on some protocols
            listed_at = p.get("listedAt")
            if not listed_at:
                continue
            try:
                listed_ts = float(listed_at)
            except (TypeError, ValueError):
                continue
            if listed_ts < cutoff:
                continue

            name     = str(p.get("name", "")).strip()
            tvl      = p.get("tvl") or 0
            category = str(p.get("category", "")).strip()
            slug     = p.get("slug", "")
            url      = f"https://defillama.com/protocol/{slug}" if slug else None

            if not name or float(tvl) < 500_000:   # Skip tiny protocols with no traction
                continue

            t = name.lower() + " " + category.lower()
            is_relevant = any(k in t for k in FOCUS_KEYWORDS)

            from bot.sources.rss import _classify_topic
            signals.append(AlphaSignal(
                kind="new_protocol",
                title=f"{name} listed on DeFiLlama ({category})",
                source="DeFiLlama New",
                url=url,
                published_ts=listed_ts,
                topic=_classify_topic(t),
                urgency=2 if is_relevant else 1,
                meta={"name": name, "tvl": tvl, "category": category},
            ))
    except Exception as exc:
        log.warning("Failed to fetch new DeFiLlama protocols: %s", exc)
    return signals


def _tvl_spikes() -> list[AlphaSignal]:
    """Surface unusually large TVL moves."""
    signals: list[AlphaSignal] = []
    for item in fetch_tvl_movers(min_change_pct=ALPHA_TVL_THRESHOLD_PCT):
        urgency = 3 if abs(item.change_pct) >= 50 else 2
        signals.append(AlphaSignal(
            kind="tvl_spike",
            title=f"{item.name} TVL {'up' if item.change_pct > 0 else 'down'} {abs(item.change_pct):.1f}% in 24h",
            source="DeFiLlama TVL",
            url=item.url,
            published_ts=time.time(),
            topic=item.topic,
            urgency=urgency,
            meta=item.meta,
        ))
    return signals


def _big_raises() -> list[AlphaSignal]:
    """Surface funding rounds above the alpha threshold."""
    signals: list[AlphaSignal] = []
    for item in fetch_raises():
        if item.amount is None or item.amount < ALPHA_RAISE_THRESHOLD_M:
            continue
        if item.age_hours > 48:
            continue
        urgency = 3 if item.amount >= 30 else 2
        signals.append(AlphaSignal(
            kind="big_raise",
            title=f"{item.name} raises ${item.amount:.0f}M ({item.round_name})",
            source="DeFiLlama Raises",
            url=item.url,
            published_ts=item.published_ts,
            topic=item.topic,
            urgency=urgency,
            meta=item.meta,
        ))
    return signals


def _github_releases() -> list[AlphaSignal]:
    """
    Check watched protocol repos for releases in the past 48 hours.
    Uses GitHub's public API — no token required, but rate-limited to 60 req/h.
    The GITHUB_TOKEN env var (available in Actions) raises this to 5000 req/h.
    """
    import os
    signals: list[AlphaSignal] = []
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    cutoff = time.time() - 48 * 3600

    for repo in WATCHED_REPOS:
        try:
            resp = _SESSION.get(
                f"https://api.github.com/repos/{repo}/releases/latest",
                headers=headers,
                timeout=10,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            published = data.get("published_at", "")
            if not published:
                continue

            from dateutil import parser as dateparser
            from datetime import timezone
            dt = dateparser.parse(published)
            ts = dt.replace(tzinfo=timezone.utc).timestamp() if dt.tzinfo is None else dt.timestamp()

            if ts < cutoff:
                continue

            tag  = data.get("tag_name", "")
            name = repo.split("/")[-1].replace("-", " ").title()
            body = (data.get("body") or "")[:200]

            from bot.sources.rss import _classify_topic
            signals.append(AlphaSignal(
                kind="github_release",
                title=f"{name} released {tag}",
                source=f"GitHub ({repo})",
                url=data.get("html_url"),
                published_ts=ts,
                topic=_classify_topic(f"{name} {body}"),
                urgency=2,
                meta={"repo": repo, "tag": tag, "body": body},
            ))
        except Exception as exc:
            log.debug("GitHub release check failed for %s: %s", repo, exc)

    return signals


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def detect_all() -> list[AlphaSignal]:
    """
    Run all alpha detectors and return signals sorted by urgency
    (highest first) then by recency.
    """
    signals: list[AlphaSignal] = []
    signals.extend(_fresh_rss_alpha())
    signals.extend(_new_defillama_protocols())
    signals.extend(_tvl_spikes())
    signals.extend(_big_raises())
    signals.extend(_github_releases())

    # Hyperliquid funding rate signals (fails silently if SDK not installed).
    try:
        from bot.sources.hyperliquid import fetch_funding_signals
        signals.extend(fetch_funding_signals())
    except Exception as exc:
        log.debug("Hyperliquid signals skipped: %s", exc)


    # Token unlock signals from DeFiLlama.
    try:
        from bot.sources.unlocks import fetch_unlock_signals
        signals.extend(fetch_unlock_signals())
    except Exception as exc:
        log.debug("Unlock signals skipped: %s", exc)

    # Large on-chain whale transactions.
    try:
        from bot.sources.whale_alert import get_whale_alerts
        for w in get_whale_alerts(lookback_minutes=90):
            if w.amount_usd >= 100_000_000:
                urgency = 3
            elif w.amount_usd >= 20_000_000:
                urgency = 2
            else:
                urgency = 1
            signals.append(AlphaSignal(
                kind="whale",
                title=w.summary(),
                source="Whale Alert",
                url=None,
                published_ts=w.published_ts,
                topic="whale",
                urgency=urgency,
                meta={"chain": w.chain, "symbol": w.symbol, "amount_usd": w.amount_usd,
                      "from_type": w.from_type, "to_type": w.to_type},
            ))
    except Exception as exc:
        log.debug("Whale alert signals skipped: %s", exc)

    # Deduplicate by title (case-insensitive)
    seen_titles: set[str] = set()
    unique: list[AlphaSignal] = []
    for s in signals:
        key = s.title.lower()[:60]
        if key not in seen_titles:
            seen_titles.add(key)
            unique.append(s)

    unique.sort(key=lambda x: (x.urgency, -x.age_hours), reverse=True)
    log.info("Alpha detector: %d signals found.", len(unique))
    return unique
