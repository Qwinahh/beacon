"""
agents/learner_agent.py — Continuous Learning Agent

Runs on a separate schedule (2x per day) to:
1. Ingest new events from Tier 1/2 sources (on-chain, media, research)
2. Ingest community signals from Reddit, X/CT, Discord, Telegram (Tier 3)
3. Cross-reference claims against existing knowledge base
4. Write confirmed events to data/vault/knowledge/events/
5. Write unconfirmed signals to data/vault/knowledge/signals/
6. Update project files with new confirmed observations
7. Detect new narrative trends and update narrative files

Fact-checking flow:
  Raw claim → verifier.classify_source() → tier check → knowledge cross-reference
  → confirmed: write to events/ as fact
  → unconfirmed: write to signals/ as sentiment only
  → rejected: discard, log reason

The bot NEVER writes Tier 3/4 content to project files as facts.
Community signals only inform WHAT to research further via Tier 1/2 sources.
"""

from __future__ import annotations

import json
import logging
import os
import time
import re
from pathlib import Path
from typing import Optional

from bot.brain.verifier import Claim, verify, process_and_store, SourceTier
from bot.brain import vault as _vault

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Knowledge sources — Tier 1 / 2 (free, no keys needed)
# ---------------------------------------------------------------------------

_TIER1_FEEDS = [
    # DeFiLlama — protocol TVL and events (no key needed)
    "https://defillama.com/api",
    # DeFiLlama news/hacks endpoint
    "https://defillama.com/hacks",
]

_TIER2_RSS_FEEDS = [
    "https://theblock.co/rss.xml",
    "https://decrypt.co/feed",
    "https://blockworks.co/feed",
    "https://thedefiant.io/feed",
    "https://banklesshq.com/rss",
]


def _fetch_rss_articles(feed_url: str, max_items: int = 10) -> list[dict]:
    """Fetch articles from an RSS feed. Returns list of {title, link, summary, published}."""
    try:
        import feedparser  # type: ignore
        feed = feedparser.parse(feed_url)
        articles = []
        for entry in feed.entries[:max_items]:
            articles.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "summary": entry.get("summary", "")[:500],
                "published": entry.get("published", ""),
                "source": feed.feed.get("title", feed_url),
            })
        return articles
    except ImportError:
        log.warning("feedparser not installed — RSS disabled. Run: pip install feedparser")
        return []
    except Exception as e:
        log.error("RSS fetch failed for %s: %s", feed_url, e)
        return []


def _fetch_defillama_hacks() -> list[dict]:
    """Fetch recent protocol hacks from DeFiLlama's free hacks API."""
    try:
        import urllib.request, json as _json
        url = "https://defillama.com/api/hacks"  # returns JSON list of hacks
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = _json.loads(resp.read())
        # Recent hacks (last 30 days)
        cutoff = time.time() - (30 * 86400)
        recent = [h for h in data if h.get("date", 0) > cutoff]
        return recent
    except Exception as e:
        log.error("DeFiLlama hacks fetch failed: %s", e)
        return []


