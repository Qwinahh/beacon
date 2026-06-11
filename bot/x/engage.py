"""
Engagement module — handles replies to mentions and own-thread continuations.

Two modes:
  1. Mention replies: @Qwinahh is mentioned → generate a genuine response.
  2. Thread continuations: add a follow-up to our own recent high-engagement
     posts → the algorithm weights "author continues their thread" at one of
     the highest signal values available (signals quality content worth
     distributing further).

Reading own tweets uses twscrape (cookie-based, free).
Writing uses official X API (Tweepy, Free tier).
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

from bot.brain.llm import complete as llm_complete
from bot.config import BOT_USERNAME, CLAUDE_MAX_TOKENS, QUOTE_TWEET_COOLDOWN_HOURS
from bot.state import State
from bot.x.client import get_mentions, post_tweet, quote_tweet

log = logging.getLogger(__name__)

# Replies are limited to this many per engage run to avoid rate-limit issues.
MAX_REPLIES_PER_RUN = 5

# Thread continuations: cap per day, not per run, because they're high-value
# and we want to spread them across different posts rather than batch them.
MAX_THREAD_REPLIES_PER_DAY = 3

# Own username — sourced from config so it's consistent across all modules.
_OWN_USERNAME = BOT_USERNAME

# Only thread on posts from this window (hours) that have engagement.
# 12h catches morning posts when the evening engage run fires.
_THREAD_WINDOW_HOURS = 12

_THREAD_SYSTEM = """\
You write follow-up additions to @Qwinahh's own tweets.
@Qwinahh trades perps, farms airdrops, and moves into DeFi protocols early.

THE GOAL: Add a second observation that deepens the original post.
This rewards readers who liked the first one. It also triggers the X algorithm's
"author continues their thread" signal -- one of the highest-value quality signals
available, worth far more than any number of likes or retweets.

RULES:
- Under 220 characters. One new data point or implication only.
- Must add something NOT in the original tweet: a consequence, a comparison,
  a number, a historical parallel, or a next step to watch.
- Do not repeat or restate the original. Go one layer deeper.
- No hashtags. No emojis. No "as I said" or references back to the original.
  Sound like a person thinking out loud, not writing a thread.
- If you cannot genuinely add anything new: respond with exactly SKIP.

EXAMPLE:
Original: "Hyperliquid OI up 40% to $4.2B. HLP utilisation still at 34%."
Follow-up: "That gap means market makers are sitting out. If utilisation closes
fast, expect spreads to tighten and more volatile fills for the next few days."
"""

_REPLY_SYSTEM = """\
You write short, genuine replies for @Qwinahh — a crypto commentary account on X.

Rules:
- Be direct and add something specific. No filler, no "great point", no agreement without substance.
- Max 240 characters.
- No price predictions. No hashtags. Sound like a person, not a bot.
- If you have a position in the mentioned project, end with (position disclosed).

OUTPUT FORMAT — respond with exactly one of:
  REPLY: [your reply text under 240 chars]
  SKIP: [one-word reason: hostile/spam/vague/no_value]

Never output anything else. No explanation before REPLY/SKIP.
"""


# ---------------------------------------------------------------------------
# Post metrics collection
# ---------------------------------------------------------------------------

_METRICS_PATH = Path("data/growth/metrics.json")
_MAX_METRIC_FETCHES_PER_RUN = 10


def _load_metrics_file() -> dict:
    if not _METRICS_PATH.exists():
        return {}
    try:
        data = json.loads(_METRICS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_metrics_file(metrics: dict) -> None:
    _METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def update_post_metrics(state: State) -> int:
    """
    Fetch engagement metrics for recently posted tweets via the official X API.

    Reads the state posts list, filters for posts between 2h and 48h old that
    are not already in data/growth/metrics.json, fetches up to 10 per run to
    stay inside the Free tier rate limits, and writes results to metrics.json
    so format_weights.py can bias the writer toward high-performing formats.

    Returns number of tweets updated.
    """
    from bot.x.client import fetch_tweet_metrics

    candidates = state.posts(min_age_h=2.0, max_age_h=48.0)
    if not candidates:
        log.debug("update_post_metrics: no posts in 2–48h window.")
        return 0

    metrics = _load_metrics_file()
    to_fetch = [p for p in candidates if p["tweet_id"] not in metrics]
    to_fetch = to_fetch[:_MAX_METRIC_FETCHES_PER_RUN]

    if not to_fetch:
        log.debug("update_post_metrics: all eligible posts already in metrics.json.")
        return 0

    updated = 0
    for post in to_fetch:
        tweet_id = post["tweet_id"]
        m = fetch_tweet_metrics(tweet_id)
        if m is None:
            log.debug("update_post_metrics: no metrics returned for %s.", tweet_id)
            continue
        metrics[tweet_id] = {
            "format":      post.get("format", "unknown"),
            "topic":       post.get("topic", ""),
            "likes":       m["likes"],
            "replies":     m["replies"],
            "retweets":    m["retweets"],
            "impressions": m["impressions"],
            "posted_at":   post.get("posted_at", 0),
        }
        updated += 1
        log.info(
            "Metrics for %s [%s] — likes:%d replies:%d rt:%d impressions:%d",
            tweet_id, post.get("format", "?"),
            m["likes"], m["replies"], m["retweets"], m["impressions"],
        )

    if updated:
        _save_metrics_file(metrics)
        log.info("update_post_metrics: stored metrics for %d tweet(s).", updated)

    return updated


# ---------------------------------------------------------------------------
# Own-thread continuation helpers
# ---------------------------------------------------------------------------

def _run_async_engage(coro):
    """Run an async coroutine from sync code, handling existing event loops."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result(timeout=60)
        else:
            return loop.run_until_complete(coro)
    except Exception as exc:
        log.warning("Async runner error (engage): %s", exc)
        return None


