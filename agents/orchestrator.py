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
from bot.sources.dropstab import get_upcoming_unlocks, UnlockItem
from bot.sources.rss import FeedItem
from bot.sources.whale_alert import get_whale_alerts, WhaleItem
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
                # Store structured fields so the writer gets rich data, not just the headline
                "raise_name":       r.name,
                "raise_amount_m":   r.amount,
                "raise_round":      r.round_name,
                "raise_category":   r.category,
                "raise_published":  r.published_ts,
            })
        log.info("Scout: %d raises", len([c for c in candidates if c["kind"] == "raise"]))
    except Exception as exc:
        log.warning("Raises fetch failed: %s", exc)

    # TVL movers — cap at 3 items, raise threshold, set real age so they
    # don't always sort to the top (TVL data is not timestamped, use 1.5h)
    try:
        from bot.sources import defillama
        for m in defillama.fetch_tvl_movers(min_change_pct=20.0)[:3]:
            direction = "up" if m.change_pct > 0 else "down"
            candidates.append({
                "title": f"{m.name} TVL {direction} {abs(m.change_pct):.1f}%",
                "source": "DeFiLlama", "kind": "tvl", "topic": m.topic,
                "age_hours": 1.5, "url": m.url, "urgency": 1,
                # Store structured fields so the writer gets the actual numbers
                "tvl_name":       m.name,
                "tvl_change_pct": m.change_pct,
                "tvl_usd":        m.tvl_usd,
                "tvl_category":   m.category,
            })
        log.info("Scout: %d TVL movers", len([c for c in candidates if c["kind"] == "tvl"]))
    except Exception as exc:
        log.warning("TVL fetch failed: %s", exc)

    # Whale alerts
    if not alpha_only:
        try:
            whale_items = get_whale_alerts(lookback_minutes=90)
            if whale_items:
                log.info("Scout: %d whale alerts", len(whale_items))
            for w in whale_items:
                candidates.append({
                    "title":        w.summary(),
                    "source":       "Whale Alert",
                    "kind":         "whale",
                    "topic":        w.topic,
                    "age_hours":    round(w.age_hours, 2),
                    "url":          w.tx_hash,
                    "urgency":      2,
                    "whale_item":   w,
                })
        except Exception as exc:
            log.warning("Whale alert fetch failed: %s", exc)

    # Token unlocks
    if not alpha_only:
        try:
            unlock_items = get_upcoming_unlocks()
            if unlock_items:
                log.info("Scout: %d upcoming unlocks", len(unlock_items))
            for u in unlock_items:
                candidates.append({
                    "title":        u.summary(),
                    "source":       "DropsTab",
                    "kind":         "unlock",
                    "topic":        u.topic,
                    "age_hours":    round(u.age_hours, 2),
                    "url":          "",
                    "urgency":      2 if u.days_until <= 1 else 1,
                    "unlock_item":  u,
                })
        except Exception as exc:
            log.warning("DropsTab fetch failed: %s", exc)

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

    Selection is editorial, not just algorithmic. The question being answered
    is: "Is there something genuinely useful to say about this to our audience?"
    Items are scored on relevance to portfolio/watchlist, urgency, and freshness.
    Generic news with no posting reason is filtered at the writer stage.

    Returns None if nothing clears the bar.
    """
    recent_topics = state.recent_topics()
    portfolio = load_portfolio()

    # Things we're actively in or farming -- highest relevance
    held = {p["project"].lower() for p in portfolio.get("positions", []) if p.get("status") == "active"}
    held |= {a["project"].lower() for a in portfolio.get("airdrops", []) if a.get("status") == "farming"}

    # Things we're watching but not in -- secondary relevance
    watching = {w["project"].lower() for w in portfolio.get("watching", [])}

    from bot.config import POST_SCORE_THRESHOLD, MAX_TOPIC_REPEAT

    rejection_log = []
    scored = []

    for c in candidates[:25]:
        title     = c.get("title", "")
        topic     = c.get("topic", "") or ""
        age_hours = c.get("age_hours", 0)
        kind      = c.get("kind", "rss")
        title_lower = title.lower()

        # Hard rejection: stale
        if age_hours > 7:
            rejection_log.append("STALE (%.1fh): %s" % (age_hours, title[:50]))
            continue

        # Hard rejection: repeated topic.
        # "general" is the catch-all category (anything not matching a specific
        # keyword). Applying the repeat cap to it blocks the majority of RSS
        # content, so we exempt it entirely -- variety comes from the title
        # fingerprint deduplication instead.
        if topic and topic != "general":
            topic_count = recent_topics.count(topic)
            if topic_count >= MAX_TOPIC_REPEAT:
                rejection_log.append("TOPIC REPEAT (%dx): %s" % (topic_count, title[:50]))
                continue

        # Hard rejection: already seen
        fp = state.fingerprint(title_lower)
        if state.has_seen(fp):
            rejection_log.append("SEEN: %s" % title[:50])
            continue

        # Base score from scorer
        dummy = FeedItem(
            source=c.get("source", ""), title=title, url=c.get("url"),
            published_ts=time.time() - age_hours * 3600,
            topic=topic, kind=kind,
        )
        item_score = score_item(dummy)

        # Urgency bonus -- alpha signals that need fast action
        urgency = c.get("urgency", 1)
        if urgency >= 3:
            item_score += 25
        elif urgency >= 2:
            item_score += 10

        # Portfolio relevance bonus -- items about things our audience is
        # actively in or tracking. These always have a reason to post.
        portfolio_match = any(h in title_lower for h in held)
        watchlist_match = any(w in title_lower for w in watching) if watching else False

        if portfolio_match:
            item_score += 30   # We're in this -- definite posting reason
            log.debug("Portfolio match (+30): %s", title[:50])
        elif watchlist_match:
            item_score += 15   # We're watching this -- likely posting reason

        # Timing signal bonus -- things with specific deadlines
        timing_keywords = [
            "unlock", "tge", "snapshot", "deadline", "ends in", "closes",
            "airdrop criteria", "airdrop announced", "mainnet", "launch",
        ]
        if any(kw in title_lower for kw in timing_keywords):
            item_score += 12   # Time-sensitive = clear reason to post now

        # Contrarian signal bonus -- data that contradicts narratives
        contrarian_keywords = [
            "despite", "but", "however", "falls short", "below expectations",
            "exit", "outflow", "decline", "hack", "exploit", "rug",
        ]
        if any(kw in title_lower for kw in contrarian_keywords):
            item_score += 8    # Counter-narrative = useful to audience

        # TVL movers for unknown protocols aren't worth posting
        if kind == "tvl" and item_score < 50:
            rejection_log.append("TVL UNKNOWN PROTOCOL (%d): %s" % (item_score, title[:50]))
            continue

        # Source diversity: never post TVL/DeFiLlama back-to-back
        last_source = (state.recent_topics() or [""])[-1]
        last_fmt    = (state._data.get("recent_formats") or [""])[-1]
        if kind == "tvl" and last_fmt in ("data_observation",) and "defillama" in (c.get("source", "")).lower():
            rejection_log.append("SOURCE DIVERSITY (no back-to-back TVL): %s" % title[:50])
            continue

        # Score floor -- wide enough that bonuses (portfolio +30, watchlist +15,
        # timing +12) can lift worthy items. Raised from -15 to -25 because the
        # TVL penalty changes narrowed the effective range too much, causing
        # 3-6h old articles to score 42 and get rejected despite being relevant.
        if item_score < POST_SCORE_THRESHOLD - 25:
            rejection_log.append("LOW SCORE (%d): %s" % (item_score, title[:50]))
            continue

        # Disclosure flag
        needs_disclosure = portfolio_match
        c = dict(c)  # copy to avoid mutating original
        c["needs_disclosure"] = needs_disclosure
        c["held_project"] = next((h for h in held if h in title_lower), None)
        c["score"] = item_score
        scored.append((item_score, c))

    if rejection_log:
        log.info("Analyst rejections:\n  " + "\n  ".join(rejection_log[:10]))

    if not scored:
        log.info("Analyst: no candidate cleared the quality bar.")
        return None

    scored.sort(key=lambda x: -x[0])
    best = scored[0][1]
    log.info(
        "Analyst selected (score=%d, urgency=%d, portfolio=%s): %s",
        best["score"], best.get("urgency", 1),
        best.get("held_project") or "no",
        best["title"][:70],
    )
    return best


# ---------------------------------------------------------------------------
# Standalone opinion post -- no news trigger required
# ---------------------------------------------------------------------------

_OPINION_ONLY_FORMATS = ["hot_take", "prediction", "contrarian", "mistake_admission"]

_OPINION_SYSTEM = """You write standalone opinion tweets for @Qwinahh -- a crypto account that
trades perps, farms airdrops, and moves into DeFi protocols before
narratives form. The audience: active DeFi farmers, perp traders,
airdrop hunters.

