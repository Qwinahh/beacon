"""
Analyst Agent -- editorial decision maker.

The Analyst receives the Scout's candidate list and selects exactly ONE item
to post. The bar is high: if nothing clears it, return null. Posting nothing
is always better than posting something generic.

A qualifying item must meet ALL of these:
  - Contains a specific number, data point, or named protocol event
  - Enables a take that says something non-obvious
  - Is fresh enough that the conversation hasn't moved on
  - Hasn't already been posted (fingerprint check)
  - Isn't the same topic as the last 2 posts on that subject
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from agents.base import ToolAgent
from bot.config import FINGERPRINT_MEMORY_SIZE, MAX_TOPIC_REPEAT, PORTFOLIO_PATH, STATE_PATH


def _score_item(title: str, source: str, kind: str, topic: str, age_hours: float) -> dict:
    from bot.brain.scorer import score
    from bot.sources.rss import FeedItem
    dummy = FeedItem(
        source=source, title=title, url=None,
        published_ts=time.time() - age_hours * 3600,
        topic=topic, kind=kind,
    )
    s = score(dummy)
    return {"score": s, "title": title[:60]}


def _get_recent_history() -> dict:
    p = Path(STATE_PATH)
    if not p.exists():
        return {"topics": [], "formats": [], "posts_today": 0}
    try:
        data = json.loads(p.read_text())
        from datetime import date
        today = date.today().isoformat()
        return {
            "topics":      data.get("recent_topics", [])[-20:],
            "formats":     data.get("recent_formats", [])[-10:],
            "posts_today": data.get("daily_counts", {}).get(today, 0),
            "seen_count":  len(data.get("seen", [])),
        }
    except Exception:
        return {"topics": [], "formats": [], "posts_today": 0}


def _check_seen(title: str) -> dict:
    from bot.state import State
    s = State()
    s.load()
    fp = s.fingerprint(title.lower())
    return {"seen": s.has_seen(fp), "fingerprint": fp}


def _get_portfolio_context() -> dict:
    p = Path(PORTFOLIO_PATH)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text())
        return {
            "active_positions": [
                {"project": x["project"], "ticker": x.get("ticker", "")}
                for x in data.get("positions", []) if x.get("status") == "active"
            ],
            "active_airdrops": [
                {"project": x["project"]}
                for x in data.get("airdrops", []) if x.get("status") == "farming"
            ],
            "watching": [
                {"project": x["project"]}
                for x in data.get("watching", [])
            ],
        }
    except Exception:
        return {}


_SCORE_SCHEMA = {
    "name": "score_item",
    "description": "Run the deterministic relevance scorer on a candidate item.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title":     {"type": "string"},
            "source":    {"type": "string"},
            "kind":      {"type": "string", "description": "rss | raise | tvl | alpha"},
            "topic":     {"type": "string"},
            "age_hours": {"type": "number"},
        },
        "required": ["title", "source", "kind", "topic", "age_hours"],
    }
}

_HISTORY_SCHEMA = {
    "name": "get_recent_history",
    "description": "Get recent posting history: topics covered, formats used, post count today.",
    "input_schema": {"type": "object", "properties": {}}
}

_CHECK_SEEN_SCHEMA = {
    "name": "check_seen",
    "description": "Check if a title has already been posted (deduplication).",
    "input_schema": {
        "type": "object",
        "properties": {"title": {"type": "string"}},
        "required": ["title"],
    }
}

_PORTFOLIO_SCHEMA = {
    "name": "get_portfolio_context",
    "description": "Get current held positions and farming activities for disclosure checks.",
    "input_schema": {"type": "object", "properties": {}}
}


class AnalystAgent(ToolAgent):

    SYSTEM = (
        "You are the Editorial Analyst for a crypto X account (@Qwinahh).\n\n"
        "You receive a list of candidate items from the Scout. Your job: pick the ONE\n"
        "best item to post right now, or return null if nothing clears the bar.\n\n"
        "THE BAR IS HIGH. Posting nothing is better than posting something generic.\n\n"
        "Process:\n"
        "1. Call get_recent_history() -- know what topics were covered recently.\n"
        "2. Call get_portfolio_context() -- check if any candidate touches a held position.\n"
        "3. For your top 2-3 candidates, call score_item() to get numeric scores.\n"
        "4. Call check_seen() on your top pick to confirm it hasn't been posted before.\n"
        "5. Select the best item OR return null.\n\n"
        "MANDATORY REJECTION CRITERIA -- reject any item that:\n"
        "- Is pure price action with no on-chain or protocol reason (e.g. 'BTC up 3% today')\n"
        "- Is a generic market sentiment piece ('crypto market looks bullish')\n"
        "- Has no specific number, dollar amount, or named protocol event in it\n"
        "- Is older than 6 hours and has already circulated everywhere\n"
        "- Has the same topic as the last 2 posts\n"
        "- Has already been posted (check_seen returns true)\n"
        "- Is a pure TVL movement (kind=tvl) and the last post was also a TVL item — one TVL post per cycle max\n"
        "- Is a DeFiLlama item (TVL or raise) and the last 2 posts were also DeFiLlama items\n\n"
        "WHAT QUALIFIES -- items where the post can:\n"
        "- Give specific airdrop math (point values, eligibility thresholds, unlock timing)\n"
        "- Surface a specific data anomaly (OI spike, funding rate extreme, TVL delta)\n"
        "- Name a specific protocol event with a concrete implication\n"
        "- Update a thesis with new evidence (not just restate the thesis)\n"
        "- Identify something most people following the feed will have missed\n\n"
        "DISCLOSURE: always flag if the item touches a held position.\n\n"
        "Return raw JSON only:\n"
        '{"selected": {"title": "...", "source": "...", "kind": "rss|raise|tvl|alpha", '
        '"topic": "...", "age_hours": 0.0, "url": "...|null", "score": 82, '
        '"needs_disclosure": true, "held_project": "Hyperliquid", '
        '"analyst_note": "Why this was selected AND why it clears the bar specifically."}, '
        '"rejection_log": ["Item X rejected because: no specific number", '
        '"Item Y rejected because: same topic as last post"]}\n\n'
        "Or if nothing qualifies:\n"
        '{"selected": null, "analyst_note": "Why nothing qualifies. Be specific.", '
        '"rejection_log": ["..."]}'
    )

    TOOLS = {
        "score_item":           (_score_item,           _SCORE_SCHEMA),
        "get_recent_history":   (_get_recent_history,   _HISTORY_SCHEMA),
        "check_seen":           (_check_seen,           _CHECK_SEEN_SCHEMA),
        "get_portfolio_context":(_get_portfolio_context,_PORTFOLIO_SCHEMA),
    }
