"""
bot/sources/coingecko.py — CoinGecko market data

Source: CoinGecko (https://www.coingecko.com/en/api)
API: api.coingecko.com/api/v3/ (public endpoints, no key needed)
Cost: FREE for basic endpoints. No key required for /trending, /global,
      /simple/price. Rate limit: ~30 calls/min on free tier.

WHY THIS MATTERS:
  - /coins/trending → what's getting attention RIGHT NOW on CoinGecko
    (proxy for what retail is searching). Bot can avoid posting about
    yesterday's news and instead comment on things already trending.
  - /global → BTC dominance, total market cap, 24h change. Gives macro
    context: "BTC dominance is at 58% — alt season hasn't started yet"
  - /simple/price → get current prices + 24h/7d change for any token.
    Lets the bot anchor posts to real numbers.
  - /coins/{id}/market_chart → historical prices for pattern posts.

All data is Tier 2 (established data source) — can be cited as fact.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
import urllib.parse
from typing import Optional

log = logging.getLogger(__name__)

_BASE = "https://api.coingecko.com/api/v3"
_CACHE: dict[str, tuple[float, any]] = {}
_TTL = {
    "trending": 1800,    # 30 min — trending changes slowly
    "global": 600,       # 10 min — market caps update faster
    "price": 300,        # 5 min — prices are real-time
}


def _get(path: str, params: Optional[dict] = None, cache_key: Optional[str] = None, ttl: int = 600) -> Optional[dict]:
    """Internal GET with caching."""
    key = cache_key or path
    now = time.time()
    if key in _CACHE and now - _CACHE[key][0] < ttl:
        return _CACHE[key][1]

    url = f"{_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "beacon-bot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        _CACHE[key] = (now, data)
        return data
    except Exception as e:
        log.warning("CoinGecko fetch failed for %s: %s", path, e)
        return None


# ---------------------------------------------------------------------------
# Trending coins
# ---------------------------------------------------------------------------

def get_trending() -> list[dict]:
    """
    Get top 7 trending coins on CoinGecko right now.
    Returns list of {name, symbol, rank, price_btc}.
    Updated every 10-15 min by CoinGecko.
    """
    data = _get("/search/trending", cache_key="trending", ttl=_TTL["trending"])
    if not data:
        return []
    coins = data.get("coins", [])
    return [
        {
            "name": c["item"]["name"],
            "symbol": c["item"]["symbol"].upper(),
            "rank": c["item"]["market_cap_rank"],
            "score": c["item"].get("score", 0),
        }
        for c in coins[:7]
    ]


def format_trending_context() -> str:
    """One-line context: what's trending on CoinGecko right now."""
    trending = get_trending()
    if not trending:
        return ""
    symbols = [f"{c['symbol']}" for c in trending[:5]]
    return f"Trending on CoinGecko right now: {', '.join(symbols)}"


# ---------------------------------------------------------------------------
# Global market data
# ---------------------------------------------------------------------------

def get_global() -> Optional[dict]:
    """
    Get global crypto market data.
    Returns dict with: total_market_cap_usd, btc_dominance, eth_dominance,
    market_cap_change_24h_pct, active_cryptocurrencies.
    """
    data = _get("/global", cache_key="global", ttl=_TTL["global"])
    if not data:
        return None
    d = data.get("data", {})
    return {
        "total_market_cap_usd": d.get("total_market_cap", {}).get("usd", 0),
        "btc_dominance": round(d.get("market_cap_percentage", {}).get("btc", 0), 1),
        "eth_dominance": round(d.get("market_cap_percentage", {}).get("eth", 0), 1),
        "market_cap_change_24h_pct": round(d.get("market_cap_change_percentage_24h_usd", 0), 2),
        "active_cryptocurrencies": d.get("active_cryptocurrencies", 0),
    }


