"""
Scout Agent -- research specialist.

Given a task ("find the best item to post right now"), the Scout calls
whichever data sources it judges most useful, reasons about what it found,
and returns a ranked list of candidates with its reasoning attached.

The Scout does NOT decide what to post -- that's the Analyst's job.
It decides what to *look at*.
"""
from __future__ import annotations

import logging
from agents.base import ToolAgent
from bot.sources import defillama, rss, newsapi
from bot.sources.alpha import detect_all as detect_alpha_signals

log = logging.getLogger(__name__)


def _fetch_rss(max_age_hours: float = 8.0) -> list:
    # Merge cryptocurrency.cv (200+ sources) with direct RSS feeds, deduplicated.
    seen: set = set()
    merged = []
    for item in newsapi.fetch_news(max_age_hours=max_age_hours, limit=20):
        key = item.title.lower()[:80]
        if key not in seen:
            seen.add(key)
            merged.append(item)
    for item in rss.fetch_all(max_age_hours=max_age_hours):
        key = item.title.lower()[:80]
        if key not in seen:
            seen.add(key)
            merged.append(item)
    merged.sort(key=lambda i: i.age_hours)
    return [
        {"title": i.title, "source": i.source, "topic": i.topic,
         "age_h": round(i.age_hours, 2), "url": i.url, "kind": "rss"}
        for i in merged[:25]
    ]


def _fetch_raises(min_amount_m: float = 0.0) -> list:
    items = defillama.fetch_raises()
    out = []
    for i in items[:20]:
        if i.amount is not None and i.amount < min_amount_m:
            continue
        title = f"{i.name} raised ${i.amount:.0f}M" if i.amount else f"{i.name} raised (undisclosed)"
        out.append({
            "title": title, "name": i.name, "amount_m": i.amount,
            "round": i.round_name, "category": i.category, "topic": i.topic,
            "age_h": round(i.age_hours, 2), "url": i.url, "kind": "raise",
        })
    return out


def _fetch_tvl_movers(min_change_pct: float = 15.0) -> list:
    items = defillama.fetch_tvl_movers(min_change_pct=min_change_pct)
    return [
        {
            "title": f"{i.name} TVL {'up' if i.change_pct > 0 else 'down'} {abs(i.change_pct):.1f}%",
            "name": i.name, "change_pct": round(i.change_pct, 1),
            "tvl_usd": round(i.tvl_usd), "category": i.category,
            "topic": i.topic, "url": i.url, "kind": "tvl",
        }
        for i in items[:15]
    ]


def _detect_alpha() -> list:
    signals = detect_alpha_signals()
    return [
        {"title": s.title, "kind": s.kind, "source": s.source, "topic": s.topic,
         "urgency": s.urgency, "age_h": round(s.age_hours, 2), "url": s.url, "meta": s.meta}
        for s in signals[:10]
    ]


def _fetch_x_context(topic: str, max_posts: int = 8) -> dict:
    """
    Fetch what influential X accounts are saying about a topic right now.
    Uses twscrape (free, no API key) via X_SCRAPER_COOKIES env var.
    Falls back gracefully if unavailable.
    """
    try:
        from bot.sources.xcontext import fetch_topic_posts
        posts = fetch_topic_posts(topic, limit=max_posts)
        if not posts:
            return {"posts": [], "summary": f"No recent X posts found for '{topic}' (or scraper unavailable)."}
        return {"posts": posts, "summary": f"Found {len(posts)} recent X posts about '{topic}'."}
    except Exception as exc:
        log.warning("fetch_x_context failed for topic '%s': %s", topic, exc)
        return {"posts": [], "summary": f"X context fetch failed: {exc}"}


_FETCH_RSS_SCHEMA = {
    "name": "fetch_rss",
    "description": "Fetch recent crypto news from 200+ sources via cryptocurrency.cv plus direct RSS feeds (CoinDesk, The Defiant, The Block, Blockworks, DL News). Results are merged and deduplicated.",
    "input_schema": {
        "type": "object",
        "properties": {
            "max_age_hours": {"type": "number", "description": "Only return items newer than this. Default 8.0."}
        },
    },
}

_FETCH_RAISES_SCHEMA = {
    "name": "fetch_raises",
    "description": "Fetch recent funding rounds from DeFiLlama.",
    "input_schema": {
        "type": "object",
        "properties": {
            "min_amount_m": {"type": "number", "description": "Only return raises above this USD million amount. Default 0."}
        },
    },
}

_FETCH_TVL_SCHEMA = {
    "name": "fetch_tvl_movers",
    "description": "Fetch DeFi protocols with significant 24h TVL changes.",
    "input_schema": {
        "type": "object",
        "properties": {
            "min_change_pct": {"type": "number", "description": "Minimum absolute TVL change percentage. Default 15."}
        },
    },
}

_DETECT_ALPHA_SCHEMA = {
    "name": "detect_alpha",
    "description": "Run all alpha detectors: fresh RSS, new protocols, TVL spikes, large raises, GitHub releases, Hyperliquid funding rates, token unlocks. Returns urgency-ranked signals.",
    "input_schema": {"type": "object", "properties": {}},
}

_FETCH_X_CONTEXT_SCHEMA = {
    "name": "fetch_x_context",
    "description": "Fetch what people on crypto X are saying about a specific topic right now. Call this after identifying a top candidate. The writer uses the returned posts to craft a take that adds to the conversation rather than repeating what has been said.",
    "input_schema": {
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "Topic or project name to search for on X. E.g. 'hyperliquid', 'kaito airdrop'."},
            "max_posts": {"type": "integer", "description": "Max posts to return. Default 8."},
        },
        "required": ["topic"],
    },
}


class ScoutAgent(ToolAgent):

    SYSTEM = (
        "You are the Research Scout for a crypto commentary account (@Qwinahh) on X.\n\n"
        "Your job: find the best raw material for one post AND gather the X conversation\n"
        "context around that topic so the writer can add a genuinely informed take.\n\n"
        "Instructions:\n"
        "1. Call detect_alpha first -- urgency-3 signals take priority over everything else.\n"
        "2. Call fetch_rss, fetch_raises, fetch_tvl_movers as needed to fill out the picture.\n"
        "3. Once you have your top 1-2 candidates, call fetch_x_context with the relevant\n"
        "   project or topic keyword. This tells the writer what has already been said on X\n"
        "   so the post can add to the conversation, not repeat it.\n"
        "4. Evaluate freshness, relevance to DeFi/perps/airdrops/early protocols, specificity.\n"
        "5. Return raw JSON only (no markdown):\n\n"
        '{"candidates": [{"rank": 1, "title": "...", "source": "...", "kind": "rss|raise|tvl|alpha", '
        '"topic": "...", "age_hours": 0.0, "url": "...|null", "urgency": 3, '
        '"reasoning": "Why this is the best pick right now.", '
        '"x_conversation": "What X accounts are already saying, or empty string."}], '
        '"scout_note": "One sentence on overall signal quality right now."}\n\n'
        "Return at most 5 candidates, ranked best-first. Pure JSON -- no explanation outside the object."
    )

    TOOLS = {
        "fetch_rss":        (_fetch_rss,        _FETCH_RSS_SCHEMA),
        "fetch_raises":     (_fetch_raises,     _FETCH_RAISES_SCHEMA),
        "fetch_tvl_movers": (_fetch_tvl_movers, _FETCH_TVL_SCHEMA),
        "detect_alpha":     (_detect_alpha,     _DETECT_ALPHA_SCHEMA),
        "fetch_x_context":  (_fetch_x_context,  _FETCH_X_CONTEXT_SCHEMA),
    }
