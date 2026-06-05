"""
agents/inspiration_agent.py — Daily inspiration feed for @Qwinahh's personal account.

Runs every morning at 07:00 UTC. Collects high-engagement posts from the top
DeFi/perps/airdrop accounts and trending keyword searches, then writes two
Obsidian vault pages:

  data/vault/inspiration/trending.md
    — Today's top-performing posts with engagement counts, sorted by traction.
      Raw material: find a post that made you think, then write your own take.

  data/vault/inspiration/patterns.md
    — LLM analysis of what formats and topics are getting traction today.
      Use this to understand the conversation before joining it.

Both files are cross-linked and updated daily. Previous day is archived to
data/vault/inspiration/history/YYYY-MM-DD.md before overwriting.

Requires: X_SCRAPER_COOKIES (twscrape, free) + at least one LLM key.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import os
import tempfile
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_VAULT_DIR       = Path("data/vault/inspiration")
_TRENDING_FILE   = _VAULT_DIR / "trending.md"
_PATTERNS_FILE   = _VAULT_DIR / "patterns.md"
_HISTORY_DIR     = _VAULT_DIR / "history"

# Accounts to monitor — high-signal DeFi/perps/airdrop voices
_MONITOR_ACCOUNTS = [
    "DefiIgnas",
    "HsakaTrades",
    "Founderization",
    "zkDrops",
    "Pentosh1",
    "0xMaki",
    "0xHamz",
    "CroissantEth",
    "SmolRefund",
    "0xSisyphus",
    "Route2FI",
    "thedefiedge",
    "Gainzy222",
    "tayvano_",
    "deFIYIelded",
]

# Keyword searches for trending posts outside the watchlist
_TRENDING_QUERIES = [
    "hyperliquid perp lang:en min_faves:30",
    "defi airdrop points lang:en min_faves:20",
    "kaito yap lang:en min_faves:20",
    "defillama tvl lang:en min_faves:25",
    "perp dex on-chain lang:en min_faves:30",
    "solana defi yield lang:en min_faves:20",
    "crypto airdrop snapshot lang:en min_faves:15",
    "ethereum restaking AVS lang:en min_faves:20",
]

# How far back to look (hours)
_LOOKBACK_HOURS = 26   # slightly more than 24 so we never miss the overnight window

# Min engagement to include in the feed
_MIN_LIKES_ACCOUNT = 10    # targeted account posts
_MIN_LIKES_KEYWORD = 15    # keyword search posts

# Max posts per account to fetch
_POSTS_PER_ACCOUNT = 8

# Top N posts to include in trending.md
_TOP_POSTS_COUNT = 20


# ---------------------------------------------------------------------------
# twscrape helpers
# ---------------------------------------------------------------------------

def _get_cookies() -> Optional[str]:
    return os.environ.get("X_SCRAPER_COOKIES", "").strip() or None


async def _make_api():
    try:
        from twscrape import API
    except ImportError:
        return None
    cookies = _get_cookies()
    if not cookies:
        return None
    api = API(os.path.join(tempfile.gettempdir(), "twscrape_pool.db"))
    try:
        await api.pool.add_account(
            username="beacon_inspiration_scraper",
            password="placeholder",
            email="placeholder@placeholder.com",
            email_password="placeholder",
            cookies=cookies,
        )
    except Exception as exc:
        log.warning("inspiration_agent twscrape setup: %s", exc)
        return None
    return api


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result(timeout=120)
        else:
            return loop.run_until_complete(coro)
    except Exception as exc:
        log.warning("inspiration_agent async runner: %s", exc)
        return None


def _age_hours(tweet_date) -> float:
    if not tweet_date:
        return 999.0
    try:
        return (time.time() - tweet_date.timestamp()) / 3600.0
    except Exception:
        return 999.0


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

async def _collect_async() -> list[dict]:
    """Collect high-engagement posts from monitored accounts + keyword searches."""
    api = await _make_api()
    if not api:
        log.warning("inspiration_agent: twscrape unavailable (no cookies or not installed).")
        return []

    posts: list[dict] = []
    seen_ids: set[str] = set()

    # --- Monitored accounts ---
    for username in _MONITOR_ACCOUNTS:
        try:
            user = await api.user_by_login(username)
            if not user:
                continue
            async for tweet in api.user_tweets(user.id, limit=_POSTS_PER_ACCOUNT):
                tid = str(tweet.id)
                if tid in seen_ids:
                    continue
                if _age_hours(getattr(tweet, "date", None)) > _LOOKBACK_HOURS:
                    continue
                if tweet.rawContent and tweet.rawContent.startswith("RT @"):
                    continue
                likes = getattr(tweet, "likeCount", 0) or 0
                if likes < _MIN_LIKES_ACCOUNT:
                    continue
                seen_ids.add(tid)
                posts.append(_tweet_to_dict(tweet, source=f"@{username}", source_type="account"))
        except Exception as exc:
            log.debug("inspiration_agent: error fetching @%s: %s", username, exc)

    # --- Keyword searches ---
    for query in _TRENDING_QUERIES:
        try:
            async for tweet in api.search(
                f"{query} -is:retweet",
                limit=15,
                kv={"product": "Latest"},
            ):
                tid = str(tweet.id)
                if tid in seen_ids:
                    continue
                if _age_hours(getattr(tweet, "date", None)) > _LOOKBACK_HOURS:
                    continue
                likes = getattr(tweet, "likeCount", 0) or 0
                if likes < _MIN_LIKES_KEYWORD:
                    continue
                seen_ids.add(tid)
                author = tweet.user.username if tweet.user else "unknown"
                posts.append(_tweet_to_dict(tweet, source=f"@{author}", source_type="keyword"))
        except Exception as exc:
            log.debug("inspiration_agent: keyword search error '%s': %s", query[:40], exc)

    log.info("inspiration_agent: collected %d raw posts.", len(posts))
    return posts


def _tweet_to_dict(tweet, source: str, source_type: str) -> dict:
    likes    = getattr(tweet, "likeCount",    0) or 0
    replies  = getattr(tweet, "replyCount",   0) or 0
    retweets = getattr(tweet, "retweetCount", 0) or 0
    quotes   = getattr(tweet, "quoteCount",   0) or 0
    followers = (getattr(tweet.user, "followersCount", 0) or 0) if tweet.user else 0
    dt = getattr(tweet, "date", None)
    posted_str = dt.strftime("%H:%M UTC") if dt else "?"
    return {
        "id":          str(tweet.id),
        "text":        (tweet.rawContent or "").strip(),
        "source":      source,
        "source_type": source_type,
        "followers":   followers,
        "likes":       likes,
        "replies":     replies,
        "retweets":    retweets,
        "quotes":      quotes,
        "engagement":  likes + replies * 3 + retweets * 2 + quotes * 2,
        "posted_at":   posted_str,
        "url":         f"https://x.com/{source.lstrip('@')}/status/{tweet.id}",
    }


# ---------------------------------------------------------------------------
# Pattern analysis via LLM
# ---------------------------------------------------------------------------

def _analyse_patterns(posts: list[dict]) -> str:
    """Use the LLM to synthesise what formats and topics are getting traction."""
    if not posts:
        return "_No posts collected — check X_SCRAPER_COOKIES is set._"

    top = sorted(posts, key=lambda p: p["engagement"], reverse=True)[:15]

    post_block = "\n\n".join(
        f"[{p['source']} | likes:{p['likes']} replies:{p['replies']} rts:{p['retweets']}]\n{p['text'][:280]}"
        for p in top
    )

    prompt = f"""You are analysing high-performing crypto X posts from the last 24 hours.