def format_global_context() -> str:
    """Build market macro context string for writer injection."""
    g = get_global()
    if not g:
        return ""

    mcap = g["total_market_cap_usd"]
    mcap_str = f"${mcap/1e12:.2f}T" if mcap > 1e12 else f"${mcap/1e9:.0f}B"
    change = g["market_cap_change_24h_pct"]
    change_str = f"+{change}%" if change > 0 else f"{change}%"

    btc_dom = g["btc_dominance"]
    # Contextual note on BTC dominance
    dom_note = ""
    if btc_dom > 58:
        dom_note = " (alts haven't moved yet)"
    elif btc_dom < 48:
        dom_note = " (alt season territory)"

    return (
        f"Crypto market: {mcap_str} total cap ({change_str} 24h). "
        f"BTC dominance: {btc_dom}%{dom_note}. "
        f"ETH dominance: {g['eth_dominance']}%."
    )


# ---------------------------------------------------------------------------
# Token prices
# ---------------------------------------------------------------------------

# Map common names/tickers to CoinGecko IDs
_COIN_ID_MAP = {
    "btc": "bitcoin", "bitcoin": "bitcoin",
    "eth": "ethereum", "ethereum": "ethereum",
    "sol": "solana", "solana": "solana",
    "arb": "arbitrum", "arbitrum": "arbitrum",
    "op": "optimism", "optimism": "optimism",
    "hype": "hyperliquid", "hyperliquid": "hyperliquid",
    "jup": "jupiter-exchange-solana", "jupiter": "jupiter-exchange-solana",
    "eigen": "eigenlayer", "eigenlayer": "eigenlayer",
    "kaito": "kaito", "meteora": "meteora-ag",
    "uni": "uniswap", "uniswap": "uniswap",
    "aave": "aave",
    "gmx": "gmx",
    "ondo": "ondo-finance",
    "tao": "bittensor", "bittensor": "bittensor",
}


def get_price(coin: str) -> Optional[dict]:
    """
    Get price + 24h/7d change for a coin.
    Returns dict with: usd, usd_24h_change, usd_7d_change.
    coin: ticker symbol or name (e.g. "eth", "hyperliquid")
    """
    coin_id = _COIN_ID_MAP.get(coin.lower(), coin.lower())
    data = _get(
        "/simple/price",
        params={
            "ids": coin_id,
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_7d_change": "true",
        },
        cache_key=f"price_{coin_id}",
        ttl=_TTL["price"],
    )
    if not data or coin_id not in data:
        return None
    d = data[coin_id]
    return {
        "usd": d.get("usd", 0),
        "change_24h": round(d.get("usd_24h_change", 0), 2),
        "change_7d": round(d.get("usd_7d_change", 0), 2),
    }


def format_price_context(coins: list[str]) -> str:
    """
    Build a price context string for a list of coins.
    E.g. "ETH: $3,240 (+4.2% 24h, +18.1% 7d). SOL: $185 (-1.3% 24h)."
    """
    parts = []
    for coin in coins[:5]:
        p = get_price(coin)
        if not p:
            continue
        price_str = f"${p['usd']:,.0f}" if p["usd"] > 1 else f"${p['usd']:.4f}"
        c24 = f"+{p['change_24h']}%" if p["change_24h"] > 0 else f"{p['change_24h']}%"
        c7 = f"+{p['change_7d']}%" if p["change_7d"] > 0 else f"{p['change_7d']}%"
        parts.append(f"{coin.upper()}: {price_str} ({c24} 24h, {c7} 7d)")
    return ". ".join(parts) + "." if parts else ""


# ---------------------------------------------------------------------------
# Combined context builder
# ---------------------------------------------------------------------------

def build_market_context(topic_coins: Optional[list[str]] = None) -> str:
    """
    Build full market context block for writer injection.
    Includes: global macro, trending coins, and prices for topic-relevant coins.
    """
    parts = []

    global_ctx = format_global_context()
    if global_ctx:
        parts.append(global_ctx)

    trending_ctx = format_trending_context()
    if trending_ctx:
        parts.append(trending_ctx)

    if topic_coins:
        price_ctx = format_price_context(topic_coins)
        if price_ctx:
            parts.append(price_ctx)

    return "\n".join(parts)
