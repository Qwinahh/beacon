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

# 3 quality posts per day. This isn't arbitrary:
# - Each post competes for feed space against all your other posts
# - The algorithm gives higher per-post distribution to accounts with high
#   engagement rates, not high volume. 3 posts at 5% eng rate beats 8 at 1%.
# - Audience fatigue: followers who see 5+ posts/day from one account start
#   muting. You need every post to feel worth reading.
MAX_POSTS_PER_DAY: Final[int] = 3
MIN_HOURS_BETWEEN_POSTS: Final[float] = 4.0  # Forces genuine content variety.

# UTC hour ranges during which posting is allowed (start_inclusive, end_exclusive).
# Two peak windows: US morning overlap (highest global audience) + US evening.
# Removed Asia window for now — audience is primarily EN-speaking DeFi traders.
POSTING_WINDOWS: Final[list[tuple[int, int]]] = [
    (13, 16),   # US morning / EU afternoon — highest engagement window globally
    (19, 22),   # US prime time — second best window
]

# Random jitter added to posting time so the schedule never looks mechanical.
POST_JITTER_SECONDS: Final[int] = 900  # ±15 min


# ---------------------------------------------------------------------------
# Content quality gate
# ---------------------------------------------------------------------------

# Items scoring below this are not posted.
POST_SCORE_THRESHOLD: Final[int] = 62

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
    "hyperliquid", "hype", "kaito", "meteora", "lighter",
    "perp", "perps", "dex", "defi", "points", "airdrop",
    "leaderboard", "tge", "listing", "raise", "funding",
    "seed", "series a", "series b", "launch", "incentives",
    "jupiter", "dtf", "agent", "virtual", "virtuals",
    "layerzero", "stargate", "arbitrum", "optimism", "base",
]

# Phrases that signal low-quality clickbait — items containing these score lower.
JUNK_PHRASES: Final[list[str]] = [
    "price prediction", "could reach", "might hit", "analyst says",
    "could explode", "will surge", "set to boom", "moon soon",
    "experts predict", "top 5 reasons", "you need to know",
]


# ---------------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------------

RSS_FEEDS: Final[list[tuple[str, str]]] = [
    ("CoinDesk",    "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml"),
    ("The Defiant", "https://thedefiant.io/feed/"),
    ("The Block",   "https://www.theblock.co/rss.xml"),
    ("Blockworks",  "https://blockworks.co/feed"),
    ("DL News",     "https://www.dlnews.com/feed/"),
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
CLAUDE_MAX_TOKENS: Final[int] = 300

# Whether to fall back to template writing when the Claude API is unavailable.
TEMPLATE_FALLBACK: Final[bool] = True


# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------

STATE_PATH:     Final[str] = "data/state.json"
PORTFOLIO_PATH: Final[str] = "data/portfolio.json"
WATCHLIST_PATH: Final[str] = "data/watchlist.json"
PERSONA_PATH:   Final[str] = "data/persona.md"


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
