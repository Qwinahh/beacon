"""
Learner Agent — absorbs market data and community signals into the knowledge base.

Runs twice daily via GitHub Actions (learn.yml). Each run:

1. Fetches live market context: Fear & Greed, prices, DeFiLlama TVL.
2. Updates data/vault/knowledge/market_context.md.
3. Fetches community signals from Reddit (+ Telegram/Discord if tokens set).
4. Runs everything through the 4-tier Verifier.
5. Writes confirmed facts to data/vault/knowledge/events/ (tier 1-2 only).
6. Writes community signals to data/vault/knowledge/signals/ with
   explicit NOT CONFIRMED labelling — never mixed with facts.

The learner never modifies project theses (that's the Researcher's job).
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from agents.base import ToolAgent
from bot.brain.verifier import Verifier

log = logging.getLogger(__name__)

_KNOWLEDGE_DIR = Path("data/vault/knowledge")
_EVENTS_DIR    = _KNOWLEDGE_DIR / "events"
_SIGNALS_DIR   = _KNOWLEDGE_DIR / "signals"


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _fetch_market_context() -> dict:
    """Gather live Fear & Greed, BTC/ETH/SOL prices, total DeFi TVL."""
    out: dict = {}
    try:
        from bot.sources.fear_greed import fetch_fear_greed
        fg = fetch_fear_greed()
        if fg:
            out["fear_greed"] = fg
    except Exception as exc:
        log.warning("Fear & Greed fetch error: %s", exc)
    try:
        from bot.sources.coingecko import fetch_prices
        prices = fetch_prices()
        if prices:
            out["prices"] = prices
    except Exception as exc:
        log.warning("CoinGecko fetch error: %s", exc)
    try:
        from bot.sources.defillama_ctx import fetch_total_tvl
        tvl = fetch_total_tvl()
        if tvl:
            out["total_tvl"] = tvl
    except Exception as exc:
        log.warning("DeFiLlama TVL fetch error: %s", exc)
    return out


def _fetch_community_signals() -> list[dict]:
    """Collect signals from Reddit (Telegram/Discord if env vars set)."""
    signals: list[dict] = []
    try:
        from bot.sources.reddit import fetch_all_signals
        for s in fetch_all_signals(limit=15):
            signals.append({
                "source":     "reddit",
                "text":       s.title,
                "meta":       s.meta,
                "age_hours":  s.age_hours,
            })
    except Exception as exc:
        log.warning("Reddit signal fetch error: %s", exc)

    if os.environ.get("TELEGRAM_BOT_TOKEN"):
        try:
            from bot.sources.telegram import fetch_all_signals as tg_signals
            for s in tg_signals(limit=10):
                signals.append({
                    "source":    "telegram",
                    "text":      s.text,
                    "meta":      s.meta,
                    "age_hours": s.age_hours,
                })
        except Exception as exc:
            log.warning("Telegram signal fetch error: %s", exc)

    if os.environ.get("DISCORD_BOT_TOKEN"):
        try:
            from bot.sources.discord import fetch_all_signals as dc_signals
            for s in dc_signals(limit=10):
                signals.append({
                    "source":    "discord",
                    "text":      s.text,
                    "meta":      s.meta,
                    "age_hours": s.age_hours,
                })
        except Exception as exc:
            log.warning("Discord signal fetch error: %s", exc)

    return signals


def _verify_signals(signals: list[dict]) -> dict:
    """Run signals through the 4-tier verifier."""
    v = Verifier()
    for s in signals:
        v.add(s["text"], source=s["source"])
    return {
        "confirmed": [{"text": i.text, "source": i.source} for i in v.confirmed_facts()],
        "community": [{"text": i.text, "source": i.source} for i in v.community_signals()],
        "rejected":  [{"text": i.text, "source": i.source} for i in v.rejected()],
        "summary":   v.summary(),
    }


def _write_event(title: str, facts: list[str], source: str) -> dict:
    """Write a confirmed event to data/vault/knowledge/events/."""
    _EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug  = title.lower()[:40].replace(" ", "-").replace("/", "-")
    slug  = "".join(c for c in slug if c.isalnum() or c == "-")
    path  = _EVENTS_DIR / f"{today}-{slug}.md"
    lines = [
        f"---\ndate: {today}\nsource: {source}\ntier: confirmed\n---\n\n",
        f"# {title}\n\n",
    ]
    for fact in facts:
        lines.append(f"- {fact}\n")
    path.write_text("".join(lines), encoding="utf-8")
    log.info("Learner: wrote event → %s", path)
    return {"written": str(path), "facts": len(facts)}


def _write_signals(signals: list[dict], date_str: str) -> dict:
    """Write community signals to data/vault/knowledge/signals/."""
    _SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    path = _SIGNALS_DIR / f"{date_str}-community.md"
    content = (
        f"---\ndate: {date_str}\ntier: community\n"
        f"warning: NOT CONFIRMED FACTS\n---\n\n"
        f"# Community Signals — {date_str}\n\n"
        "**These are community narratives only. Never cite as confirmed.**\n\n"
    )
    for s in signals:
        content += f"- [{s['source']}] {s['text']}\n"
    path.write_text(content, encoding="utf-8")
    log.info("Learner: wrote %d community signals → %s", len(signals), path)
    return {"written": str(path), "signals": len(signals)}


def _update_market_context(market_data: dict) -> dict:
    """Update data/vault/knowledge/market_context.md."""
    _KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    path = _KNOWLEDGE_DIR / "market_context.md"
    now  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = [
        f"---\nupdated: {now}\n---\n\n",
        "# Live Market Context\n\n",
        "*Auto-updated by learner agent 2× daily.*\n\n",
    ]

    fg = market_data.get("fear_greed")
    if fg:
        lines.append(f"## Sentiment\n\nFear & Greed: **{fg['value']}/100** ({fg['label']}, {fg['direction']})\n\n")

    prices = market_data.get("prices", {})
    if prices:
        lines.append("## Prices\n\n")
        for _, d in prices.items():
            chg     = d.get("change_24h")
            chg_str = f" ({'+' if chg >= 0 else ''}{chg:.1f}% 24h)" if chg is not None else ""
            lines.append(f"- **{d['ticker']}**: ${d['price']:,.0f}{chg_str}\n")
        lines.append("\n")

    tvl = market_data.get("total_tvl")
    if tvl:
        tvl_b   = tvl["tvl_usd"] / 1e9
        chg     = tvl.get("change_7d_pct")
        chg_str = f" ({'+' if chg >= 0 else ''}{chg:.1f}% 7d)" if chg is not None else ""
        lines.append(f"## Total DeFi TVL\n\n${tvl_b:.1f}B{chg_str}\n\n")

    path.write_text("".join(lines), encoding="utf-8")
    log.info("Learner: updated market_context.md")
    return {"written": str(path)}


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

_FETCH_MARKET_SCHEMA = {
    "name": "fetch_market_context",
    "description": "Fetch live market data: Fear & Greed index, BTC/ETH/SOL prices, total DeFi TVL.",
    "input_schema": {"type": "object", "properties": {}, "required": []},
}

_FETCH_SIGNALS_SCHEMA = {
    "name": "fetch_community_signals",
    "description": "Collect community signals from Reddit, Telegram (if token set), Discord (if token set).",
    "input_schema": {"type": "object", "properties": {}, "required": []},
}

_VERIFY_SCHEMA = {
    "name": "verify_signals",
    "description": "Run signals through the 4-tier verifier (on-chain > research > community > noise).",
    "input_schema": {
        "type": "object",
        "properties": {
            "signals": {
                "type":  "array",
                "items": {"type": "object"},
                "description": "List of {text, source} dicts from fetch_community_signals.",
            }
        },
        "required": ["signals"],
    },
}

_WRITE_EVENT_SCHEMA = {
    "name": "write_event",
    "description": "Write a confirmed event or data point to knowledge/events/. Only tier 1-2 facts.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title":  {"type": "string", "description": "Short title for the event."},
            "facts":  {"type": "array", "items": {"type": "string"}, "description": "Factual bullet points with numbers."},
            "source": {"type": "string", "description": "Data source that confirmed this."},
        },
        "required": ["title", "facts", "source"],
    },
}

_WRITE_SIGNALS_SCHEMA = {
    "name": "write_signals",
    "description": "Write community signals (tier 3) to knowledge/signals/. Clearly labelled NOT CONFIRMED.",
    "input_schema": {
        "type": "object",
        "properties": {
            "signals":  {"type": "array", "items": {"type": "object"}},
            "date_str": {"type": "string", "description": "Date string YYYY-MM-DD."},
        },
        "required": ["signals", "date_str"],
    },
}

_UPDATE_MARKET_SCHEMA = {
    "name": "update_market_context",
    "description": "Persist latest prices, TVL, and sentiment to market_context.md.",
    "input_schema": {
        "type": "object",
        "properties": {
            "market_data": {"type": "object", "description": "Output from fetch_market_context."},
        },
        "required": ["market_data"],
    },
}


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class LearnerAgent(ToolAgent):

    SYSTEM = (
        "You are the Learner Agent for @Qwinahh's crypto bot.\n\n"
        "Your job: absorb today's market data and community signals into the\n"
        "knowledge base. Run twice daily. Keep the knowledge fresh.\n\n"
        "Process:\n"
        "1. Call fetch_market_context() — get Fear & Greed, prices, DeFi TVL.\n"
        "2. Call update_market_context(market_data) — persist the snapshot.\n"
        "3. Call fetch_community_signals() — collect Reddit/Telegram/Discord.\n"
        "4. Call verify_signals(signals) — classify tier 1-4.\n"
        "5. For confirmed facts (tier 1-2): group related facts, call write_event().\n"
        "   Max 3 write_event calls per run — only the most noteworthy facts.\n"
        "6. For community signals (tier 3): call write_signals() — one file per day.\n"
        "   NEVER mix community signals into confirmed events.\n\n"
        "Rules:\n"
        "- Never write tier 4 (noise) anywhere.\n"
        "- Community signals stay separated from facts, always.\n\n"
        'Return JSON: {"learned": true, "events_written": N, "signals_written": N, "market_updated": true}'
    )

    TOOLS = {
        "fetch_market_context":   (_fetch_market_context,   _FETCH_MARKET_SCHEMA),
        "fetch_community_signals": (_fetch_community_signals, _FETCH_SIGNALS_SCHEMA),
        "verify_signals":         (_verify_signals,          _VERIFY_SCHEMA),
        "write_event":            (_write_event,             _WRITE_EVENT_SCHEMA),
        "write_signals":          (_write_signals,           _WRITE_SIGNALS_SCHEMA),
        "update_market_context":  (_update_market_context,   _UPDATE_MARKET_SCHEMA),
    }


def run_learning_cycle() -> dict:
    """Entry point called by learn.yml."""
    log.info("Learner: starting learning cycle.")
    today  = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    result = LearnerAgent().run(f"Run the learning cycle for today ({today}).")
    log.info("Learner: done — %s", result)
    return result


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    result = run_learning_cycle()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("learned") else 1)