async def _fetch_own_recent_tweets_async() -> list[dict]:
    """
    Fetch our own recent tweets that got some engagement via twscrape.

    Only returns tweets from the last _THREAD_WINDOW_HOURS hours that have
    at least 3 likes OR 1 reply -- we only thread on posts that landed.
    """
    cookies = os.environ.get("X_SCRAPER_COOKIES", "").strip()
    if not cookies:
        return []

    try:
        from twscrape import API
    except ImportError:
        log.debug("twscrape not installed -- thread reply fetch skipped.")
        return []

    api = API(os.path.join(tempfile.gettempdir(), "twscrape_pool.db"))
    try:
        await api.pool.add_account(
            username="beacon_thread_scraper",
            password="placeholder",
            email="placeholder@placeholder.com",
            email_password="placeholder",
            cookies=cookies,
        )
    except Exception as exc:
        log.warning("X_SCRAPER_COOKIES missing or expired — refresh in GitHub Secrets")
        log.debug("twscrape setup error (thread): %s", exc)
        return []

    results: list[dict] = []
    now = time.time()
    cutoff = now - (_THREAD_WINDOW_HOURS * 3600)

    try:
        user = await api.user_by_login(_OWN_USERNAME)
        if not user:
            log.debug("Could not resolve @%s via twscrape.", _OWN_USERNAME)
            return []

        async for tweet in api.user_tweets(user.id, limit=30):
            ts = getattr(tweet, "date", None)
            if not ts:
                continue
            tweet_time = ts.timestamp()
            if tweet_time < cutoff:
                break  # Tweets are newest-first; stop once past the window

            content = tweet.rawContent or ""
            # Skip retweets and replies to other people's tweets
            if content.startswith("RT @"):
                continue
            in_reply_to = getattr(tweet, "inReplyToTweetId", None)
            if in_reply_to and str(in_reply_to) != str(tweet.id):
                # This is a reply to someone else, not a standalone post
                continue

            likes   = getattr(tweet, "likeCount",  0) or 0
            replies = getattr(tweet, "replyCount", 0) or 0

            if likes >= 3 or replies >= 1:
                results.append({
                    "id":        str(tweet.id),
                    "text":      content,
                    "likes":     likes,
                    "replies":   replies,
                    "age_hours": (now - tweet_time) / 3600,
                })

    except Exception as exc:
        log.debug("Own tweet fetch error: %s", exc)

    return results


def _generate_thread_reply(original_text: str) -> Optional[str]:
    prompt = (
        f"Your original tweet:\n\n{original_text}\n\n"
        "Add a follow-up observation that deepens this — one layer further — "
        "or respond with exactly SKIP if there is nothing genuinely new to add."
    )
    reply = llm_complete(
        system=_THREAD_SYSTEM,
        user=prompt,
        max_tokens=CLAUDE_MAX_TOKENS,
        temperature=0.75,
    )
    if not reply:
        return None
    reply = reply.strip()
    if reply.upper().startswith("SKIP") or len(reply) < 20:
        return None
    if len(reply) > 280:
        reply = reply[:276].rsplit(".", 1)[0] + "."
    return reply


