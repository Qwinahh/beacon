"""
bot/x/trend.py — Proactive outbound engagement.

WHY THIS MODULE EXISTS — the follower acquisition funnel:

  When @Qwinahh replies to a post by an account with 50k-200k followers,
  everyone reading that thread sees the reply. Of those readers:
    - ~5-10% click the profile if the reply is specific and credible
    - ~10-20% of profile visitors follow if the pinned post + recent posts are good

  Net result: 1 great reply to a 100k-follower account = 5-20 new followers.
  1 mediocre reply = 0 new followers and a slight credibility cost.

  This means:
    - 3-4 EXCELLENT replies per day > 40 mediocre replies
    - Who you reply to matters as much as what you say
    - Timing matters: reply within 60 minutes while the post is still being read

WHY THE LIMITS ARE WHAT THEY ARE:
  - 6 outbound replies per day cap (combined with state.MAX_REPLIES_PER_DAY = 8):
    * More than ~8-10/day looks like spam to followers and to X's algo
    * Engagement rate per reply (profile clicks / replies sent) collapses after 6-8/day
    * X's API rate limits also enforce this naturally on free/basic tier
  - 1 hour freshness window for targeted accounts (not 3h):
    * Reply notifications are only seen while the post is active in feeds
    * A reply at 2h is 10x less visible than a reply at 20 minutes
  - Max 1 reply per account per day:
    * Replying twice to the same person looks like following/harassment
    * Distributes visibility across multiple audiences

TWO ENGAGEMENT MODES:
  1. TARGETED ACCOUNT MONITORING — curated list of DeFi/perps/airdrop accounts.
     Prioritised by follower count (bigger audience = more visibility per reply).
  2. KEYWORD SEARCH — catches high-engagement trending posts not on the watchlist.

Requires X API Basic tier. Fails silently on free tier.
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

# Per-run caps — the daily cap in State enforces the absolute ceiling.
# These just prevent one bad run from using up the entire day's budget.
MAX_PER_RUN = 2   # Max replies sent in a single engage.py invocation.
              # engage.yml runs hourly. 2/run × ~3 active hours = 6/day budget.

# Reply freshness — only engage posts posted this recently.
# Targeted accounts: 60 min (their posts are read actively in this window).
# Keyword search: 90 min (broader search, slightly older ok).
TARGETED_FRESHNESS_MINUTES = 60
KEYWORD_FRESHNESS_MINUTES  = 90

# Minimum audience for targeted engagement.
# Below this, the reply is seen by too few people to be worth the slot.
MIN_FOLLOWERS_FOR_TARGETED = 10_000

# Keyword queries for catch-all search. Kept tight to avoid low-quality posts.
_KEYWORD_QUERIES = [
    "hyperliquid perp funding -is:retweet lang:en min_faves:50",
    "defi airdrop points farm -is:retweet lang:en min_faves:40",
    "kaito yap leaderboard -is:retweet lang:en min_faves:30",
]

# ---------------------------------------------------------------------------
# Curated target accounts — prioritised by approximate follower size.
# The bot works down this list in order, so high-follower accounts get
# engagement priority. Update via data/growth/target_accounts.json.
# ---------------------------------------------------------------------------
_DEFAULT_TARGET_ACCOUNTS = [
    # Tier 1: 100k-500k followers — each reply reaches a large crypto audience
    "CryptoHayes",
    "HsakaTrades",
    "MessariCrypto",
    "delphi_digital",

    # Tier 2: 30k-100k followers — highly engaged niche audiences
    "DefiIgnas",
    "hasufl",
    "tomhschmidt",
    "Croissant_eth",
    "Pentosh1",
    "0xMaki",

    # Tier 3: 10k-30k followers — peer level, direct niche relevance
    "0xHamz",
    "Founderization",
    "DefiIgnas",
    "zkDrops",
    "0xShitposter",
]


# ---------------------------------------------------------------------------
# The reply system prompt — this encodes the "why" into every generation.
# ---------------------------------------------------------------------------
_REPLY_SYSTEM = """\
You write outbound replies for @Qwinahh — a crypto account that trades perps,
farms airdrops, and moves into DeFi protocols before narratives form.

THE GOAL OF EVERY REPLY:
Make the person reading it think "who IS this?" and click the profile.
That is the only metric that matters. Not likes. Not agreement. Profile clicks.

A reply achieves this when it:
1. Adds something the original tweet didn't say — a specific number,
   a mechanic, a historical pattern, a counterpoint with data behind it.
2. Sounds like someone with real skin in the game, not a summariser.
3. Is short enough to read in 3 seconds but dense enough to reward it.

HARD RULES:
- Under 220 characters. One idea. No buildup.
- Never open with: "Great point", "Totally agree", "Interesting", "100%",
  "Exactly", "This", "Facts", or any agreement without substance.
