"""
bot/x/trend.py — Proactive outbound engagement.

Two modes:
  1. TARGETED ACCOUNT MONITORING — watches a curated list of high-value DeFi/perps
     accounts and replies to their recent posts when we can add something specific.
     These are the accounts @Qwinahh should be visible alongside in followers' feeds.

  2. KEYWORD SEARCH — finds trending conversations around focus topics and adds
     genuine commentary. Catches posts from accounts not on the watchlist.

Both modes enforce strict quality gates:
  - Must add a specific data point, not just agree
  - Only posts from the last 3 hours (recency advantage in notifications)
  - Max 4 engagements per run total (3 targeted + 1 keyword)
  - Never replies to the same post twice
  - Skips if quality gate says SKIP

Requires X API Basic tier for search. Fails silently on free tier.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

import tweepy

from bot.brain.llm import complete as llm_complete
from bot.config import CLAUDE_MAX_TOKENS, FOCUS_KEYWORDS
from bot.portfolio.tracker import load_portfolio
from bot.state import State
from bot.x.client import get_client, post_tweet

log = logging.getLogger(__name__)

MAX_TARGETED_ENGAGEMENTS = 3
MAX_KEYWORD_ENGAGEMENTS  = 1
MAX_TOTAL_PER_RUN        = 4

# ---------------------------------------------------------------------------
# Curated high-value accounts to monitor and engage with.
#
# Selection criteria:
#   - Active in DeFi, perps, airdrops, or on-chain alpha
#   - Engaged audience (replies tend to get seen by relevant people)
#   - Post content @Qwinahh has a genuine angle on
#   - Mix of sizes: some peers (5k-30k), some larger (50k-300k)
#
# These are NOT accounts to spam. Only engage when you can add something real.
# Update this list in data/growth/target_accounts.json to customise without
# touching code.
# ---------------------------------------------------------------------------

_DEFAULT_TARGET_ACCOUNTS = [
    # Perps / Hyperliquid ecosystem
    "ilmoi",
    "HsakaTrades",
    "CryptoHayes",

    # DeFi / TVL / yield farming
    "DefiIgnas",
    "Founderization",
    "0xHamz",
    "Croissant_eth",
    "0xMaki",

    # Airdrop / points meta
    "Pentosh1",
    "zkDrops",

    # On-chain data / research
    "tomhschmidt",
    "hasufl",
    "0xShitposter",

    # Narrative / cycle analysis
    "MessariCrypto",
    "delphi_digital",
]

# Keyword-based search queries for catch-all engagement.
_KEYWORD_QUERIES = [
    "hyperliquid funding rate -is:retweet lang:en",
    "defi points airdrop farm -is:retweet lang:en",
    "kaito yap leaderboard -is:retweet lang:en",
    "perp dex liquidity -is:retweet lang:en min_faves:30",
]

_REPLY_SYSTEM = """\
You write outbound replies for @Qwinahh — a crypto account that trades perps,
farms airdrops, and moves into DeFi protocols before narratives form.

The reply MUST:
- Add something the original tweet didn't say: a specific number, a counterpoint,
  a sharper angle, a historical parallel, or a mechanic the author didn't mention.
- Be under 230 characters.
- Sound like a person who actually follows this closely — not a summariser.
- NOT open with "Great point", "Totally agree", "Interesting", or any affirmation.
- NOT make price predictions. No hashtags.
- If you hold a position in the mentioned project: end with (position disclosed).
- If the tweet is low quality, price-only, hostile, or there's nothing real to add: SKIP.