These posts have NO news hook. They are:
  - Strong opinions about narratives the account is tracking
  - Predictions with a specific timeframe and testable outcome
  - Things the account got wrong and what changed the view
  - Observations about how the market is behaving RIGHT NOW
  - "Hot takes" that challenge conventional CT wisdom with data

LANGUAGE RULES (Quin's voice):
- No em-dashes, no "landscape", no "ecosystem", no "space", no "bullish on"
- No hashtags, no emojis, no "gm", no "ngmi", no "wen", no "alpha"
- Under 260 characters. One idea. Sound like a person, not a press release.
- Start with the opinion or prediction -- never with "I think" or "Just saw"
- Must contain "I", "my", or a direct opinion ("this is", "that means", "the issue is")

OUTPUT FORMAT:
Line 1: FORMAT: [hot_take / prediction / contrarian / mistake_admission]
Line 2: [the tweet text]

Or if nothing genuine to say:
SKIP
"""


def _maybe_standalone_opinion(state: State):
    """
    Generate and post a standalone opinion tweet if conditions are met.

    Fires at most twice per day, with a minimum 4h gap since the last
    opinion post. Uses persona + trending context as the only inputs --
    no news item required.

    Returns a result dict like run_post_cycle(), or None if not firing.
    """
    opinion_today = state._data.get("opinion_posts_today", 0)
    if opinion_today >= 2:
        return None

    last_opinion_ts = state._data.get("last_opinion_ts", 0)
    if time.time() - last_opinion_ts < 4 * 3600:
        return None

    from bot.config import MIN_HOURS_BETWEEN_POSTS, MAX_POSTS_PER_DAY
    if state.posts_today() >= MAX_POSTS_PER_DAY:
        return None
    last_post = state.last_post_timestamp()
    if last_post and (time.time() - last_post) < MIN_HOURS_BETWEEN_POSTS * 3600:
        return None

    log.info("Standalone opinion: conditions met (opinions today=%d/2)", opinion_today)

    try:
        from bot.brain.context import build_writer_context
        context_block = build_writer_context(topic="defi_opinion", title="standalone opinion post")
    except Exception as exc:
        log.warning("Opinion context build failed: %s", exc)
        context_block = ""

    import random
    fmt = random.choice(_OPINION_ONLY_FORMATS)

    user_prompt = (
        f"Write a {fmt.upper().replace('_', ' ')} post for @Qwinahh. "
        "This has no news hook -- it's a genuine opinion based on what you're "
        "seeing in DeFi/perps/airdrops right now.\n\n"
        "Draw from the context below to make it feel specific and timely:\n\n"
        + context_block[:2000]
        + "\n\nRemember: one strong opinion, under 260 characters, starts with the take."
    )

    from bot.brain.llm import complete as llm_complete
    from bot.config import CLAUDE_MAX_TOKENS
    try:
        raw = llm_complete(
            system=_OPINION_SYSTEM,
            user=user_prompt,
            max_tokens=CLAUDE_MAX_TOKENS,
            temperature=0.85,
        )
    except Exception as exc:
        log.warning("Opinion generation failed: %s", exc)
        return None

    if not raw:
        return None

    raw = raw.strip()
    if raw.upper().startswith("SKIP") or not raw:
        log.info("Opinion writer chose to SKIP this slot.")
        return None

    lines = raw.splitlines()
    tweet_text = ""
    detected_fmt = fmt
    for i, line in enumerate(lines):
        if line.upper().startswith("FORMAT:"):
            detected_fmt = line.split(":", 1)[1].strip().lower()
            remaining = "\n".join(lines[i+1:]).strip()
            if remaining:
                tweet_text = remaining
        elif not tweet_text and not line.upper().startswith("FORMAT:"):
            tweet_text = line.strip()

    if not tweet_text:
        tweet_text = raw.strip()

    if tweet_text.upper().startswith("FORMAT:"):
        tweet_text = "\n".join(tweet_text.splitlines()[1:]).strip()

    if len(tweet_text) < 20 or len(tweet_text) > 280:
        log.info("Opinion text invalid (len=%d): %s", len(tweet_text), tweet_text[:60])
        return None

    try:
        from bot.brain.authenticity_judge import passes as judge_passes
        ok, judge_result = judge_passes(tweet_text, content_type="tweet")
        if not ok:
            log.info("Opinion failed authenticity gate (score=%d): %s",
                     judge_result["score"], tweet_text[:60])
            return None
    except Exception as exc:
        log.debug("Opinion judge error: %s -- proceeding", exc)

    log.info("Posting standalone opinion (%s, %d chars): %s",
             detected_fmt, len(tweet_text), tweet_text[:80])
    tweet_id = post_tweet(tweet_text)
    if not tweet_id:
        log.error("Standalone opinion post_tweet() failed.")
        return None

    state.increment_post_count()
    state.set_last_post_timestamp(time.time())
    state.mark_seen(state.fingerprint(tweet_text.lower()))
    state.record_format(detected_fmt)
    state._data["opinion_posts_today"] = opinion_today + 1
    state._data["last_opinion_ts"] = time.time()
    state.save()

    result = {
        "action":      "posted",
        "tweet_id":    tweet_id,
        "tweet_text":  tweet_text,
        "reason":      "Standalone opinion post (%s)" % detected_fmt,
        "topic":       "opinion",
        "format_used": detected_fmt,
    }
    _post_success_hooks(state, result)
    log.info("Standalone opinion posted: %s", tweet_id)
    return result


# ---------------------------------------------------------------------------
# Market mood post -- fires when Fear & Greed swings sharply
# ---------------------------------------------------------------------------

_MOOD_SYSTEM = """You write market sentiment posts for @Qwinahh -- a crypto account that trades
perps, farms airdrops, and moves into DeFi protocols before narratives form.

You've been given a Fear & Greed index signal -- a sharp 24h swing or extreme
reading. Write a genuine reaction post that tells your audience what this means
for actual positioning, not just what the number is.

WHAT MAKES A GREAT MOOD POST:
  - Interprets the signal through the lens of someone actively trading
  - Gives a specific implication: "this means [X] for longs / for the funding rate"
  - References historical pattern if you have one: "last time F&G was here was [event]"
  - Doesn't state the obvious. Everyone can read the index.
  - Under 260 characters. No hashtags. No "the market is uncertain."

FORMATS:
  A. "F&G at [N] (extreme fear/greed). [what this means for your thesis]. [1 action]"
  B. "Sentiment just [moved] [N] points in 24h. [why this matters]. [what you're watching]"
  C. Contrarian: "crowd is [fearful/greedy] right now. historically this is when [counter-trade]"

OUTPUT: Just the tweet text. No preamble.
If no genuine take to add: SKIP
"""


def _maybe_market_mood_post(state: State):
    """
    Post a market mood reaction when Fear & Greed swings >15 pts in 24h
    or crosses into Extreme Fear/Extreme Greed territory.

    Max 1x/day, min 12h gap. Fires ~60% of the time when triggered.
    Returns result dict or None.
    """
    mood_today = state._data.get("mood_posts_today", 0)
    if mood_today >= 1:
        return None

    last_mood_ts = state._data.get("last_mood_ts", 0)
    if time.time() - last_mood_ts < 12 * 3600:
        return None

    from bot.config import MAX_POSTS_PER_DAY
    if state.posts_today() >= MAX_POSTS_PER_DAY:
        return None

    import random as _random
    if _random.random() > 0.60:
        return None

    try:
        from bot.sources.fear_greed import detect_mood_swing
        swing = detect_mood_swing()
    except Exception as exc:
        log.debug("Mood swing detection failed: %s", exc)
        return None

    if not swing:
        return None

    log.info("Market mood trigger: %s", swing["description"])

    try:
        from bot.brain.context import build_writer_context
        ctx = build_writer_context(topic="market_sentiment", title="market mood post")
    except Exception:
        ctx = ""

    user_prompt = (
        f"Fear & Greed signal:\n{swing['description']}\n\n"
        f"Delta: {swing['delta']:+d} points in 24h "
        f"({swing['yesterday']} -> {swing['today']})\n"
        f"Current: {swing['today']} ({swing['today_label']})\n\n"
        f"Additional market context:\n{ctx[:1500]}\n\n"
        "Write your market reaction post. Under 260 chars. "
        "Don't just restate the number -- give an implication or contrarian read."
    )

    from bot.brain.llm import complete as llm_complete
    from bot.config import CLAUDE_MAX_TOKENS
    try:
        raw = llm_complete(
            system=_MOOD_SYSTEM,
            user=user_prompt,
            max_tokens=CLAUDE_MAX_TOKENS,
            temperature=0.82,
        )
    except Exception as exc:
        log.warning("Mood post generation failed: %s", exc)
        return None

    if not raw:
        return None

    raw = raw.strip()
    if raw.upper().startswith("SKIP"):
        log.info("Mood writer chose SKIP.")
        return None

    tweet_text = raw.splitlines()[0].strip()
    if len(tweet_text) > 280:
        tweet_text = tweet_text[:277] + "..."

    try:
        from bot.brain.authenticity_judge import passes as judge_passes
        ok, _ = judge_passes(tweet_text, content_type="tweet")
        if not ok:
            log.info("Mood post failed authenticity gate: %s", tweet_text[:60])
            return None
    except Exception:
        pass

    tweet_id = post_tweet(tweet_text)
    if not tweet_id:
        log.error("Mood post_tweet() failed.")
        return None

    state.increment_post_count()
    state.set_last_post_timestamp(time.time())
    state.mark_seen(state.fingerprint(tweet_text.lower()))
    state._data["mood_posts_today"] = mood_today + 1
    state._data["last_mood_ts"] = time.time()
    state.save()

    result = {
        "action":      "posted",
        "tweet_id":    tweet_id,
        "tweet_text":  tweet_text,
        "reason":      "Market mood post (F&G swing: %s)" % swing["description"][:60],
        "topic":       "market_sentiment",
        "format_used": "market_read",
    }
    log.info("Market mood posted: %s -- %s", tweet_id, tweet_text[:80])
    return result


# ---------------------------------------------------------------------------
# Thread continuation -- posts 2-3 follow-up tweets after a thread_hook
# ---------------------------------------------------------------------------

def _post_thread_continuation(hook_id: str, hook_text: str, item, state: State) -> None:
    """
    After posting a thread_hook tweet, generate and post 2-3 continuation tweets
    as replies to form a complete thread. Non-fatal -- any failure is logged and swallowed.
    """
    try:
        from bot.brain.writer import generate_thread_continuation
        from bot.portfolio.tracker import load_portfolio
        portfolio = load_portfolio()
        continuations = generate_thread_continuation(hook_text, item, portfolio)
    except Exception as exc:
        log.warning("Thread continuation generation failed: %s", exc)
        return

    if not continuations:
        log.info("Thread continuation: no tweets generated.")
        return

    last_id = hook_id
    for i, cont_text in enumerate(continuations, start=2):
        try:
            cont_id = post_tweet(cont_text, reply_to_id=last_id)
            if cont_id:
                last_id = cont_id
                log.info("Thread part %d posted (%s): %s", i, cont_id, cont_text[:60])
            else:
                log.warning("Thread part %d post_tweet failed.", i)
                break
        except Exception as exc:
            log.warning("Thread part %d error: %s", i, exc)
            break


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
    # Step 0a: Market mood post -- fires on sharp F&G swings (max 1x/day)
    # Highest-priority proactive content: raw emotional market reads.
    # ------------------------------------------------------------------
    if not alpha_only:
        mood_result = _maybe_market_mood_post(state)
        if mood_result:
            return mood_result

    # ------------------------------------------------------------------
    # Step 0b: Standalone opinion check (~2x/day, no news hook required)
    # Fires ~30% of runs when eligible -- mixes reactive + proactive content.
    # ------------------------------------------------------------------
    import random as _random
    if not alpha_only and _random.random() < 0.30:
        opinion_result = _maybe_standalone_opinion(state)
        if opinion_result:
            return opinion_result

    # ------------------------------------------------------------------
    # Step 0c: Portfolio diary post -- fires when portfolio.json has content
    # Personal trade reality posts ("just sized into X because Y").
    # Max 1x/day, 8h gap. Source: data/portfolio.json
    # ------------------------------------------------------------------
    if not alpha_only:
        try:
            from bot.sources.portfolio_diary import maybe_diary_post
            diary_result = maybe_diary_post(state)
            if diary_result:
                return diary_result
        except Exception as exc:
            log.warning("Portfolio diary check failed: %s", exc)

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

    # Build a properly-typed item so the writer gets full structured data.
    # Raises and TVL movers have richer context (amounts, percentages) that
    # the generic FeedItem would strip out, causing the quality gate to reject
    # posts for being "too vague" even when the data is specific.
    kind = selected.get("kind", "rss")
    if kind == "raise" and selected.get("raise_name"):
        from bot.sources.defillama import RaiseItem
        item = RaiseItem(
            name         = selected["raise_name"],
            amount       = selected.get("raise_amount_m"),
            round_name   = selected.get("raise_round", ""),
            category     = selected.get("raise_category", selected.get("topic", "")),
            url          = selected.get("url"),
            published_ts = selected.get("raise_published",
                           time.time() - selected.get("age_hours", 0) * 3600),
            topic        = selected.get("topic", "raise"),
        )
    elif kind == "tvl" and selected.get("tvl_name"):
        from bot.sources.defillama import TvlMoverItem
        item = TvlMoverItem(
            name       = selected["tvl_name"],
            change_pct = selected["tvl_change_pct"],
            tvl_usd    = selected["tvl_usd"],
            category   = selected.get("tvl_category", selected.get("topic", "")),
            url        = selected.get("url"),
            topic      = selected.get("topic", "defi"),
        )
    elif kind == "whale" and selected.get("whale_item"):
        item = selected["whale_item"]
    elif kind == "unlock" and selected.get("unlock_item"):
        item = selected["unlock_item"]
    else:
        item = FeedItem(
            source       = selected.get("source", ""),
            title        = selected["title"],
            url          = selected.get("url"),
            published_ts = time.time() - selected.get("age_hours", 0) * 3600,
            topic        = selected.get("topic", ""),
            kind         = kind,
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

    # Fire thread continuation if this was a thread_hook format
    if fmt_name == "thread_hook":
        _post_thread_continuation(tweet_id, text, item, state)

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
         