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
    Fetch high-engagement crypto posts suitable for quote-tweeting via twscrape.

    Returns posts with >_QT_LIKES_MIN_HARD likes from the last 24h, sorted by
    engagement descending.
    """
    cookies = os.environ.get("X_SCRAPER_COOKIES", "").strip()
    if not cookies:
        return []

    try:
        from twscrape import API
    except ImportError:
        log.debug("twscrape not installed — quote tweet candidate fetch skipped.")
        return []

    api = API(os.path.join(tempfile.gettempdir(), "twscrape_pool.db"))
    try:
        await api.pool.add_account(
            username="beacon_qt_scraper",
            password="placeholder",
            email="placeholder@placeholder.com",
            email_password="placeholder",
            cookies=cookies,
        )
    except Exception as exc:
        log.debug("twscrape setup error (qt): %s", exc)
        return []

    results: list[dict] = []
    now = time.time()
    cutoff_24h = now - 86_400  # 24 hour window — QTs don't need to be fresh

    for query in _QT_KEYWORD_QUERIES:
        try:
            async for tweet in api.search(
                f"{query} -is:retweet",
                limit=20,
                kv={"product": "Top"},  # Top posts, not Latest, for high engagement
            ):
                ts = getattr(tweet, "date", None)
                if ts and ts.timestamp() < cutoff_24h:
                    continue

                content = tweet.rawContent or ""
                if content.startswith("RT @"):
                    continue

                likes    = getattr(tweet, "likeCount", 0) or 0
                retweets = getattr(tweet, "retweetCount", 0) or 0

                if likes < _QT_LIKES_MIN_HARD:
                    continue

                author = tweet.user.username if tweet.user else "unknown"
                # Skip our own posts — no value in quote-tweeting yourself
                if author.lower() == _OWN_USERNAME.lower():
                    continue

                results.append({
                    "id":       str(tweet.id),
                    "text":     content,
                    "author":   author,
                    "likes":    likes,
                    "replies":  getattr(tweet, "replyCount", 0) or 0,
                    "retweets": retweets,
                    "url":      f"https://x.com/{author}/status/{tweet.id}",
                })
        except Exception as exc:
            log.debug("QT keyword search error for '%s': %s", query, exc)

    # Deduplicate by tweet ID and sort by engagement
    seen_ids: set[str] = set()
    unique = []
    for post in results:
        if post["id"] not in seen_ids:
            seen_ids.add(post["id"])
            unique.append(post)

    unique.sort(key=lambda p: p["likes"] + p["retweets"] * 2, reverse=True)
    return unique


def _quote_tweet_with_take(post_data: dict) -> Optional[str]:
    """
    Generate a quote-tweet commentary for a high-engagement post.

    Returns the commentary text (under 180 chars) or None if rejected.
    post_data must have: id, text, author, likes. Requires likes > _QT_LIKES_MIN_SOFT.
    """
    if post_data.get("likes", 0) < _QT_LIKES_MIN_SOFT:
        return None

    prompt = (
        f"Tweet by @{post_data['author']}:\n\n{post_data['text']}\n\n"
        "Write a quote-tweet take that adds something specific. "
        "Use the TAKE:/SKIP: format from the system prompt."
    )
    raw = llm_complete(
        system=_QUOTE_TWEET_SYSTEM,
        user=prompt,
        max_tokens=220,
        temperature=0.78,
    )
    if not raw:
        return None

    raw = raw.strip()
    if raw.upper().startswith("TAKE:"):
        text = raw[5:].strip()
    elif raw.upper().startswith("SKIP"):
        log.debug("QT take skipped by model for @%s post.", post_data.get("author"))
        return None
    else:
        text = raw  # unstructured fallback

    if not text or len(text) < 20:
        return None

    if len(text) > 180:
        text = text[:177].rsplit(".", 1)[0] + "."

    from bot.brain.authenticity_judge import passes as judge_passes
    ok, result = judge_passes(text, content_type="reply")
    if not ok:
        log.debug(
            "QT take failed authenticity (score=%d) — skipping: %s",
            result["score"], text[:60],
        )
        return None

    return text


def run_quote_tweet(state: State) -> int:
    """
    Find one high-engagement crypto post and quote-tweet it with a specific take.

    Gated by QUOTE_TWEET_COOLDOWN_HOURS (6h). Only posts with >100 likes qualify.
    Tracks posted quote tweet IDs in state to avoid repeating.

    Returns 1 if a quote tweet was posted, 0 otherwise.
    """
    now = time.time()

    # Cooldown check
    elapsed_h = (now - state.last_quote_tweet_ts()) / 3600
    if elapsed_h < QUOTE_TWEET_COOLDOWN_HOURS:
        log.debug(
            "Quote tweet cooldown: %.1fh elapsed, %.1fh required.",
            elapsed_h, QUOTE_TWEET_COOLDOWN_HOURS,
        )
        return 0

    cookies = os.environ.get("X_SCRAPER_COOKIES", "").strip()
    if not cookies:
        log.debug("X_SCRAPER_COOKIES not set — quote tweet skipped.")
        return 0

    candidates = _run_async_engage(_fetch_quote_candidates_async()) or []
    if not candidates:
        log.info("No quote tweet candidates found this run.")
        return 0

    # Pick the first candidate that hasn't been quote-tweeted yet
    for post in candidates:
        tweet_id = post["id"]
        if state.already_quote_tweeted(tweet_id):
            continue

        take = _quote_tweet_with_take(post)
        if not take:
            # Mark as seen so we don't retry the same post next run
            state.mark_quote_tweeted(tweet_id)
            log.debug("No viable take for @%s post %s — marking seen.", post["author"], tweet_id)
            continue

        sent_id = quote_tweet(take, quote_tweet_id=tweet_id)
        if sent_id:
            state.mark_quote_tweeted(tweet_id)
            state.set_last_quote_tweet_ts(now)
            log.info(
                "Quote-tweeted @%s (%d likes) → %s: %s",
                post["author"], post["likes"], sent_id, take[:70],
            )
            return 1

    log.info("Quote tweet: no viable candidate passed quality gate this run.")
    return 0


# ---------------------------------------------------------------------------
# Replies to own-post mentions
# ---------------------------------------------------------------------------

# Hard cap per engage run — we reply to inbound engagement, but don't flood.
MAX_MENTION_REPLIES_PER_RUN = 3

# Hours before we'll reply to the same author again for this feature.
# Different from the outbound reply cooldown — this is inbound conversation.
_MENTION_REPLY_COOLDOWN_HOURS = 12

_MENTION_REPLY_SYSTEM = """\
You write replies for @Qwinahh responding to people who replied to one of their tweets.
@Qwinahh trades perps, farms airdrops, and moves into DeFi protocols early.