The goal is for people who see this reply to wonder "who is this?" and click the
profile. Only reply if the reply is genuinely worth reading.
"""


def _load_target_accounts() -> list[str]:
    """Load target account list from file if it exists, else use defaults."""
    import json
    from pathlib import Path
    path = Path("data/growth/target_accounts.json")
    if path.exists():
        try:
            data = json.loads(path.read_text())
            return data.get("accounts", _DEFAULT_TARGET_ACCOUNTS)
        except Exception:
            pass
    return _DEFAULT_TARGET_ACCOUNTS


def _portfolio_context(portfolio: dict) -> str:
    positions = [p["project"] for p in portfolio.get("positions", []) if p.get("status") == "active"]
    airdrops  = [a["project"] for a in portfolio.get("airdrops",  []) if a.get("status") == "farming"]
    if not positions and not airdrops:
        return ""
    return "Held positions (disclose if relevant): " + ", ".join(positions + airdrops)


def _generate_reply(tweet_text: str, portfolio: dict) -> Optional[str]:
    portfolio_ctx = _portfolio_context(portfolio)
    prompt = f"Tweet to reply to:\n\n{tweet_text}"
    if portfolio_ctx:
        prompt += f"\n\n{portfolio_ctx}"
    prompt += "\n\nWrite a reply that adds something specific, or respond with exactly SKIP."

    reply = llm_complete(system=_REPLY_SYSTEM, user=prompt, max_tokens=CLAUDE_MAX_TOKENS, temperature=0.75)
    if not reply:
        return None
    reply = reply.strip()
    if reply.upper().startswith("SKIP") or len(reply) < 15:
        return None
    if len(reply) > 280:
        reply = reply[:276].rsplit(".", 1)[0] + "."
    return reply


def _get_my_user_id(client: tweepy.Client) -> Optional[str]:
    try:
        me = client.get_me()
        if me and me.data:
            return str(me.data.id)
    except Exception:
        pass
    return None


def _is_recent(created_at, max_age_hours: float = 3.0) -> bool:
    """Return True if the tweet was posted within max_age_hours."""
    if not created_at:
        return True
    age = time.time() - created_at.timestamp()
    return age < max_age_hours * 3600


# ---------------------------------------------------------------------------
# Mode 1: Targeted account monitoring
# ---------------------------------------------------------------------------

def _engage_targeted_accounts(
    client: tweepy.Client,
    state: State,
    portfolio: dict,
    my_user_id: Optional[str],
    max_engagements: int,
) -> int:
    target_accounts = _load_target_accounts()
    already_replied = state.last_replied_to()
    engagements     = 0

    for username in target_accounts:
        if engagements >= max_engagements:
            break
        try:
            user_resp = client.get_user(username=username, user_fields=["id"])
            if not user_resp or not user_resp.data:
                continue
            user_id = str(user_resp.data.id)

            if my_user_id and user_id == my_user_id:
                continue

            tweets_resp = client.get_users_tweets(
                id=user_id,
                max_results=5,
                tweet_fields=["public_metrics", "created_at"],
                exclude=["retweets", "replies"],
            )
            if not tweets_resp or not tweets_resp.data:
                continue

            for tweet in tweets_resp.data:
                tweet_id = str(tweet.id)
                if tweet_id in already_replied:
                    continue
                if not _is_recent(getattr(tweet, "created_at", None), max_age_hours=3.0):
                    continue

                metrics = tweet.public_metrics or {}
                if metrics.get("like_count", 0) < 5 and metrics.get("reply_count", 0) < 2:
                    continue

                # Only engage if the post is in our focus topics
                text_lower = tweet.text.lower()
                if not any(kw in text_lower for kw in FOCUS_KEYWORDS):
                    continue

                reply_text = _generate_reply(tweet.text, portfolio)
                if not reply_text:
                    log.debug("Skipping @%s tweet — quality gate rejected.", username)
                    continue

                sent_id = post_tweet(reply_text, reply_to_id=tweet_id)
                if sent_id:
                    state.mark_replied(tweet_id)
                    engagements += 1
                    log.info(
                        "Targeted reply → @%s ('%s...'): %s",
                        username, tweet.text[:40], reply_text[:60],
                    )
                    break  # one reply per account per run

        except tweepy.errors.Forbidden:
            log.debug("Can't read @%s (protected or API tier)", username)
        except tweepy.errors.TweepyException as exc:
            log.debug("Tweepy error for @%s: %s", username, exc)
        except Exception as exc:
            log.debug("Error targeting @%s: %s", username, exc)

    return engagements


# ---------------------------------------------------------------------------
# Mode 2: Keyword search engagement
# ---------------------------------------------------------------------------

def _engage_keyword_search(
    client: tweepy.Client,
    state: State,
    portfolio: dict,
    my_user_id: Optional[str],
    max_engagements: int,
) -> int:
    already_replied = state.last_replied_to()
    engagements     = 0

    for query in _KEYWORD_QUERIES:
        if engagements >= max_engagements:
            break
        try:
            resp = client.search_recent_tweets(
                query=query,
                max_results=10,
                tweet_fields=["public_metrics", "created_at", "author_id"],
                sort_order="relevancy",
            )
            if not resp or not resp.data:
                continue

            for tweet in resp.data:
                if engagements >= max_engagements:
                    break

                tweet_id  = str(tweet.id)
                author_id = str(tweet.author_id)

                if tweet_id in already_replied:
                    continue
                if my_user_id and author_id == my_user_id:
                    continue
                if not _is_recent(getattr(tweet, "created_at", None), max_age_hours=2.0):
                    continue

                metrics = tweet.public_metrics or {}
                if metrics.get("like_count", 0) < 30 and metrics.get("reply_count", 0) < 5:
                    continue

                reply_text = _generate_reply(tweet.text, portfolio)
                if not reply_text:
                    continue

                sent_id = post_tweet(reply_text, reply_to_id=tweet_id)
                if sent_id:
                    state.mark_replied(tweet_id)
                    engagements += 1
                    log.info(
                        "Keyword reply (likes:%d) '%s...': %s",
                        metrics.get("like_count", 0),
                        tweet.text[:40],
                        reply_text[:60],
                    )

        except tweepy.errors.Forbidden:
            log.warning("Search unavailable — X API Basic tier required.")
            break
        except tweepy.errors.TweepyException as exc:
            log.error("Search error: %s", exc)

    return engagements


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(state: State) -> int:
    """
    Proactive outbound engagement.
    Returns total number of replies sent.
    """
    client    = get_client()
    portfolio = load_portfolio()
    my_id     = _get_my_user_id(client)

    targeted = _engage_targeted_accounts(
        client, state, portfolio, my_id, MAX_TARGETED_ENGAGEMENTS
    )
    keyword  = _engage_keyword_search(
        client, state, portfolio, my_id,
        max(0, MAX_TOTAL_PER_RUN - targeted),
    )

    total = targeted + keyword
    log.info("Proactive engagement: %d targeted + %d keyword = %d total.", targeted, keyword, total)
    return total
