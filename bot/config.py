"""
Central configuration for the bot.
All tuneable constants live here — never scatter magic numbers across modules.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Final


# ---------------------------------------------------------------------------
# Posting cadence
# ---------------------------------------------------------------------------

# 6 posts per day — matches what top CT accounts actually do.
# Research across HsakaTrades, DefiIgnas, Pentosh1 and similar: they post 5-8x/day.
# X's algorithm punishes inactivity: one inactive day drops per-post views from
# 5-10k down to <1k. Frequency AND quality both matter — this is not either/or.
# Quality gates (authenticity judge, reject phrases, score threshold) handle quality.
# Frequency handles distribution.
#
# Mix: 2 filler/quick-takes early in the day, 2 value posts mid-day,
# 2 bangers in US prime time. The last post works while you sleep.
MAX_POSTS_PER_DAY: Final[int] = 6
MIN_HOURS_BETWEEN_POSTS: Final[float] = 1.5  # Posts every ~2h during active windows.

# UTC hour ranges during which posting is allowed.
# Covers the full active crypto window: EU morning through US late evening.
# Posts spread across 5 cron triggers (see post.yml) so distribution is even.
POSTING_WINDOWS: Final[list[tuple[int, int]]] = [
    (8, 23),    # Wide window — individual post timing handled by cron schedule
]

# Random jitter added to posting time so the schedule never looks mechanical.
POST_JITTER_SECONDS: Final[int] = 900  # ±15 min

# Probability that a normal (non-alpha) cycle attempts a 3-5 tweet thread
# instead of a single post. Falls through to freeform/normal pipeline on
# any failure, so this never blocks a posting cycle.
THREAD_CHANCE: Final[float] = 0.15


# ---------------------------------------------------------------------------
# Content quality gate
# ---------------------------------------------------------------------------

# Items scoring below this are not posted.
# Lowered to 58 during warm-up — quality gates in writer.py still apply.
# Raise back to 62+ once the account has consistent daily engagement.
POST_SCORE_THRESHOLD: Final[int] = 58

# How many recent topics to track for variety enforcement.
TOPIC_MEMORY_SIZE: Final[int] = 30

# Max times the same topic may appear in recent history before being skipped.
MAX_TOPIC_REPEAT: Final[int] = 2

# How many post fingerprints to retain for deduplication.
FINGERPRINT_MEMORY_SIZE: Final[int] = 500


# ---------------------------------------------------------------------------
# Focus keywords — items containing these score higher
# ---------------------------------------------------------------------------

FOCUS_KEYWORDS: Final[list[str]] = [
    "hyperliquid", "hype", "meteora", "lighter",
    "perp", "perps", "dex", "defi", "points", "airdrop",
    "leaderboard", "tge", "listing", "raise", "funding",
    "seed", "series a", "series b", "launch", "incentives",
    "jupiter", "dtf", "agent", "virtual", "virtuals",
    "layerzero", "stargate", "arbitrum", "optimism", "base",
    "kaito studio",
]

# Phrases that signal low-quality clickbait — items containing these score lower.
JUNK_PHRASES: Final[list[str]] = [
    "price prediction", "could reach", "might hit", "analyst says",
    "could explode", "will surge", "set to boom", "moon soon",
    "experts predict", "top 5 reasons", "you need to know",
]


def scrub_voice(text: str) -> str:
    """Strip the single most-cited deterministic AI tell: the em/en dash used as a
    connector. Real posts use a comma or a period, not "—". Word-level tells
    (delve, leverage, TVL over-use, etc.) are handled by the persona and the
    authenticity judge, not here, to avoid mangling sentences."""
    if not text:
        return text
    for dash in ("—", "–"):  # em dash, en dash
        text = text.replace(f" {dash} ", ", ").replace(dash, ", ")
    text = text.replace("  ", " ").replace(" ,", ",").replace(" .", ".")
    return text.strip()


# ---------------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------------

RSS_FEEDS: Final[list[tuple[str, str]]] = [
    # Existing sources
    ("CoinDesk",         "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml"),
    ("The Defiant",      "https://thedefiant.io/feed/"),
    ("The Block",        "https://www.theblock.co/rss.xml"),
    ("Blockworks",       "https://blockworks.co/feed"),
    ("DL News",          "https://www.dlnews.com/feed/"),

    # DeFi-specific — lower noise, higher signal (validated 2026-06-05)
    ("Decrypt",          "https://decrypt.co/feed"),
    ("Protos",           "https://protos.com/feed/"),
    ("CoinTelegraph",    "https://cointelegraph.com/rss"),

    # Protocol blogs — direct from source (validated 2026-06-05)
    ("Hyperliquid Blog", "https://hyperliquid.substack.com/feed"),
    ("DefiLlama Blog",   "https://defillama.substack.com/feed"),
]

DEFILLAMA_PROTOCOLS_URL: Final[str] = "https://api.llama.fi/protocols"
DEFILLAMA_RAISES_URL:    Final[str] = "https://defillama.com/raises/download.json"

COINGECKO_PRICE_URL: Final[str] = "https://api.coingecko.com/api/v3/simple/price"
COINGECKO_IDS: Final[dict[str, str]] = {
    "bitcoin":  "BTC",
    "ethereum": "ETH",
    "solana":   "SOL",
}

# Maximum age of an RSS item before it is ignored.
RSS_MAX_AGE_HOURS: Final[float] = 8.0

# Items fetched per feed per run.
RSS_ITEMS_PER_FEED: Final[int] = 15

# Items fetched from DeFiLlama raises endpoint.
RAISES_FETCH_LIMIT: Final[int] = 40

# Minimum 24h TVL change (%) to include a TVL mover.
TVL_MIN_CHANGE_PCT: Final[float] = 12.0


# ---------------------------------------------------------------------------
# AI writer
# ---------------------------------------------------------------------------

# Model used for tweet generation. Haiku is fast and cheap; upgrade if needed.
CLAUDE_MODEL: Final[str] = "claude-haiku-4-5-20251001"

# Maximum tokens for a generated tweet.
# 400 gives headroom for the REASON: line + tweet text without truncation.
CLAUDE_MAX_TOKENS: Final[int] = 400

# Whether to fall back to template writing when the Claude API is unavailable.
TEMPLATE_FALLBACK: Final[bool] = True


# ---------------------------------------------------------------------------
# Image generation (agents/image_agent.py)
# ---------------------------------------------------------------------------

# Replicate API token. Image generation is entirely optional — when the
# token is missing the image agent disables itself and posting continues
# text-only. Model: black-forest-labs/flux-schnell ($0.003/image).
REPLICATE_API_TOKEN: Final[str] = os.getenv("REPLICATE_API_TOKEN", "")
IMAGE_GENERATION_ENABLED: Final[bool] = bool(REPLICATE_API_TOKEN)

# Probability that an image-eligible post attempts image generation.
# Text posts slightly out-engage images on median (Buffer 18M-post data,
# see data/vault/knowledge/image-strategy.md) — images are an accent,
# not a default.
IMAGE_CHANCE: Final[float] = 0.35


# ---------------------------------------------------------------------------
# X account identity
# ---------------------------------------------------------------------------

# The bot's own X handle. Used to resolve its own user ID for mentions,
# self-filtering in replies, and post-reply fetches.
BOT_USERNAME: Final[str] = "Qwinahh"

# Minimum hours between quote-tweets (engagement farming, see engage.py).
QUOTE_TWEET_COOLDOWN_HOURS: Final[float] = 6.0


# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------

STATE_PATH:     Final[str] = "data/state.json"
PORTFOLIO_PATH: Final[str] = "data/portfolio.json"
WATCHLIST_PATH: Final[str] = "data/watchlist.json"
PERSONA_PATH:   Final[str] = "data/persona.md"

# Performance tracking (agents/performance_tracker.py)
POST_LOG_PATH:            Final[str] = "data/performance/post_log.json"
PERFORMANCE_LOG_MD_PATH:  Final[str] = "data/vault/knowledge/performance-log.md"

# Weekly suggestion reports (agents/suggestion_agent.py)
SUGGESTIONS_DIR: Final[str] = "data/suggestions"

# Vault persona file read by writer + reply generation
VAULT_PERSONA_PATH: Final[str] = "data/vault/persona.md"


# ---------------------------------------------------------------------------
# Environment variable names (never hardcode secrets)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EnvKeys:
    x_api_key:        str = "X_API_KEY"
    x_api_secret:     str = "X_API_SECRET"
    x_access_token:   str = "X_ACCESS_TOKEN"
    x_access_secret:  str = "X_ACCESS_SECRET"
    anthropic_api_key: str = "ANTHROPIC_API_KEY"


ENV: Final[EnvKeys] = EnvKeys()


def require_env(key: str) -> str:
    """Return an environment variable or raise a descriptive error."""
    value = os.environ.get(key)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            "Add it to GitHub Secrets or your local .env file."
        )
    return value
