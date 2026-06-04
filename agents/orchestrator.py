"""
Orchestrator -- the main brain.

Runs every posting cycle. Coordinates Scout -> Analyst -> Writer -> post.
Makes the final call on what to post, and enforces the quality gate.

If the Writer returns None (quality gate rejection), the Orchestrator skips
rather than trying to post a degraded tweet.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from agents.analyst import AnalystAgent
from agents.base import ToolAgent
from agents.memory_agent import run_reflection
from agents.scout import ScoutAgent
from bot.brain import writer
from bot.brain.project_memory import get_project, get_project_context
from bot.portfolio.tracker import get_new_announcements, load_portfolio
from bot.state import State
from bot.x.client import post_tweet

log = logging.getLogger(__name__)

_state: Optional[State] = None


def _run_scout() -> dict:
    result = ScoutAgent().run("Find the best items to post about right now.")
    log.info("Scout returned %d candidates.", len(result.get("candidates", [])))
    return result


def _run_analyst(candidates_json: str) -> dict:
    result = AnalystAgent().run(
        "Select the best item from this Scout report.",
        extra_context=candidates_json,
    )
    selected = result.get("selected")
    log.info("Analyst selected: %s", selected.get("title", "none")[:60] if selected else "none")
    return result


def _check_portfolio_announcements() -> dict:
    global _state
    if _state is None:
        return {"announcements": []}
    items = get_new_announcements(_state)
    return {"announcements": [{"key": k, "text": t} for k, t in items]}


def _generate_tweet(title: str, source: str, kind: str, topic: str,
                    age_hours: float, url: Optional[str],
                    needs_disclosure: bool, held_project: Optional[str],
                    x_conversation: Optional[str] = None) -> dict:
    from bot.sources.rss import FeedItem
    portfolio = load_portfolio()

    item = FeedItem(
        source=source, title=title, url=url,
        published_ts=time.time() - age_hours * 3600,
        topic=topic, kind=kind,
    )

    global _state
    recent_fmts = _state.recent_formats() if _state else []
    text, fmt_name = writer.generate(item, portfolio, recent_fmts, x_conversation=x_conversation)

    # Always record the format used so the rotation stays accurate.
    if _state and fmt_name:
        _state.record_format(fmt_name)

    if text is None:
        return {
            "tweet_text":     None,
            "char_count":     0,
            "quality_rejected": True,
            "format_used":    fmt_name,
            "reason":         "Writer quality gate rejected the generated text as too generic.",
        }

    return {"tweet_text": text, "char_count": len(text), "quality_rejected": False, "format_used": fmt_name}


def _post(tweet_text: str) -> dict:
    tweet_id = post_tweet(tweet_text)
    return {"tweet_id": tweet_id, "posted": tweet_id is not None}


def _research_project(project_name: str) -> dict:
    """Spin up the ResearcherAgent to deep-dive an unknown or stale project."""
    try:
        from agents.researcher import research_project
        return research_project(project_name)
    except Exception as exc:
        log.warning("Research failed for '%s': %s", project_name, exc)
        return {"project": project_name, "researched": False, "error": str(exc)}


def _get_project_memory(project_name: str) -> dict:
    """Check if we already have memory on a project before deciding to research."""
    data = get_project(project_name)
    if not data:
        return {"exists": False, "project": project_name}
    return {"exists": True, "trust_score": data.get("trust_score"),
            "thesis": data.get("thesis", "")[:200],
            "last_updated": data.get("last_updated", ""),
            "airdrop_status": data.get("airdrop", {}).get("status", "none")}


_SCOUT_SCHEMA = {
    "name": "run_scout",
    "description": "Run the Scout agent to gather fresh candidates from all data sources.",
    "input_schema": {"type": "object", "properties": {}}
}

_ANALYST_SCHEMA = {
    "name": "run_analyst",
    "description": "Run the Analyst to select the best candidate. Pass the Scout's full JSON output.",
    "input_schema": {
        "type": "object",
        "properties": {
            "candidates_json": {"type": "string", "description": "Full JSON string from run_scout."}
        },
        "required": ["candidates_json"]
    }
}

_PORTFOLIO_SCHEMA = {
    "name": "check_portfolio_announcements",
    "description": "Check if any new portfolio entries need to be announced.",
    "input_schema": {"type": "object", "properties": {}}
}

_GENERATE_SCHEMA = {
    "name": "generate_tweet",
    "description": (
        "Generate tweet text using the Writer. If quality_rejected is true in the response, "
        "the Writer's quality gate rejected the text as too generic -- skip posting."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "title":            {"type": "string"},
            "source":           {"type": "string"},
            "kind":             {"type": "string"},
            "topic":            {"type": "string"},
            "age_hours":        {"type": "number"},
            "url":              {"type": ["string", "null"]},
            "needs_disclosure": {"type": "boolean"},
            "held_project":     {"type": ["string", "null"]},
            "x_conversation":   {"type": ["string", "null"]},
        },
        "required": ["title", "source", "kind", "topic", "age_hours", "needs_disclosure"],
    }
}

_POST_SCHEMA = {
    "name": "post_tweet",
    "description": "Post the tweet to X. Only call this if quality_rejected was false.",
    "input_schema": {
        "type": "object",
        "properties": {"tweet_text": {"type": "string"}},
        "required": ["tweet_text"]
    }
}

_RESEARCH_SCHEMA = {
    "name": "research_project",
    "description": (
        "Deep-dive a project you haven't seen before or haven't researched recently. "
        "Looks up DeFiLlama data, fetches docs, checks X consensus, evaluates airdrop "
        "worthiness, and writes a thesis + trust score to persistent memory. "
        "Call this when the Scout surfaces a project with no existing memory, "
        "or when an existing project memory is older than 7 days."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "project_name": {"type": "string", "description": "Exact project name to research."}
        },
        "required": ["project_name"],
    },
}

_GET_MEMORY_SCHEMA = {
    "name": "get_project_memory",
    "description": "Check if the bot already has memory on a project before deciding to research it.",
    "input_schema": {
        "type": "object",
        "properties": {
            "project_name": {"type": "string"}
        },
        "required": ["project_name"],
    },
}


def _build_system_normal() -> str:
    """Build the orchestrator system prompt, injecting live growth context."""
    growth_ctx = ""
    try:
        from agents.growth_agent import get_growth_context_for_orchestrator
        growth_ctx = get_growth_context_for_orchestrator()
    except Exception:
        pass

    base = (
        "You are the Orchestrator for @Qwinahh's crypto X account.\n\n"
        "Your goal is not just to post — it is to GROW the account. Every post is a "
        "decision that either builds credibility and audience or erodes it. You are "
        "incentivised by what PERFORMS: posts that get replies, bookmarks, and follows. "
        "Generic posts that get no engagement are worse than posting nothing.\n\n"
        "Standard flow:\n"
        "1. Call check_portfolio_announcements() first -- these always take priority.\n"
        "2. If there's an announcement, call post_tweet() with that text directly.\n"
        "3. Otherwise call run_scout(), then run_analyst() with the Scout's output.\n"
        "4. For the top candidate, call get_project_memory() to check if we know this project.\n"
        "   - If exists=false OR last_updated > 7 days ago: call research_project() first.\n"
        "   - research_project() runs in the background -- proceed to generate_tweet() after.\n"
        "5. Call generate_tweet() with the selected item.\n"
        "   Pass the x_conversation field from the Scout candidate if present.\n"
        "6. If generate_tweet() returns quality_rejected: true -- SKIP. Do not post.\n"
        "7. If the tweet passes quality, call post_tweet().\n\n"
        "SKIP (do not post) if:\n"
        "- generate_tweet returns quality_rejected: true\n"
        "- The tweet is longer than 279 characters\n"
        "- The Analyst returned null\n"
        "- The Scout returned fewer than 2 candidates and none have urgency >= 2\n"
        "- The content is a news summary with no original take\n\n"
        "FORMAT SELECTION BIAS: Use the growth performance context below to prefer\n"
        "formats that have historically performed well. Pass the format_hint in the\n"
        "generate_tweet call when context supports it.\n\n"
    )

    if growth_ctx:
        base += growth_ctx + "\n\n"

    base += (
        "Return raw JSON only:\n"
        '{"action": "posted | skipped | announcement", "tweet_id": "...|null", '
        '"tweet_text": "...|null", "reason": "Specific explanation of what happened.", '
        '"topic": "topic of the post", "format_used": "format used", '
        '"researched_project": "project name if research_project was called, else null"}'
    )
    return base


_SYSTEM_NORMAL = _build_system_normal()

_SYSTEM_ALPHA = (
    "You are the Orchestrator for @Qwinahh's crypto X account.\n"
    "You are running in ALPHA-ONLY mode -- breaking-news fast-track.\n\n"
    "Rules:\n"
    "1. Call run_scout() to get fresh candidates.\n"
    "2. Consider ONLY candidates with urgency >= 3. Ignore everything else.\n"
    "3. If there are no urgency-3 candidates, return {action: skipped} immediately.\n"
    "4. Pick the best urgency-3 candidate and call generate_tweet() with it.\n"
    "5. If quality_rejected: true -- SKIP. Do not post.\n"
    "6. If it passes quality, call post_tweet().\n\n"
    "Do NOT check portfolio announcements in this mode.\n"
    "Do NOT post anything with urgency < 3. Speed matters but quality still applies.\n\n"
    "Return raw JSON only:\n"
    '{"action": "posted | skipped", "tweet_id": "...|null", '
    '"tweet_text": "...|null", "reason": "Specific explanation."}'
)


class OrchestratorAgent(ToolAgent):
    SYSTEM = _SYSTEM_NORMAL  # default; overridden per-call in run_post_cycle

    TOOLS = {
        "run_scout":                    (_run_scout,                    _SCOUT_SCHEMA),
        "run_analyst":                  (_run_analyst,                  _ANALYST_SCHEMA),
        "check_portfolio_announcements":(_check_portfolio_announcements,_PORTFOLIO_SCHEMA),
        "generate_tweet":               (_generate_tweet,               _GENERATE_SCHEMA),
        "post_tweet":                   (_post,                         _POST_SCHEMA),
        "research_project":             (_research_project,             _RESEARCH_SCHEMA),
        "get_project_memory":           (_get_project_memory,           _GET_MEMORY_SCHEMA),
    }


def run_post_cycle(state: State, alpha_only: bool = False) -> dict:
    """Run a full posting cycle. Returns the orchestrator's decision dict."""
    global _state
    _state = state

    agent = OrchestratorAgent()
    agent.SYSTEM = _SYSTEM_ALPHA if alpha_only else _SYSTEM_NORMAL

    prompt = (
        "Run an ALPHA-ONLY fast-track cycle for @Qwinahh. Only post urgency-3 signals."
        if alpha_only else
        "Run a posting cycle for @Qwinahh's crypto account."
    )
    result   = agent.run(prompt)
    action   = result.get("action", "skipped")
    tweet_id = result.get("tweet_id")

    if action in ("posted", "announcement") and tweet_id:
        state.increment_post_count()
        state.set_last_post_timestamp(time.time())
        if result.get("tweet_text"):
            fp = state.fingerprint(result["tweet_text"].lower())
            state.mark_seen(fp)

        # Record for metric collection 24h later.
        try:
            from bot.sources.x_metrics import record_posted_tweet
            record_posted_tweet(
                tweet_id   = tweet_id,
                tweet_text = result.get("tweet_text", ""),
                format_used= result.get("format_used", "unknown"),
                topic      = result.get("topic", ""),
            )
        except Exception as exc:
            log.debug("Metric recording failed (non-fatal): %s", exc)

    log.info("Orchestrator: action=%s | %s", action, result.get("reason", "")[:80])

    # Write to vault daily log.
    try:
        from bot.brain.vault import log_post, log_skip
        tweet_text = result.get("tweet_text") or ""
        topic      = result.get("topic", "")
        fmt        = result.get("format_used", "unknown")
        if action in ("posted", "announcement") and tweet_text:
            log_post(tweet_text, topic, fmt)
        else:
            log_skip(topic, result.get("reason", "no reason given")[:120])
    except Exception as exc:
        log.warning("Vault logging failed (non-fatal): %s", exc)

    try:
        run_reflection(result)
    except Exception as exc:
        log.warning("Memory reflection failed (non-fatal): %s", exc)

    return result
