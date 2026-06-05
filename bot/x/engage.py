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
import logging
import os
import tempfile
import time
from typing import Optional

from bot.brain.llm import complete as llm_complete
from bot.config import CLAUDE_MAX_TOKENS
from bot.state import State
from bot.x.client import get_mentions, post_tweet

log = logging.getLogger(__name__)

# Replies are limited to this many per engage run to avoid rate-limit issues.
MAX_REPLIES_PER_RUN = 5

# Thread continuations: cap per day, not per run, because they're high-value
# and we want to spread them across different posts rather than batch them.
MAX_THREAD_REPLIES_PER_DAY = 3

# Own username — used to look up our own tweets via twscrape.
_OWN_USERNAME = os.environ.get("X_USERNAME", "Qwinahh")

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
# Mention quality gate
# ---------------------------------------------------------------------------

_NICHE_KEYWORDS = {
    "defi", "crypto", "bitcoin", "eth", "ethereum", "btc", "sol", "solana",
    "perp", "futures", "trading", "airdrop", "yield", "farm", "protocol",
    "dex", "liquidity", "token", "nft", "web3", "blockchain", "dao",
    "staking", "lending", "vault", "hyperliquid", "arbitrum", "base",
    "optimism", "layer2", "l2", "tvl", "defillama", "kaito", "points",
    "alpha", "on-chain", "onchain", "wallet", "position", "long", "short",
}

_SPAM_SIGNALS = [
    "follow back", "followback", "follow4follow", "f4f",
    "giveaway", "free crypto", "dm me", "click here",
    "limited offer", "pump", "100x", "1000x", "moon guaranteed",
]


def _is_niche_mention(mention: dict) -> bool:
    """
    Return True if the mention is worth replying to.
    Rejects mass-tag spam, non-crypto accounts, and obvious bots.
    """
    text      = mention.get("text", "")
    username  = mention.get("author_username", "").lower()
    followers = mention.get("author_followers", 0) or 0

    if text.count("@") > 4:
        log.debug("Rejecting mention from @%s: mass-tag (%d @s)", username, text.count("@"))
        return False

    if followers < 10:
        log.debug("Rejecting mention from @%s: too few followers (%d)", username, followers)
        return False

    lower_text = text.lower()
    if any(s in lower_text for s in _SPAM_SIGNALS):
        log.debug("Rejecting mention from @%s: spam signal detected", username)
        return False

    return True


# ---------------------------------------------------------------------------
# Mention reply helpers
# ---------------------------------------------------------------------------

def _parse_mention_reply(raw: str) -> Optional[str]:
    """Parse structured REPLY:/SKIP: response from LLM."""
    if not raw:
        return None
    raw = raw.strip()

    if raw.upper().startswith("REPLY:"):
        text = raw[6:].strip()
        if len(text) < 10:
            return None
        log.debug("Parsed REPLY: prefix from mention reply.")
        return text

    if raw.upper().startswith("SKIP"):
        log.debug("Skipping reply (model decided not to respond).")
        return None

    # Fallback: treat unstructured output as a reply if it looks like one
    if len(raw) <= 280 and not any(
        raw.lower().startswith(w) for w in ["i'll skip", "skipping", "not worth", "no value"]
    ):
        return raw if len(raw) >= 10 else None

    return None


def _generate_reply(mention_text: str) -> Optional[str]:
    prompt = (
        f"Mention received:\n\n{mention_text}\n\n"
        "Write a reply that adds something specific. "
        "Use the REPLY:/SKIP: format from the system prompt."
    )
    raw = llm_complete(system=_REPLY_SYSTEM, user=prompt, max_tokens=CLAUDE_MAX_TOKENS, temperature=0.7)
    reply = _parse_mention_reply(raw)
    if reply and len(reply) > 280:
        reply = reply[:276].rsplit(".", 1)[0] + "."
    return reply


def run(state: State) -> int:
    """
    Check for new mentions and reply to them.

    Returns the number of replies sent.
    """
    since_id = state._data.get("last_mention_id")
    mentions  = get_mentions(since_id=since_id)

    if not mentions:
        log.info("No new mentions.")
        return 0

    # Update the cursor so we don't re-process old mentions.
    newest_id = max(m["id"] for m in mentions)
    state._data["last_mention_id"] = newest_id

    already_replied = state.last_replied_to()
    replies_sent    = 0

    for mention in mentions:
        if replies_sent >= MAX_REPLIES_PER_RUN:
            break

        tweet_id = mention["id"]
        if tweet_id in already_replied:
            continue

        if not _is_niche_mention(mention):
            state.mark_replied(tweet_id)  # Mark seen so we don't retry
            continue

        reply_text = _generate_reply(mention["text"])
        if not reply_text:
            continue

        sent_id = post_tweet(reply_text, reply_to_id=tweet_id)
        if sent_id:
            state.mark_replied(tweet_id)
            replies_sent += 1
            log.info("Replied to %s: %s", tweet_id, reply_text[:60])

    return replies_sent
