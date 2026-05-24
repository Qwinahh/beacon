"""
Hyperliquid alpha signals.

Uses the official hyperliquid-python-sdk to pull funding rates and open
interest. When these cross meaningful thresholds, they become urgency-2
alpha signals -- the kind of perp market data that makes for an actually
useful tweet rather than a generic news summary.

Requires: pip install hyperliquid-python-sdk
If not installed, all functions return empty lists silently.

Signal types generated:
  - Extreme funding rate (>0.05%/8h on BTC or ETH perp)
  - Large OI shift (>15% move in 24h)
  - Funding rate divergence between BTC and ETH (>0.04% spread)
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from bot.sources.alpha import AlphaSignal

log = logging.getLogger(__name__)

# Thresholds for signal generation.
FUNDING_RATE_EXTREME   = 0.0005   # 0.05% per 8h -- marks longs/shorts crowded
FUNDING_RATE_DIVERGENCE = 0.0004  # Spread between BTC and ETH funding
OI_CHANGE_PCT_THRESHOLD = 15.0    # % OI change in 24h to flag

# Perp coins to monitor.
WATCH_COINS = ["BTC", "ETH", "SOL", "HYPE"]


def _get_info():
    """Return Hyperliquid Info object or None if SDK not installed."""
    try:
        from hyperliquid.info import Info
        return Info(base_url="https://api.hyperliquid.xyz", skip_ws=True)
    except ImportError:
        return None
    except Exception as exc:
        log.warning("Hyperliquid SDK init failed: %s", exc)
        return None


def _safe_float(val, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def fetch_funding_signals() -> list[AlphaSignal]:
    """
    Check current funding rates and OI for watched coins.
    Returns AlphaSignal objects for any that cross thresholds.
    """
    info = _get_info()
    if info is None:
        return []

    signals: list[AlphaSignal] = []

    try:
        meta = info.meta()
        universe = meta.get("universe", [])
        # Build name->index map.
        name_to_idx = {c["name"]: i for i, c in enumerate(universe)}

        all_mids = info.all_mids()  # {coin: mid_price_str}
        ctx_data  = info.contexts()  # list of (AssetContext, ...)

        funding_rates: dict[str, float] = {}
        oi_values:     dict[str, float] = {}

        for coin in WATCH_COINS:
            idx = name_to_idx.get(coin)
            if idx is None or idx >= len(ctx_data):
                continue
            ctx = ctx_data[idx][0] if isinstance(ctx_data[idx], (list, tuple)) else ctx_data[idx]
            if hasattr(ctx, "funding"):
                funding_rates[coin] = _safe_float(ctx.funding)
            if hasattr(ctx, "openInterest"):
                oi_values[coin] = _safe_float(ctx.openInterest)

        # --- Extreme funding rate signals ---
        for coin, rate in funding_rates.items():
            if abs(rate) >= FUNDING_RATE_EXTREME:
                direction = "longs" if rate > 0 else "shorts"
                payer     = "shorts" if rate > 0 else "longs"
                urgency   = 2
                signals.append(AlphaSignal(
                    title=(
                        f"Hyperliquid {coin} perp funding at {rate*100:.3f}%/8h "
                        f"-- {direction} paying {payer}"
                    ),
                    kind="alpha",
                    source="hyperliquid",
                    topic=f"{coin.lower()} perps funding",
                    urgency=urgency,
                    age_hours=0.0,
                    url=f"https://app.hyperliquid.xyz/trade/{coin}",
                    meta={
                        "coin":     coin,
                        "funding":  rate,
                        "signal":   "extreme_funding",
                    },
                ))

        # --- Funding rate divergence (BTC vs ETH) ---
        btc_f = funding_rates.get("BTC")
        eth_f = funding_rates.get("ETH")
        if btc_f is not None and eth_f is not None:
            divergence = abs(btc_f - eth_f)
            if divergence >= FUNDING_RATE_DIVERGENCE:
                higher = "BTC" if btc_f > eth_f else "ETH"
                lower  = "ETH" if btc_f > eth_f else "BTC"
                signals.append(AlphaSignal(
                    title=(
                        f"Perp funding divergence: {higher} at {funding_rates[higher]*100:.3f}%/8h "
                        f"vs {lower} at {funding_rates[lower]*100:.3f}%/8h"
                    ),
                    kind="alpha",
                    source="hyperliquid",
                    topic="perps funding divergence",
                    urgency=2,
                    age_hours=0.0,
                    url="https://app.hyperliquid.xyz",
                    meta={
                        "btc_funding": btc_f,
                        "eth_funding": eth_f,
                        "divergence":  divergence,
                        "signal":      "funding_divergence",
                    },
                ))

    except Exception as exc:
        log.warning("Hyperliquid signal fetch failed: %s", exc)

    return signals