def run_own_thread_replies(state: State) -> int:
    """
    Post follow-up observations on our own recent high-engagement tweets.

    X's algorithm weights "author continues their thread" as one of the
    highest-quality signals -- it tells the system the post is worth
    distributing further. This is higher-ROI than almost any other action.

    Returns number of thread replies posted.
    """
    # Daily cap tracking
    today = time.strftime("%Y-%m-%d")
    thread_daily = state._data.setdefault("thread_replies_daily", {})
    count_today  = thread_daily.get(today, 0)

    # Clean up old date keys
    for old_date in [k for k in thread_daily if k < today]:
        del thread_daily[old_date]

    if count_today >= MAX_THREAD_REPLIES_PER_DAY:
        log.debug(
            "Thread reply daily cap reached (%d/%d).",
            count_today, MAX_THREAD_REPLIES_PER_DAY,
        )
        return 0

    # Fetch own recent tweets with engagement
    own_tweets = _run_async_engage(_fetch_own_recent_tweets_async()) or []
    if not own_tweets:
        log.debug("No own tweets with engagement in last %dh.", _THREAD_WINDOW_HOURS)
        return 0

    # Track which tweet IDs we've already threaded on (avoid double-threading)
    already_threaded = set(state._data.get("threaded_tweet_ids", []))

    # Sort by engagement score (replies weighted higher -- they indicate real interest)
    own_tweets.sort(
        key=lambda t: t["replies"] * 3 + t["likes"],
        reverse=True,
    )

    sent = 0
    for tweet in own_tweets:
        if count_today + sent >= MAX_THREAD_REPLIES_PER_DAY:
            break

        tweet_id = tweet["id"]
        if tweet_id in already_threaded:
            continue

        thread_text = _generate_thread_reply(tweet["text"])
        if not thread_text:
            log.debug("No thread addition generated for tweet %s.", tweet_id)
            already_threaded.add(tweet_id)  # Don't retry this tweet
            continue

        sent_id = post_tweet(thread_text, reply_to_id=tweet_id)
        if sent_id:
            already_threaded.add(tweet_id)
            sent += 1
            count_today += 1
            log.info(
                "Thread reply on %s (likes:%d replies:%d age:%.1fh): %s",
                tweet_id, tweet["likes"], tweet["replies"],
                tweet["age_hours"], thread_text[:70],
            )
            break  # One thread reply per run cycle -- spread them out

    # Persist state
    state._data["threaded_tweet_ids"] = list(already_threaded)[-200:]
    thread_daily[today] = count_today
    return sent


# ---------------------------------------------------------------------------
# Quote tweet
# ---------------------------------------------------------------------------

# Minimum likes for a post to be considered worth quote-tweeting.
_QT_LIKES_MIN_SOFT = 50    # required for _quote_tweet_with_take() to proceed
_QT_LIKES_MIN_HARD = 100   # required for run_quote_tweet() candidate selection

# Keyword queries for finding quote-tweet candidates. Higher min_faves than
# trend.py because we want established engagement, not just freshness.
_QT_KEYWORD_QUERIES = [
    "hyperliquid defi lang:en min_faves:100",
    "airdrop points farm defi lang:en min_faves:80",
    "defillama tvl protocol lang:en min_faves:100",
    "perp dex funding rate crypto lang:en min_faves:100",
    "solana defi yield lang:en min_faves:150",
]

_QUOTE_TWEET_SYSTEM = """\
You write quote-tweet commentary for @Qwinahh — a crypto account that trades perps,
farms airdrops, and moves into DeFi protocols before narratives form.

A quote tweet is NOT amplification. It is you adding your own specific take that
the reader wouldn't have gotten from the original alone.

RULES:
- Under 180 characters. One observation only. One sentence is fine.
- Must ADD something the original didn't say: a mechanism it missed, a counterpoint
  with data, a specific consequence, a direct implication for someone farming/trading this.
- Do NOT praise or agree without substance. Do NOT say "great take", "this", or "exactly".
- Do NOT summarize what the original said — the reader can see it.
- No hashtags. No emojis. Sound like someone with real skin in the game.
- If you hold a relevant position, end with (position disclosed).
- If you cannot add something genuinely new and specific: respond with exactly SKIP.

OUTPUT FORMAT — respond with exactly one of:
  TAKE: [your commentary under 180 chars]
  SKIP: [one-word reason: vague/no_value/agree_only/price_only]

Examples:
  TAKE: That TVL is almost entirely protocol-owned liquidity. Strip it and organic demand is half what the headline shows.
  TAKE: Seen this. The farm math breaks when points end. Check what happened to the previous cohort before sizing in.
  SKIP: price_only
"""


async def _fetch_quote_candidates_async() -> list[dict]:
    """
    Fetch high-engagement crypto p