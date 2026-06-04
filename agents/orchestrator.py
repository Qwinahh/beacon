"""
Orchestrator -- pure-Python posting pipeline.

NO LLM IS USED HERE. Orchestration is deterministic Python:
  Scout (gather) -> Analyst (score + filter) -> Writer (generate text) -> Post

The only LLM call is inside writer.generate(), which uses the free
provider chain (Groq -> Cerebras -> OpenRouter -> Anthropic). This means
the bot works with just GROQ_API_KEY -- no Anthropic key required for posting.

Why this is better than the old agent loop:
  - No ANTHROPIC_API_KEY dependency for orchestration
  - No unpredictable LLM tool-call sequencing
  - Deterministic skip/post decisions -- easy to debug
  - Significantly faster (1 LLM call instead of 5-8)
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from bot.brain import writer
from bot.brain.scorer import score as score_item
from bot.brain.project_memory import get_project
from bot.portfolio.tracker import get_new_announcements, load_portfolio
from bot.sources.rss import FeedItem
from bot.state import State
from bot.x.client import post_tweet

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Step 1: Scout -- gather candidates from all data sources
# ---------------------------------------------------------------------------

def _gather_candidates(alpha_only: bool = False) -> list:
    """Pull from all data sources. Returns urgency-sorted candidate list."""
    candidates = []

    # Alpha signals (highest priority)
    try:
        from bot.sources.alpha import detect_all
        for s in detect_all():
            candidates.append({
                "title":     s.title,
                "source":    s.source,
                "kind":      s.kind,
                "topic":     s.topic,
                "age_hours": round(s.age_hours, 2),
                "url":       s.url,
                "urgency":   s.urgency,
            })
        log.info("Scout: %d alpha signals", len([c for c in candidates if c.get("urgency", 0) >= 2]))
    except Exception as exc:
        log.warning("Alpha detection failed: %s", exc)

    if alpha_only:
        result = [c for c in candidates if c.get("urgency", 0) >= 3]
        log.info("Scout (alpha-only): %d urgency-3 candidates", len(result))
        return result

    # RSS / news
    try:
        from bot.sources import newsapi, rss
        seen_titles = set()
        for item in newsapi.fetch_news(max_age_hours=8.0, limit=20):
            key = item.title.lower()[:80]
            if key not in seen_titles:
                seen_titles.add(key)
                candidates.append({
                    "title": item.title, "source": item.source,
                    "kind": "rss", "topic": item.topic,
                    "age_hours": round(item.age_hours, 2),
                    "url": item.url, "urgency": 1,
                })
        for item in rss.fetch_all(max_age_hours=8.0):
            key = item.title.lower()[:80]
            if key not in seen_titles:
                seen_titles.add(key)
                candidates.append({
                    "title": item.title, "source": item.source,
                    "kind": "rss", "topic": item.topic,
                    "age_hours": round(item.age_hours, 2),
                    "url": item.url, "urgency": 1,
                })
        log.info("Scout: %d RSS items", len([c for c in candidates if c["kind"] == "rss"]))
    except Exception as exc:
        log.warning("RSS fetch failed: %s", exc)

    # Raises
    try:
        from bot.sources import defillama
        for r in defillama.fetch_raises()[:15]:
            title = f"{r.name} raised ${r.amount:.0f}M" if r.amount else f"{r.name} raised (undisclosed)"
            candidates.append({
                "title": title, "source": "DeFiLlama",
                "kind": "raise", "topic": r.topic,
                "age_hours": round(r.age_hours, 2),
                "url": r.url, "urgency": 2,
                "amount_m": r.amount,
            })
        log.info("Scout: %d raises", len([c for c in candidates if c["kind"] == "raise"]))
    except Exception as exc:
        log.warning("Raises fetch failed: %s", exc)

    # TVL movers
    try:
        from bot.sources import defillama
        for m in defillama.fetch_tvl_movers(min_change_pct=15.0)[:10]:
            direction = "up" if m.change_pct > 0 else "down"
            candidates.append({
                "title": f"{m.name} TVL {direction} {abs(m.change_pct):.1f}%",
                "source": "DeFiLlama", "kind": "tvl", "topic": m.topic,
                "age_hours": 0.0, "url": m.url, "urgency": 1,
                "change_pct": m.change_pct,
            })
        log.info("Scout: %d TVL movers", len([c for c in candidates if c["kind"] == "tvl"]))
    except Exception as exc:
        log.warning("TVL fetch failed: %s", exc)

    # Sort: urgency desc, age asc (freshest first within each urgency tier)
    candidates.sort(key=lambda c: (-c.get("urgency", 0), c.get("age_hours", 99)))
    log.info("Scout total: %d candidates", len(candidates))
    return candidates


# ---------------------------------------------------------------------------
# Step 2: Analyst -- deterministic filtering and selection
# ---------------------------------------------------------------------------

def _select_best(candidates: list, state: State) -> Optional[dict]:
    """
    Apply rejection rules, score each candidate, return best one.
    Returns None if nothing clears the bar.
    """
    recent_topics = state.recent_topics()
    portfolio = load_portfolio()
    held = {p["project"].lower() for p in portfolio.get("positions", []) if p.get("status") == "active"}
    held |= {a["project"].lower() for a in portfolio.get("airdrops", []) if a.get("status") == "farming"}

    from bot.config import POST_SCORE_THRESHOLD, MAX_TOPIC_REPEAT

    rejection_log = []
    scored = []

    for c in candidates[:20]:
        title     = c.get("title", "")
        topic     = c.get("topic", "") or ""
        age_hours = c.get("age_hours", 0)
        kind      = c.get("kind", "rss")

        # Hard rejection: stale
        if age_hours > 7:
            rejection_log.append("STALE (%.1fh): %s" % (age_hours, title[:50]))
            continue

        # Hard rejection: repeated topic
        topic_count = recent_topics.count(topic) if topic else 0
        if topic_count >= MAX_TOPIC_REPEAT:
            rejection_log.append("TOPIC REPEAT (%dx): %s" % (topic_count, title[:50]))
            continue

        # Hard rejection: already seen
        fp = state.fingerprint(title.lower())
        if state.has_seen(fp):
            rejection_log.append("SEEN: %s" % title[:50])
            continue

        # Score
        dummy = FeedItem(
            source=c.get("source", ""), title=title, url=c.get("url"),
            published_ts=time.time() - age_hours * 3600,
            topic=topic, kind=kind,
        )
        item_score = score_item(dummy)

        # Urgency bonus
        urgency = c.get("urgency", 1)
        if urgency >= 3:
            item_score += 20
        elif urgency >= 2:
            item_score += 8

        # TVL movers for unknown protocols aren't worth posting
        if kind == "tvl" and item_score < 45:
            rejection_log.append("TVL LOW SCORE (%d): %s" % (item_score, title[:50]))
            continue

        # Soft score floor (10 below threshold to allow urgency bonus to lift)
        if item_score < POST_SCORE_THRESHOLD - 10:
            rejection_log.append("LOW SCORE (%d): %s" % (item_score, title[:50]))
            continue

        # Disclosure
        needs_disclosure = any(h in title.lower() for h in held)
        c = dict(c)  # copy to avoid mutating original
        c["needs_disclosure"] = needs_disclosure
        c["held_project"] = next((h for h in held if h in title.lower()), None)
        c["score"] = item_score
        scored.append((item_score, c))

    if rejection_log:
        log.info("Analyst rejections:\n  " + "\n  ".join(rejection_log[:10]))

    if not scored:
        log.info("Analyst: no candidate cleared the quality bar.")
        return None

    scored.sort(key=lambda x: -x[0])
    best = scored[0][1]
    log.info("Analyst selected (score=%d, urgency=%d): %s",
             best["score"], best.get("urgency", 1), best["title"][:70])
    return best


# ---------------------------------------------------------------------------
# Step 3: X conversation context (optional enrichment for writer)
# ---------------------------------------------------------------------------

def _fetch_x_context(topic: str) -> str:
    try:
        from bot.sources.xcontext import fetch_topic_posts
        posts = fetch_topic_posts(topic, limit=6)
        if posts:
            return "\n".join(posts[:6])
    except Exception as exc:
        log.debug("X context fetch failed: %s", exc)
    return ""


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_post_cycle(state: State, alpha_only: bool = False) -> dict:
    """
    Full posting cycle. Pure Python -- no LLM except writer.generate().

    Flow: portfolio check -> scout -> analyst -> writer -> post_tweet
    Returns dict with keys: action, tweet_id, tweet_text, reason, topic, format_used
    """
    log.info("=== Posting cycle start (alpha_only=%s) ===", alpha_only)
    log.info("Posts today: %d | Last post: %.1fh ago",
             state.posts_today(),
             (time.time() - state.last_post_timestamp()) / 3600
             if state.last_post_timestamp() else 999)

    # ------------------------------------------------------------------
    # Step 0: Portfolio announcements -- always highest priority
    # ------------------------------------------------------------------
    try:
        items = get_new_announcements(state)
        for key, text in items:
            tweet_id = post_tweet(text)
            if tweet_id:
                state.increment_post_count()
                state.set_last_post_timestamp(time.time())
                state.mark_seen(state.fingerprint(text.lower()))
                result = {
                    "action": "announcement", "tweet_id": tweet_id,
                    "tweet_text": text,
                    "reason": "Portfolio announcement: %s" % key,
                    "topic": key, "format_used": "announcement",
                }
                _post_success_hooks(state, result)
                return result
    except Exception as exc:
        log.warning("Portfolio announcement check failed: %s", exc)

    # ------------------------------------------------------------------
    # Step 1: Scout
    # ------------------------------------------------------------------
    try:
        candidates = _gather_candidates(alpha_only=alpha_only)
    except Exception as exc:
        log.error("Scout failed: %s", exc)
        reason = "Scout error: %s" % exc
        _log_skip("", reason, state)
        return {"action": "skipped", "reason": reason, "topic": "", "format_used": ""}

    if not candidates:
        reason = ("Alpha-only: no urgency-3 signals." if alpha_only
                  else "Scout returned no candidates.")
        log.info("Skipping: %s", reason)
        _log_skip("", reason, state)
        return {"action": "skipped", "reason": reason, "topic": "", "format_used": ""}

    # ------------------------------------------------------------------
    # Step 2: Analyst
    # ------------------------------------------------------------------
    try:
        selected = _select_best(candidates, state)
    except Exception as exc:
        log.error("Analyst failed: %s", exc)
        reason = "Analyst error: %s" % exc
        _log_skip("", reason, state)
        return {"action": "skipped", "reason": reason, "topic": "", "format_used": ""}

    if not selected:
        reason = "No candidate cleared the quality bar -- better to post nothing than something generic."
        log.info(reason)
        _log_skip("", reason, state)
        return {"action": "skipped", "reason": reason, "topic": "", "format_used": ""}

    # ------------------------------------------------------------------
    # Step 3: X context enrichment (non-fatal)
    # ------------------------------------------------------------------
    x_conversation = ""
    try:
        topic_for_ctx = selected.get("topic") or selected.get("title", "")[:30]
        x_conversation = _fetch_x_context(topic_for_ctx)
        if x_conversation:
            log.info("X context fetched: %d chars for '%s'", len(x_conversation), topic_for_ctx)
    except Exception as exc:
        log.debug("X context enrichment failed (non-fatal): %s", exc)

    # ------------------------------------------------------------------
    # Step 4: Generate tweet text (only LLM call in the pipeline)
    # ------------------------------------------------------------------
    portfolio   = load_portfolio()
    recent_fmts = state.recent_formats()

    item = FeedItem(
        source       = selected.get("source", ""),
        title        = selected["title"],
        url          = selected.get("url"),
        published_ts = time.time() - selected.get("age_hours", 0) * 3600,
        topic        = selected.get("topic", ""),
        kind         = selected.get("kind", "rss"),
    )

    try:
        text, fmt_name = writer.generate(
            item, portfolio, recent_fmts,
            x_conversation=x_conversation or None,
        )
    except Exception as exc:
        log.error("Writer failed: %s", exc)
        reason = "Writer error: %s" % exc
        _log_skip(selected.get("topic", ""), reason, state)
        return {"action": "skipped", "reason": reason,
                "topic": selected.get("topic", ""), "format_used": ""}

    if fmt_name:
        state.record_format(fmt_name)

    if text is None:
        reason = "Writer quality gate: text rejected as too generic."
        log.info(reason)
        _log_skip(selected.get("topic", ""), reason, state)
        return {"action": "skipped", "reason": reason,
                "topic": selected.get("topic", ""), "format_used": fmt_name or ""}

    log.info("Generated tweet (%d chars, fmt=%s): %s", len(text), fmt_name, text[:80])

    # ------------------------------------------------------------------
    # Step 5: Post to X
    # ------------------------------------------------------------------
    tweet_id = post_tweet(text)

    if not tweet_id:
        reason = "post_tweet() failed -- see Tweepy error above for X API details."
        log.error(reason)
        _log_skip(selected.get("topic", ""), reason, state)
        return {"action": "skipped", "reason": reason,
                "tweet_text": text,
                "topic": selected.get("topic", ""), "format_used": fmt_name or ""}

    # ------------------------------------------------------------------
    # Success
    # ------------------------------------------------------------------
    state.increment_post_count()
    state.set_last_post_timestamp(time.time())
    state.mark_seen(state.fingerprint(text.lower()))
    if selected.get("topic"):
        state.record_topic(selected["topic"])

    result = {
        "action":      "posted",
        "tweet_id":    tweet_id,
        "tweet_text":  text,
        "reason":      "Posted: %s" % selected["title"][:80],
        "topic":       selected.get("topic", ""),
        "format_used": fmt_name or "unknown",
    }

    log.info("Posted tweet %s", tweet_id)
    _post_success_hooks(state, result)
    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _post_success_hooks(state: State, result: dict) -> None:
    """Non-fatal post-success actions: metrics, vault log, memory."""
    try:
        from bot.sources.x_metrics import record_posted_tweet
        record_posted_tweet(
            tweet_id    = result["tweet_id"],
            tweet_text  = result.get("tweet_text", ""),
            format_used = result.get("format_used", "unknown"),
            topic       = result.get("topic", ""),
        )
    except Exception as exc:
        log.debug("Metric recording failed (non-fatal): %s", exc)

    try:
        from bot.brain.vault import log_post
        log_post(result.get("tweet_text", ""), result.get("topic", ""),
                 result.get("format_used", ""))
    except Exception as exc:
        log.warning("Vault log_post failed (non-fatal): %s", exc)

    try:
        from agents.memory_agent import run_reflection
        run_reflection(result)
    except Exception as exc:
        log.warning("Memory reflection failed (non-fatal): %s", exc)


def _log_skip(topic: str, reason: str, state: State) -> None:
    try:
        from bot.brain.vault import log_skip
        log_skip(topic, reason)
    except Exception as exc:
        log.warning("Vault log_skip failed (non-fatal): %s", exc)