- Never make price predictions. No hashtags.
- If you hold a relevant position, end with: (position disclosed)
- If the tweet is price-only, hostile, vague, or there is genuinely
  nothing specific to add: respond with exactly SKIP.

EXAMPLES OF REPLIES WORTH SENDING:
Tweet: "Hyperliquid TVL up 40% this week"
Reply: "OI up too but HLP utilisation is only 34%. More TVL than traders to take the other side right now."

Tweet: "Kaito points season 2 is live, time to farm"
Reply: "Engagement-to-point ratio is 3x worse than S1. Farm is already crowded."

Tweet: "DeFi summer vibes with all these new protocols launching"
Reply: SKIP (vague, no data, nothing to add)

EXAMPLES OF REPLIES NOT WORTH SENDING:
"Agreed, this is a really important development for the space." → SKIP
"Great take, been watching this closely too." → SKIP
"This!" → SKIP
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_target_accounts() -> list[str]:
    import json
    from pathlib import Path
    path = Path("data/growth/target_accounts.json")
    if path.exists():
        try:
            return json.loads(path.read_text()).get("accounts", _DEFAULT_TARGET_ACCOUNTS)
        except Exception:
            pass
    return _DEFAULT_TARGET_ACCOUNTS


def _portfolio_context(portfolio: dict) -> str:
    positions = [p["project"] for p in portfolio.get("positions", []) if p.get("status") == "active"]
    airdrops  = [a["project"] for a in portfolio.get("airdrops",  []) if a.get("status") == "farming"]
    if not positions and not airdrops:
        return ""
    return "Your held positions (disclose if relevant): " + ", ".join(positions + airdrops)


def _generate_reply(tweet_text: str, author_username: str, portfolio: dict) -> Optional[str]:
    portfolio_ctx = _portfolio_context(portfolio)
    prompt = f"Tweet by @{author_username}:\n\n{tweet_text}"
    if portfolio_ctx:
        prompt += f"\n\n{portfolio_ctx}"
    prompt += (
        "\n\nWrite a reply that would make someone click the profile, "
        "or respond with exactly SKIP if there is nothing specific to add."
    )

    reply = llm_complete(system=_REPLY_SYSTEM, user=prompt, max_tokens=CLAUDE_MAX_TOKENS, temperature=0.72)
    if not reply:
        return None
    reply = reply.strip()
    if reply.upper().startswith("SKIP") or len(reply) < 15:
        return None
    if len(reply) > 280:
        reply = reply[:276].rsplit(".", 1)[0] + "."
    return reply


def _is_fresh(created_at, max_age_minutes: float) -> bool:
    if not created_at:
        return True
    age_minutes = (time.time() - created_at.timestamp()) / 60
    return age_minutes < max_age_minutes


def _get_my_user_id(client: tweepy.Client) -> Optional[str]:
    try:
        me = client.get_me()
        if me and me.data:
            return str(me.data.id)
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Mode 1: Targeted account monitoring
# ---------------------------------------------------------------------------

def _engage_targeted(
    client: tweepy.Client,
    state: State,
    portfolio: dict,
    my_user_id: Optional[str],
    budget: int,
) -> int:
    """
    Check recent posts from target accounts and reply to the best one
    within the time window, if we have something specific to add.

    Works down the list in priority order (high-follower accounts first),
    stops as soon as the per-run budget is used.
    """
    target_accounts = _load_target_accounts()
    already_replied = state.last_replied_to()
    sent = 0

    for username in target_accounts:
        if sent >= budget or state.at_daily_reply_cap():
            break

        # Don't reply to the same account twice in one day
        if state.times_engaged_account_recently(username, window=20) >= 1:
            log.debug("Already engaged @%s recently, skipping.", username)
            continue

        try:
            user_resp = client.get_user(
                username=username,
                user_fields=["id", "public_metrics"],
            )
            if not user_resp or not user_resp.data:
                continue

            user = user_resp.data
            user_id = str(user.id)

            if my_user_id and user_id == my_user_id:
                continue

            # Enforce minimum audience size — below this the reply isn't worth the slot
            followers = (user.public_metrics or {}).get("followers_count", 0)
            if followers < MIN_FOLLOWERS_FOR_TARGETED:
                log.debug("@%s has %d followers, below minimum. Skipping.", username, followers)
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

                # Only engage while the post is still being actively read
                if not _is_fresh(getattr(tweet, "created_at", None), TARGETED_FRESHNESS_MINUTES):
                    continue

                # Needs at least some initial engagement (not a dud post)
                metrics = tweet.public_metrics or {}
                if metrics.get("like_count", 0) < 3 and metrics.get("reply_count", 0) < 1:
                    continue

                # Relevance check — is this about something we actually have a view on?
                text_lower = tweet.text.lower()
                if not any(kw in text_lower for kw in FOCUS_KEYWORDS):
                    log.debug("@%s post not in focus topics, skipping.", username)
                    continue

                reply_text = _generate_reply(tweet.text, username, portfolio)
                if not reply_text:
                    log.debug("Quality gate: nothing specific to add to @%s post.", username)
                    continue

                sent_id = post_tweet(reply_text, reply_to_id=tweet_id)
                if sent_id:
                    state.mark_replied(tweet_id)
                    state.increment_reply_count()
                    state.mark_engaged_account(username)
                    sent += 1
                    log.info(
                        "Replied to @%s (%dk followers, %d min old): %s",
                        username,
                        followers // 1000,
                        (time.time() - tweet.created_at.timestamp()) // 60 if tweet.created_at else 0,
                        reply_text[:70],
                    )
                    break  # One reply per account per run

        except tweepy.errors.Forbidden:
            log.debug("Can't read @%s", username)
        except tweepy.errors.TweepyException as exc:
            log.debug("API error for @%s: %s", username, exc)

    return sent


