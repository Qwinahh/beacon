"""
CoinGecko price context.

Fetches current prices and 24h changes for BTC, ETH, SOL.
Free public API — no key required (rate-limited to ~30 req/min).
Injected into every post cycle.
"""
from __future__ import annotations

import logging

import requests

from bot.config import COINGECKO_IDS, COINGECKO_PRICE_URL

log = logging.getLogger(__name__)

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "CryptoBot/2.0"})


def fetch_prices() -> dict[str, dict]:
    """Return {coin_id: {price, change_24h, ticker}} for configured coins."""
    out: dict[str, dict] = {}
    try:
        ids = ",".join(COINGECKO_IDS.keys())
        resp = _SESSION.get(
            COINGECKO_PRICE_URL,
            params={
                "ids":                 ids,
                "vs_currencies":       "usd",
                "include_24hr_change": "true",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        for coin_id, ticker in COINGECKO_IDS.items():
            entry  = data.get(coin_id, {})
            price  = entry.get("usd")
            change = entry.get("usd_24h_change")
            if price is not None:
                out[coin_id] = {
                    "price":      price,
                    "change_24h": round(change, 2) if change is not None else None,
                    "ticker":     ticker,
                }
    except Exception as exc:
        log.warning("CoinGecko fetch failed: %s", exc)
    return out


def prices_summary() -> str:
    """Return a compact price line for context injection."""
    prices = fetch_prices()
    if not prices:
        return ""
    parts = []
    for _, d in prices.items():
        chg     = d.get("change_24h")
        chg_str = f" ({'+' if chg >= 0 else ''}{chg:.1f}%)" if chg is not None else ""
        parts.append(f"{d['ticker']} ${d['price']:,.0f}{chg_str}")
    return "Prices: " + " | ".join(parts)