Below are the top posts by engagement. Identify:
1. **What topics are getting traction** — specific narratives, protocols, events
2. **What formats are working** — data dumps, contrarian takes, questions, thread openers, callouts
3. **Voice patterns** — what makes these posts land (specific numbers, strong opinions, insider knowledge)
4. **3 content angles** for @Qwinahh to post about today based on these trends

Posts:

{post_block}

Write a concise editorial brief (under 400 words). Use markdown headers. Be specific — name protocols, quote numbers, identify the actual narrative. No generic advice."""

    try:
        from bot.brain.llm import complete as llm_complete
        result = llm_complete(
            system="You are a crypto content strategist. Be specific and concise.",
            user=prompt,
            max_tokens=500,
            temperature=0.6,
        )
        return result.strip() if result else "_LLM analysis unavailable._"
    except Exception as exc:
        log.warning("inspiration_agent LLM analysis failed: %s", exc)
        return "_LLM analysis unavailable._"


# ---------------------------------------------------------------------------
# Vault writers
# ---------------------------------------------------------------------------

def _format_trending_md(posts: list[dict], today: str, analysis: str) -> str:
    top = sorted(posts, key=lambda p: p["engagement"], reverse=True)[:_TOP_POSTS_COUNT]

    lines = [
        f"---",
        f"title: Trending — {today}",
        f"updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"type: inspiration",
        f"---",
        f"",
        f"# Trending Today — {today}",
        f"",
        f"Top-performing posts from monitored accounts + keyword searches in the last 24h.",
        f"Use these as raw material — find a post that made you think, then write your own take.",
        f"",
        f"[[patterns|→ What's Working Today]] | [[../dashboard|← Dashboard]]",
        f"",
        f"---",
        f"",
        f"## Top Posts by Engagement",
        f"",
    ]

    for i, p in enumerate(top, 1):
        eng_bar = "🔥" * min(int(p["engagement"] / 50), 5) or "·"
        lines += [
            f"### {i}. {p['source']} · {p['posted_at']}",
            f"",
            f"> {p['text'][:300]}{'...' if len(p['text']) > 300 else ''}",
            f"",
            f"**Likes:** {p['likes']} · **Replies:** {p['replies']} · **RTs:** {p['retweets']} · **Quotes:** {p['quotes']} {eng_bar}",
            f"[View post]({p['url']})",
            f"",
        ]

    lines += [
        f"---",
        f"",
        f"## Today's Pattern Analysis",
        f"",
        analysis,
        f"",
        f"---",
        f"",
        f"_Updated daily at ~07:00 UTC by the inspiration agent. Archive: [[history/{today}]]_",
    ]

    return "\n".join(lines)


def _format_patterns_md(posts: list[dict], today: str, analysis: str) -> str:
    # Topic frequency
    from collections import Counter
    import re

    focus_topics = [
        "hyperliquid", "kaito", "meteora", "airdrop", "points", "perp",
        "defi", "restaking", "eigenlayer", "solana", "arbitrum", "base",
        "tvl", "yield", "funding rate", "listing", "tge", "raise",
    ]
    text_blob = " ".join(p["text"].lower() for p in posts)
    topic_counts = Counter(t for t in focus_topics if t in text_blob)
    top_topics = topic_counts.most_common(8)

    # Format frequency (heuristic)
    format_counts = Counter()
    for p in posts:
        t = p["text"]
        if "?" in t:
            format_counts["question"] += 1
        if any(c.isdigit() for c in t) and ("%" in t or "$" in t or "M" in t or "B" in t):
            format_counts["data_observation"] += 1
        if any(w in t.lower() for w in ["but", "however", "actually", "wrong", "not"]):
            format_counts["contrarian"] += 1
        if t.endswith(":") or t.count("\n") >= 2:
            format_counts["thread_hook"] += 1

    lines = [
        f"---",
        f"title: What's Working — {today}",
        f"updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"type: inspiration",
        f"---",
        f"",
        f"# What's Working Today — {today}",
        f"",
        f"Pattern analysis across {len(posts)} high-engagement posts from the last 24h.",
        f"",
        f"[[trending|→ Today's Top Posts]] | [[../dashboard|← Dashboard]]",
        f"",
        f"---",
        f"",
        f"## Trending Topics",
        f"",
    ]

    if top_topics:
        for topic, count in top_topics:
            bar = "█" * min(count, 10)
            lines.append(f"- **{topic}** {bar} ({count} posts)")
    else:
        lines.append("_No clear topic clusters today._")

    lines += [
        f"",
        f"## Format Breakdown",
        f"",
    ]

    if format_counts:
        for fmt, count in format_counts.most_common():
            lines.append(f"- **{fmt}**: {count} posts")
    else:
        lines.append("_Insufficient data for format analysis._")

    lines += [
        f"",
        f"## Editorial Analysis",
        f"",
        analysis,
        f"",
        f"---",
        f"",
        f"## Top Accounts Active Today",
        f"",
    ]

    from collections import Counter as C2
    account_counts = C2(p["source"] for p in posts)
    for acct, cnt in account_counts.most_common(10):
        lines.append(f"- {acct} ({cnt} qualifying posts)")

    lines += [
        f"",
        f"---",
        f"_Updated daily at ~07:00 UTC. Archive: [[history/{today}]]_",
    ]

    return "\n".join(lines)


def _archive_existing(today: str) -> None:
    """Move yesterday's trending.md to history/ before overwriting."""
    _HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    if _TRENDING_FILE.exists():
        archive = _HISTORY_DIR / f"{today}.md"
        if not archive.exists():
            try:
                archive.write_text(_TRENDING_FILE.read_text(encoding="utf-8"), encoding="utf-8")
            except Exception as exc:
                log.debug("inspiration_agent archive failed: %s", exc)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run() -> None:
    """
    Run the inspiration agent. Called by inspiration.yml daily at 07:00 UTC.
    Fails gracefully — vault pages get a minimal stub if anything goes wrong.
    """
    today = date.today().isoformat()
    _VAULT_DIR.mkdir(parents=True, exist_ok=True)

    log.info("inspiration_agent: collecting posts for %s", today)

    posts = _run_async(_collect_async()) or []

    if posts:
        log.info("inspiration_agent: %d posts collected, running analysis.", len(posts))
        analysis = _analyse_patterns(posts)
    else:
        analysis = "_No posts collected — X_SCRAPER_COOKIES may not be set or twscrape is unavailable._"
        log.warning("inspiration_agent: no posts collected.")

    _archive_existing(today)

    trending_md = _format_trending_md(posts, today, analysis)
    patterns_md = _format_patterns_md(posts, today, analysis)

    _TRENDING_FILE.write_text(trending_md, encoding="utf-8")
    _PATTERNS_FILE.write_text(patterns_md, encoding="utf-8")

    log.info(
        "inspiration_agent: wrote trending.md (%d posts) and patterns.md.",
        len(posts),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