Context: Someone replied to a post @Qwinahh made. Write @Qwinahh's response to keep
the conversation going.

RULES:
- Under 160 characters. One exchange, not an essay.
- Be genuine and conversational. Engage with their actual point — add to it,
  push back with data, or ask something specific.
- Never say "thanks for engaging", "great question", "appreciate the reply",
  or anything that sounds like customer service or PR copy.
- If they're pushing back: engage with the substance, not the emotion.
- If they're agreeing without adding anything: add one more layer yourself.
- No hashtags. No emojis. Sound like a real person mid-conversation.
- If the reply is low-effort ("wen token", "price?", "gm", "ser", "ngmi"):
  respond with SKIP.

OUTPUT FORMAT — respond with exactly one of:
  REPLY: [your reply under 160 chars]
  SKIP: [one-word reason: low_effort/spam/price_ask/hostile/no_value]
"""


async def _fetch_replies_to_own_posts_async() -> list[dict]:
    """
    Fetch recent replies to @Qwinahh's own posts via twscrape.

    Step 1: build a set of our own tweet IDs from the last 48h (all tweets,
            not just high-engagement ones — any post can receive replies).
    Step 2: search for @Qwinahh mentions, return only those whose
            inReplyToTweetId matches one of our own tweet IDs.
    """
    cookies = os.environ.get("X_SCRAPER_COOKIES", "").strip()
    if not cookies:
        return []

    try:
        from twscrape import API
    except ImportError:
        log.debug("twscrape not installed — post-reply fetch skipped.")
        return []

    api = API(os.path.join(tempfile.gettempdir(), "twscrape_pool.db"))
    try:
        await api.pool.add_account(
            username="beacon_post_reply_scraper",
            password="placeholder",
            email="placeholder@placeholder.com",
            email_password="placeholder",
            cookies=cookies,
        )
    except Exception as exc:
        log.debug("twscrape setup error (post reply): %s", exc)
        return []

    now = time.time()

    # Step 1 — own tweet IDs from last 48h (tweets we could receive replies to)
    own_tweets: dict[str, str] = {}  # tweet_id -> tweet_text
    try:
        user = await api.user_by_login(_OWN_USERNAME)
        if not user:
            log.debug("Could not resolve @%s for post-reply fetch.", _OWN_USERNAME)
            return []
        async for tweet in api.user_tweets(user.id, limit=50):
            ts = getattr(tweet, "date", None)
            if ts and ts.timestamp() < now - 172_800:  # 48h cutoff; newest-first → safe to break
                break
            content = tweet.rawContent or ""
            if not content.startswith("RT @"):
                own_tweets[str(tweet.id)] = content
    except Exception as exc:
        log.debug("Own tweet fetch (post-reply): %s", exc)

    if not own_tweets:
        log.debug("No own tweets in last 48h — skipping post-reply fetch.")
        return []

    # Step 2 — search mentions, keep only direct replies to our posts
    results: list[dict] = []
    try:
        query = f"@{_OWN_USERNAME} -from:{_OWN_USERNAME} lang:en"
        async for tweet in api.search(query, limit=50, kv={"product": "Latest"}):
            ts = getattr(tweet, "date", None)
            if ts and ts.timestamp() < now - 86_400:
                continue  # Skip mentions older than 24h; don't break (search not time-sorted)

            in_reply_to = str(getattr(tweet, "inReplyToTweetId", "") or "")
            if in_reply_to not in own_tweets:
                continue  # Not a reply to one of our posts

            content = tweet.rawContent or ""
            author = tweet.user.username if tweet.user else ""
            if not author or author.lower() == _OWN_USERNAME.lower():
                continue  # Skip our own replies

            results.append({
                "id":          str(tweet.id),
                "text":        content,
                "author":      author,
                "parent_id":   in_reply_to,
                "parent_text": own_tweets[in_reply_to],
            })
    except Exception as exc:
        log.debug("Post-reply mention search error: %s", exc)

    return results


def _generate_mention_reply(
    original_text: str,
    reply_text: str,
    author: str,
) -> Optional[str]:
    prompt = (
        f"Your original tweet:\n\n{original_text}\n\n"
        f"Reply from @{author}:\n\n{reply_text}\n\n"
        "Write a response. Use the REPLY:/SKIP: format from the system prompt."
    )
    raw = llm_complete(
        system=_MENTION_REPLY_SYSTEM,
        user=prompt,
        max_tokens=200,
        temperature=0.72,
    )
    if not raw:
        return None

    raw = raw.strip()
    if raw.upper().startswith("REPLY:"):
        text = raw[6:].strip()
    elif raw.upper().startswith("SKIP"):
        log.debug("Mention reply skipped by model for @%s.", author)
        return None
    else:
        text = raw  # unstructured fallback

    if not text or len(text) < 10:
        return None

    if len(text) > 160:
        text = text[:157].rsplit(".", 1)[0] + "."

    from bot.brain.authenticity_judge import passes as judge_passes
    ok, result = judge_passes(text, content_type="reply")
    if not ok:
        log.debug(
            "Mention reply failed authenticity (score=%d) — skipping",
            result["score"],
        )
        return None

    return text


def reply_to_own_mentions(state: State) -> int:
    """
    Reply to people who replied directly to one of the bot's own posts.

    Gated at MAX_MENTION_REPLIES_PER_RUN (3) per run.
    Per-author cooldown of _MENTION_REPLY_COOLDOWN_HOURS (12h) tracked under
    state "replied_to_mentions" dict: {username_lower: last_replied_timestamp}.

    Returns number of replies sent.
    """
    mentions = _run_async_engage(_fetch_replies_to_own_posts_async()) or []
    if not mentions:
        log.debug("No replies to own posts found this run.")
        return 0

    # Per-author cooldown dict — keyed by lowercase username, value is last reply ts
    replied_ts: dict[str, float] = state._data.setdefault("replied_to_mentions", {})

    # Prune entries older than 24h to prevent unbounded growth
    now = time.time()
    stale = [u for u, ts in replied_ts.items() if ts < now - 86_400]
    for u in stale:
        del replied_ts[u]

    already_replied = state.last_replied_to()
    sent = 0

    for mention in mentions:
        if sent >= MAX_MENTION_REPLIES_PER_RUN:
            break

        tweet_id = mention["id"]
        if tweet_id in already_replied:
            continue

        author_lower = mention["author"].lower()

        # Skip spam
        if any(s in mention["text"].lower() for s in _SPAM_SIGNALS):
            log.debug("Skipping post-reply from @%s: spam signal.", author_lower)
            continue

        # 12h per-author cooldown
        if now - replied_ts.get(author_lower, 0) < _MENTION_REPLY_COOLDOWN_HOURS * 3600:
            log.debug("Author @%s in cooldown — skipping.", author_lower)
            continue

        reply_text = _generate_mention_reply(
            original_text=mention["parent_text"],
            reply_text=mention["text"],
            author=mention["author"],
        )
        if not reply_text:
            continue

        sent_id = post_tweet(reply_text, reply_to_id=tweet_id)
        if sent_id:
            state.mark_replied(tweet_id)
            replied_ts[author_lower] = now
            sent += 1
            log.info(
                "Replied to @%s's reply on post %s → %s: %s",
                mention["author"], mention["parent_id"], sent_id, reply_text[:60],
            )

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
    if reply:
        from bot.brain.authenticity_judge import passes as judge_passes
        ok, result = judge_passes(reply, content_type="reply")
        if not ok:
            log.debug("Reply failed authenticity check (score=%d) — skipping", result["score"])
            return None
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