# ---------------------------------------------------------------------------
# Mode 2: Keyword search
# ---------------------------------------------------------------------------

def _engage_keyword(
    client: tweepy.Client,
    state: State,
    portfolio: dict,
    my_user_id: Optional[str],
    budget: int,
) -> int:
    """
    Find high-engagement posts on focus topics and reply to the best ones.
    Lower priority than targeted — uses remaining budget only.
    """
    already_replied = state.last_replied_to()
    sent = 0

    for query in _KEYWORD_QUERIES:
        if sent >= budget or state.at_daily_reply_cap():
            break
        try:
            resp = client.search_recent_tweets(
                query=query,
                max_results=10,
                tweet_fields=["public_metrics", "created_at", "author_id"],
                expansions=["author_id"],
                user_fields=["username", "public_metrics"],
                sort_order="relevancy",
            )
            if not resp or not resp.data:
                continue

            users_by_id = {str(u.id): u for u in (resp.includes.get("users") or [])}

            for tweet in resp.data:
                if sent >= budget or state.at_daily_reply_cap():
                    break

                tweet_id  = str(tweet.id)
                author_id = str(tweet.author_id)

                if tweet_id in already_replied:
                    continue
                if my_user_id and author_id == my_user_id:
                    continue
                if not _is_fresh(getattr(tweet, "created_at", None), KEYWORD_FRESHNESS_MINUTES):
                    continue

                # Need meaningful engagement for keyword search
                metrics = tweet.public_metrics or {}
                if metrics.get("like_count", 0) < 40 and metrics.get("reply_count", 0) < 8:
                    continue

                author = users_by_id.get(author_id)
                author_username = author.username if author else "unknown"
                author_followers = (author.public_metrics or {}).get("followers_count", 0) if author else 0

                # Don't spam to the same account across modes
                if state.times_engaged_account_recently(author_username, window=20) >= 1:
                    continue

                reply_text = _generate_reply(tweet.text, author_username, portfolio)
                if not reply_text:
                    continue

                sent_id = post_tweet(reply_text, reply_to_id=tweet_id)
                if sent_id:
                    state.mark_replied(tweet_id)
                    state.increment_reply_count()
                    state.mark_engaged_account(author_username)
                    sent += 1
                    log.info(
                        "Keyword reply → @%s (%dk followers, likes:%d): %s",
                        author_username,
                        author_followers // 1000,
                        metrics.get("like_count", 0),
                        reply_text[:70],
                    )

        except tweepy.errors.Forbidden:
            log.warning("Search unavailable — X API Basic tier required.")
            break
        except tweepy.errors.TweepyException as exc:
            log.error("Search error: %s", exc)

    return sent


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(state: State) -> int:
    """
    Proactive outbound engagement.

    Checks daily cap first — if we've already sent 8 replies today, stops.
    Works through targeted accounts first, then keyword search with remaining budget.

    Returns total replies sent this run.
    """
    if state.at_daily_reply_cap():
        log.info(
            "Daily reply cap reached (%d/%d). No outbound engagement this run.",
            state.replies_today(), State.MAX_REPLIES_PER_DAY,
        )
        return 0

    log.info(
        "Outbound engagement: %d/%d replies used today.",
        state.replies_today(), State.MAX_REPLIES_PER_DAY,
    )

    client    = get_client()
    portfolio = load_portfolio()
    my_id     = _get_my_user_id(client)

    targeted = _engage_targeted(client, state, portfolio, my_id, MAX_PER_RUN)
    remaining = max(0, MAX_PER_RUN - targeted)
    keyword  = _engage_keyword(client, state, portfolio, my_id, remaining)

    total = targeted + keyword
    log.info(
        "Outbound: %d targeted + %d keyword = %d total | %d/%d used today.",
        targeted, keyword, total, state.replies_today(), State.MAX_REPLIES_PER_DAY,
    )
    return total
