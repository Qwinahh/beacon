"""
bot/sources/defillama_ctx.py — DeFiLlama extended context

Supplements the existing defillama.py (which handles raises + TVL movers as
candidate items for the scout). This module provides:

  - Per-protocol TVL with 7d/30d change (for researcher context)
  - Total DeFi TVL macro context
  - Top yield opportunities (real yield, not subsidised)
  - 7-day TVL movers for writer context injection

All data: Tier 1 (on-chain aggregated). Write to vault as confirmed fact.
Cost: Free, no API key. Source: api.llama.fi
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from typing import Optional

log = logging.getLogger(__name__)

_BASE = "https://api.llama.fi"
_CACHE: dict[str, tuple[float, any]] = {}
_DEFAULT_TTL = 1800


def _get(path: str, ttl: int = _DEFAULT_TTL) -> Optional[any]:
    now = time.time()
    if path in _CACHE and now - _CACHE[path][0] < ttl:
        return _CACHE[path][1]
    try:
        req = urllib.request.Request(
            f"{_BASE}{path}",
            headers={"User-Agent": "beacon-bot/1.0"},
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read())
        _CACHE[path] = (now, data)
        return data
    except Exception as e:
        log.warning("DeFiLlama ctx fetch failed for %s: %s", path, e)
        return None


# ---------------------------------------------------------------------------
# Per-protocol TVL with history
# ---------------------------------------------------------------------------

def get_protocol_tvl(slug: str) -> Optional[dict]:
    """
    Get TVL + 7d/30d change for a protocol by its DeFiLlama slug.
    E.g. "hyperliquid", "aave-v3", "uniswap-v3", "meteora"
    """
    data = _get(f"/protocol/{slug}", ttl=1800)
    if not data:
        return None

    tvl_series = data.get("tvl", [])
    if not tvl_series:
        return None

    current_tvl = tvl_series[-1]["totalLiquidityUSD"]

    def tvl_n_days_ago(n: int) -> Optional[float]:
        cutoff = time.time() - (n * 86400)
        for entry in reversed(tvl_series):
            if entry["date"] <= cutoff:
                return entry["totalLiquidityUSD"]
        return None

    tvl_7d = tvl_n_days_ago(7)
    tvl_30d = tvl_n_days_ago(30)

    return {
        "slug": slug,
        "name": data.get("name", slug),
        "current_tvl": current_tvl,
        "change_7d_pct": round((current_tvl - tvl_7d) / tvl_7d * 100, 1) if tvl_7d and tvl_7d > 0 else None,
        "change_30d_pct": round((current_tvl - tvl_30d) / tvl_30d * 100, 1) if tvl_30d and tvl_30d > 0 else None,
        "category": data.get("category", ""),
    }


def format_protocol_tvl(slug: str) -> str:
    """One-liner TVL context. E.g. 'Hyperliquid TVL: $2.1B (+34% 7d)'"""
    d = get_protocol_tvl(slug)
    if not d or not d["current_tvl"]:
        return ""
    tvl = d["current_tvl"]
    tvl_str = f"${tvl/1e9:.2f}B" if tvl >= 1e9 else f"${tvl/1e6:.0f}M"
    changes = []
    if d["change_7d_pct"] is not None:
        c = d["change_7d_pct"]
        changes.append(f"{'+'if c>0 else ''}{c}% 7d")
    if d["change_30d_pct"] is not None:
        c = d["change_30d_pct"]
        changes.append(f"{'+'if c>0 else ''}{c}% 30d")
    change_str = f" ({', '.join(changes)})" if changes else ""
    return f"{d['name']} TVL: {tvl_str}{change_str}"


# ---------------------------------------------------------------------------
# Total DeFi TVL macro
# ---------------------------------------------------------------------------

def get_total_tvl_context() -> str:
    """'Total DeFi TVL: $98B (up from $72B 30d ago, +36%)'"""
    data = _get("/charts", ttl=3600)
    if not data or not isinstance(data, list) or len(data) < 2:
        return ""
    current = data[-1]["totalLiquidityUSD"]
    ago = data[-30]["totalLiquidityUSD"] if len(data) >= 30 else data[0]["totalLiquidityUSD"]
    curr_str = f"${current/1e9:.1f}B"
    ago_str = f"${ago/1e9:.1f}B"
    change = round((current - ago) / ago * 100, 1) if ago > 0 else 0
    direction = "up" if change > 0 else "down"
    return f"Total DeFi TVL: {curr_str} ({direction} from {ago_str} 30d ago, {'+' if change>0 else ''}{change}%)"


# ---------------------------------------------------------------------------
# 7-day TVL movers (bigger picture than existing 24h movers)
# ---------------------------------------------------------------------------

def get_weekly_movers(limit: int = 6, min_tvl: float = 50e6) -> list[dict]:
    """Protocols with biggest 7d TVL change, filtered by min TVL."""
    data = _get("/protocols", ttl=3600)
    if not data or not isinstance(data, list):
        return []
    movers = []
    for p in data:
        tvl = p.get("tvl") or 0
        change = p.get("change_7d")
        if tvl < min_tvl or change is None:
            continue
        try:
            movers.append({
                "name": p["name"],
                "slug": p.get("slug", ""),
                "tvl": float(tvl),
                "change_7d_pct": round(float(change), 1),
                "category": p.get("category", ""),
            })
        except (TypeError, ValueError):
            continue
    movers.sort(key=lambda x: abs(x["change_7d_pct"]), reverse=True)
    return movers[:limit]


def format_weekly_movers() -> str:
    """'TVL up 7d: Hyperliquid +34%, Morpho +18%. TVL down: Compound -12%'"""
    movers = get_weekly_movers(limit=8)
    if not movers:
        return ""
    gainers = [m for m in movers if m["change_7d_pct"] > 10][:3]
    losers = [m for m in movers if m["change_7d_pct"] < -10][:3]
    parts = []
    if gainers:
        parts.append("TVL gainers 7d: " + ", ".join(f"{m['name']} +{m['change_7d_pct']}%" for m in gainers))
    if losers:
        parts.append("TVL losers 7d: " + ", ".join(f"{m['name']} {m['change_7d_pct']}%" for m in losers))
    return ". ".join(parts)


# ---------------------------------------------------------------------------
# Real yields (sustainable APY, not mercenary mining)
# ---------------------------------------------------------------------------

def get_top_real_yields(
    min_tvl: float = 10e6,
    max_apy: float = 40.0,
    stable_only: bool = True,
    limit: int = 5,
) -> list[dict]:
    """
    Top yield pools filtered for realism:
      - min_tvl: ignore micro pools
      - max_apy: ignore obvious Ponzi yields (>40% on stables = red flag)
      - stable_only: stablecoin pools only (safer, more predictable)
    """
    data = _get("/yields/pools", ttl=3600)
    if not data or not isinstance(data, list):
        return []
    pools = []
    for p in data:
        tvl = p.get("tvlUsd") or 0
        apy = p.get("apy") or 0
        if tvl < min_tvl or apy > max_apy or apy <= 0:
            continue
        if stable_only and not p.get("stablecoin", False):
            continue
        pools.append({
            "project": p.get("project", ""),
            "symbol": p.get("symbol", ""),
            "chain": p.get("chain", ""),
            "apy": round(float(apy), 2),
            "tvl_usd": float(tvl),
            "stable": p.get("stablecoin", False),
        })
    pools.sort(key=lambda x: x["apy"], reverse=True)
    return pools[:limit]


def format_top_yields(stable_only: bool = True) -> str:
    """'Top stable yields: Aave USDC 8.2% on Arbitrum | Morpho USDC 7.1% on Base'"""
    pools = get_top_real_yields(stable_only=stable_only, limit=3)
    if not pools:
        return ""
    label = "Top stable yields" if stable_only else "Top DeFi yields"
    items = [f"{p['project']} {p['symbol']} {p['apy']}% on {p['chain']}" for p in pools]
    return f"{label}: {' | '.join(items)}"


# ---------------------------------------------------------------------------
# Build full context block for a specific protocol slug
# ---------------------------------------------------------------------------

def build_protocol_context(slug: str) -> str:
    """Full DeFiLlama context for a specific protocol. Used by researcher agent."""
    parts = []
    tvl_line = format_protocol_tvl(slug)
    if tvl_line:
        parts.append(tvl_line)
    total = get_total_tvl_context()
    if total:
        parts.append(total)
    movers = format_weekly_movers()
    if movers:
        parts.append(movers)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# General market context for writer injection (no specific protocol)
# ---------------------------------------------------------------------------

def build_market_context() -> str:
    """Total TVL + weekly movers + top yields. Used as background context."""
    parts = []
    total = get_total_tvl_context()
    if total:
        parts.append(total)
    movers = format_weekly_movers()
    if movers:
        parts.append(movers)
    yields = format_top_yields(stable_only=True)
    if yields:
        parts.append(yields)
    return "\n".join(parts)
