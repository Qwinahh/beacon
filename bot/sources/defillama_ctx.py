"""
DeFiLlama macro context.

Fetches total cross-chain DeFi TVL for macro context injection.
Distinct from defillama.py which tracks per-protocol raises and movers.
"""
from __future__ import annotations

import logging
from typing import Optional

import requests

log = logging.getLogger(__name__)

_TVL_URL = "https://api.llama.fi/v2/historicalChainTvl"
_SESSION  = requests.Session()
_SESSION.headers.update({"User-Agent": "CryptoBot/2.0"})


def fetch_total_tvl() -> Optional[dict]:
    """Return current and 7d-delta total DeFi TVL."""
    try:
        resp = _SESSION.get(_TVL_URL, timeout=12)
        resp.raise_for_status()
        history = resp.json()
        if not history or not isinstance(history, list):
            return None
        current  = history[-1]["tvl"]
        prev_7d  = history[-8]["tvl"] if len(history) >= 8 else None
        change_7d = ((current - prev_7d) / prev_7d * 100) if prev_7d else None
        return {
            "tvl_usd":       current,
            "change_7d_pct": round(change_7d, 1) if change_7d is not None else None,
        }
    except Exception as exc:
        log.warning("DeFiLlama total TVL fetch failed: %s", exc)
        return None


def tvl_summary() -> str:
    """Return compact TVL line for context injection."""
    data = fetch_total_tvl()
    if not data:
        return ""
    tvl_b   = data["tvl_usd"] / 1e9
    chg     = data.get("change_7d_pct")
    chg_str = f" ({'+' if chg >= 0 else ''}{chg:.1f}% 7d)" if chg is not None else ""
    return f"Total DeFi TVL: ${tvl_b:.1f}B{chg_str}"