def _fetch_defillama_raises() -> list[dict]:
    """Fetch recent fundraising rounds from DeFiLlama."""
    try:
        import urllib.request, json as _json
        url = "https://defillama.com/api/raises"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = _json.loads(resp.read())
        raises_list = data.get("raises", [])
        cutoff = time.time() - (7 * 86400)  # last 7 days
        return [r for r in raises_list if r.get("date", 0) > cutoff]
    except Exception as e:
        log.error("DeFiLlama raises fetch failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Community sources — Tier 3
# ---------------------------------------------------------------------------

def _fetch_reddit_signals(topics: list[str]) -> list[dict]:
    """Fetch Reddit community signals for given topics."""
    try:
        from bot.sources.reddit import search_reddit
        results = []
        for topic in topics[:5]:  # limit topics to avoid rate limits
            posts = search_reddit(topic, limit=5)
            results.extend(posts)
        return results
    except Exception as e:
        log.error("Reddit signal fetch failed: %s", e)
        return []


def _fetch_x_signals(topics: list[str]) -> list[dict]:
    """Fetch X/CT community signals using existing twscrape integration."""
    try:
        from bot.sources.xcontext import fetch_topic_posts
        results = []
        for topic in topics[:5]:
            posts = fetch_topic_posts(topic, limit=8)
            for post in posts:
                results.append({
                    "text": post,
                    "source": "x/ct",
                    "source_tier": 3,
                    "topic": topic,
                })
        return results
    except Exception as e:
        log.error("X signal fetch failed: %s", e)
        return []


def _fetch_telegram_signals(topics: list[str]) -> list[dict]:
    """Fetch Telegram community signals."""
    try:
        from bot.sources.telegram import search_channels
        results = []
        for topic in topics[:3]:
            msgs = search_channels(topic, limit=5)
            results.extend(msgs)
        return results
    except Exception as e:
        log.error("Telegram signal fetch failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Narrative detection
# ---------------------------------------------------------------------------

_NARRATIVE_KEYWORDS = {
    "rwa": ["rwa", "real world asset", "tokenized", "t-bill", "ondo", "maple", "centrifuge"],
    "ai_agents": ["ai agent", "virtuals", "elizaos", "bittensor", "deai", "ai16z"],
    "depin": ["depin", "helium", "hivemapper", "io.net", "physical infrastructure"],
    "btc_defi": ["bitcoin defi", "babylon", "btc staking", "lombard", "lbtc"],
    "restaking": ["restaking", "eigenlayer", "symbiotic", "actively validated"],
    "perps_dex": ["hyperliquid", "gmx", "dydx", "perps dex", "on-chain perps"],
    "memecoins": ["memecoin", "pump.fun", "pumpfun", "solana meme"],
}


def _detect_narrative_trend(signals: list[dict]) -> dict[str, int]:
    """Count narrative mentions across all signals."""
    counts: dict[str, int] = {k: 0 for k in _NARRATIVE_KEYWORDS}
    all_text = " ".join(
        (s.get("text") or s.get("title") or "").lower()
        for s in signals
    )
    for narrative, keywords in _NARRATIVE_KEYWORDS.items():
        for kw in keywords:
            counts[narrative] += all_text.count(kw)
    return counts


# ---------------------------------------------------------------------------
# Project detection — maps article text to known project slugs
# ---------------------------------------------------------------------------

# Maps keyword → vault project slug (must match data/vault/projects/<slug>.md)
_PROJECT_KEYWORDS: dict[str, list[str]] = {
    "hyperliquid": ["hyperliquid", "hype token", "hlp", "hip-3", "hip-2"],
    "kaito":       ["kaito", "yap", "yappers", "infofi"],
    "meteora":     ["meteora", "dlmm", "dynamic liquidity"],
    "jupiter":     ["jupiter", "jup", "jlp"],
    "layerzero":   ["layerzero", "layer zero", "zro"],
    "arbitrum":    ["arbitrum", "arb token"],
    "optimism":    ["optimism", "op token", "superchain"],
    "base":        ["base chain", "base network", "base l2"],
    "eigenlayer":  ["eigenlayer", "eigen", "restaking", "avs"],
    "solana":      ["solana", "sol token"],
    "ethereum":    ["ethereum", "eth"],
    "bitcoin":     ["bitcoin", "btc"],
}


def _detect_project_from_text(text: str) -> Optional[str]:
    """Return the vault project slug if a known project is mentioned in text."""
    lower = text.lower()
    for slug, keywords in _PROJECT_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return slug
    return None


# ---------------------------------------------------------------------------
# Main learner run
# ---------------------------------------------------------------------------

def _get_active_topics() -> list[str]:
    """Get list of topics to research from active projects."""
    projects = _vault.list_projects()
    topics = []
    for p in projects:
        if p.get("blocked"):
            continue
        name = p.get("name", "")
        if name:
            topics.append(name)
    # Always include broad market topics
    topics.extend(["crypto", "defi", "airdrop", "hyperliquid", "solana", "ethereum"])
    return list(dict.fromkeys(topics))  # dedup while preserving order


def run_learning_cycle() -> dict:
    """
    Main entry point. Run a full learning cycle:
    1. Fetch Tier 1/2 events (hacks, raises, news)
    2. Verify and write confirmed events
    3. Fetch Tier 3 community signals
    4. Detect narrative trends
    5. Update project observations where relevant
    Returns summary dict.
    """
    log.info("Learner agent starting learning cycle")
    summary = {
        "confirmed_events": 0,
        "community_signals": 0,
        "projects_updated": 0,
        "narrative_trends": {},
        "errors": [],
    }

    topics = _get_active_topics()

    # --- Step 1: Tier 1 — DeFiLlama hacks ---
    claims = []
    try:
        hacks = _fetch_defillama_hacks()
        for hack in hacks:
            name = hack.get("name", "Unknown Protocol")
            amount = hack.get("amount", 0)
            claim_text = f"{name} was exploited for ${amount:,.0f}" if amount else f"{name} was exploited"
            claims.append(Claim(
                text=claim_text,
                source="https://defillama.com/hacks",
                related_project=name.lower().replace(" ", "-"),
            ))
        log.info("DeFiLlama: found %d recent hacks", len(hacks))
    except Exception as e:
        summary["errors"].append(f"DeFiLlama hacks: {e}")

    # --- Step 2: Tier 1 — DeFiLlama raises ---
    try:
        raises = _fetch_defillama_raises()
        for raise_ in raises:
            name = raise_.get("name", "Unknown")
            amount = raise_.get("amount", 0)
            lead = raise_.get("leadInvestors", [""])[0] if raise_.get("leadInvestors") else ""
            claim_text = f"{name} raised ${amount}M" + (f" led by {lead}" if lead else "")
            claims.append(Claim(
                text=claim_text,
                source="https://defillama.com/raises",
                related_project=name.lower().replace(" ", "-"),
            ))
        log.info("DeFiLlama: found %d recent raises", len(raises))
    except Exception as e:
        summary["errors"].append(f"DeFiLlama raises: {e}")

    # --- Step 3: Tier 2 — RSS news articles ---
    for feed_url in _TIER2_RSS_FEEDS:
        try:
            articles = _fetch_rss_articles(feed_url, max_items=5)
            for article in articles:
                claims.append(Claim(
                    text=article["title"],
                    source=article["link"] or feed_url,
                    related_project=_detect_project_from_text(article["title"]),
                ))
        except Exception as e:
            summary["errors"].append(f"RSS {feed_url}: {e}")

    # --- Step 4: Verify and store Tier 1/2 claims ---
    counts = process_and_store(claims)
    summary["confirmed_events"] = counts["confirmed"]

    # --- Step 5: Update project observations for confirmed hacks ---
    for claim in claims:
        result = verify(claim)
        if result.write_as == "fact" and claim.related_project:
            # Add observation to project file if it exists
            project_name = claim.related_project
            proj = _vault.read_project(project_name)
            if proj:
                added = _vault.add_observation(
                    project_name,
                    claim.text,
                    source=claim.source,
                )
                if added:
                    summary["projects_updated"] += 1

    # --- Step 6: Community signals (Tier 3) ---
    community_signals = []
    community_signals.extend(_fetch_reddit_signals(topics))
    community_signals.extend(_fetch_x_signals(topics))
    community_signals.extend(_fetch_telegram_signals(topics))

    # Write as unconfirmed signals
    signal_claims = [
        Claim(
            text=(s.get("text") or s.get("title") or "")[:300],
            source=s.get("source", "community"),
            related_project=s.get("topic"),
        )
        for s in community_signals
        if s.get("text") or s.get("title")
    ]
    signal_counts = process_and_store(signal_claims)
    summary["community_signals"] = signal_counts.get("unconfirmed", 0)

    # --- Step 7: Narrative trend detection ---
    all_signals = community_signals + [
        {"text": c.text} for c in claims
    ]
    trend_counts = _detect_narrative_trend(all_signals)
    # Only report narratives with meaningful signal
    summary["narrative_trends"] = {
        k: v for k, v in trend_counts.items() if v >= 2
    }

    log.info(
        "Learning cycle complete: %d confirmed events, %d community signals, "
        "%d projects updated, trends: %s",
        summary["confirmed_events"],
        summary["community_signals"],
        summary["projects_updated"],
        summary["narrative_trends"],
    )
    return summary


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [learner] %(levelname)s %(message)s",
    )
    result = run_learning_cycle()
    print(json.dumps(result, indent=2))
