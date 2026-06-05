"""
Trend engagement.

Finds trending crypto conversations on X and adds genuine commentary.
The goal is to surface @Qwinahh to people already in relevant discussions —
not to spam, but to be the reply that's actually worth reading.

Rate limits enforced here:
  - Max 3 trend engagements per run.
  - Only engages with posts from the past 3 hours with meaningful engagement.
  - Never engages the same post twice.
  - Requires X API Basic tier (search is unavailable on free tier).

Note: adding genuine value to a trending conversation is legitimate and
common on X. This module is not for broadcasting — it's for participating.
Any engagement with topics linked to held positions includes disclosure.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import anthropic
import tweepy

from bot.config import CLAUDE_MAX_TOKENS, CLAUDE_MODEL, FOCUS_KEYWORDS
from bot.portfolio.tracker import load_portfolio
from bot.state import State
from bot.x.client import get_client, post_tweet

log = logging.getLogger(__name__)

MAX_TREND_ENGAGEMENTS_PER_RUN = 3

# Keywords used to find relevant trending conversations.
TREND_SEARCH_QUERIES = [
    "hyperliquid perp -is:retweet lang:en",
    "defi airdrop points -is:retweet lang:en",
    "kaito yap -is:retweet lang:en",
    "crypto alpha launch -is:retweet lang:en",
]

_TREND_REPLY_SYSTEM = """\
You write short, insightful replies for a crypto commentary account (@Qwinahh).

The reply must:
- Add something the original tweet didn't say (a data point, a counterpoint, a sharper angle).
- Be under 220 characters.
- Sound like someone who actually follows this space closely.
- NOT start with "Great point" or "Totally agree" or any filler opener.
- NOT make price predictions.
- NOT use hashtags.
- If the topic is linked to a held position in the portfolio, end with "(position disclosed)".

Be selective. A reply that adds nothing is worse than no reply.

OUTPUT FORMAT — respond with exactly one of:
  REPLY: [your reply text under 220 chars]
  SKIP: [one-word reason: hostile/spam/vague/no_value]
"""


def _portfolio_context(portfolio: dict) -> str:
    positions = [p["project"] for p in portfolio.get("positions", []) if p.get("status") == "active"]
    airdrops  = [a["project"] for a in portfolio.get("airdrops",  []) if a.get("status") == "farming"]
    if not positions and not airdrops:
        return ""
    return "Held positions: " + ", ".join(positions + airdrops)


def _parse_reply(raw: str) -> Optional[str]:
    upper = raw.upper()
    if upper.startswith("REPLY:"):
        text = raw[6:].strip()
        return text if len(text) >= 15 else None
    if upper.startswith("SKIP"):
        return None
    # Fallback: treat unstructured output as a reply if long enough.
    return raw.strip() if len(raw.strip()) >= 15 else None


def _generate_trend_reply(tweet_text: str, portfolio: dict) -> Optional[str]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    client = anthropic.Anthropic(api_key=api_key)
    portfolio_ctx = _portfolio_context(portfolio)
    prompt = f"Tweet to reply to:\n\n{tweet_text}"
    if portfolio_ctx:
        prompt += f"\n\n{portfolio_ctx}"

    try:
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            system=_TREND_REPLY_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        reply = _parse_reply(raw)
        if reply is None:
            return None
        if len(reply) > 280:
            reply = reply[:276].rsplit(".", 1)[0] + "."
        return reply
    except anthropic.APIError as exc:
        log.error("Anthropic API error in trend reply: %s", exc)
        return None


def _search_trending(query: str, min_likes: int = 50) -> list[dict]:
    """
    Search for recent, high-engagement tweets matching a query.
    Returns list of {id, text, like_count, author_id}.
    Requires X API Basic or above.
    """
    client = get_client()
    try:
        resp = client.search_recent_tweets(
            query=query,
            max_results=10,
            tweet_fields=["public_metrics", "created_at", "author_id"],
            sort_order="relevancy",
        )
        if not resp.data:
            return []

        results = []
        for tweet in resp.data:
            metrics   = tweet.public_metrics or {}
            likes     = metrics.get("like_count", 0)
            replies   = metrics.get("reply_count", 0)
            if likes < min_likes and replies < 10:
                continue
            results.append({
                "id":        str(tweet.id),
                "text":      tweet.text,
                "like_count": likes,
                "author_id": str(tweet.author_id),
            })
        return results

    except tweepy.errors.Forbidden:
        log.warning("Trending search unavailable — X API Basic tier required.")
        return []
    except tweepy.errors.TweepyException as exc:
        log.error("Search error: %s", exc)
        return []


def run(state: State) -> int:
    """
    Find trending relevant posts and reply to the best ones.
    Returns number of replies sent.
    """
    portfolio = load_portfolio()
    already_replied = state.last_replied_to()
    engagements = 0

    for query in TREND_SEARCH_QUERIES:
        if engagements >= MAX_TREND_ENGAGEMENTS_PER_RUN:
            break

        tweets = _search_trending(query)
        for tweet in tweets:
            if engagements >= MAX_TREND_ENGAGEMENTS_PER_RUN:
                break

            tweet_id = tweet["id"]
            if tweet_id in already_replied:
                continue

            # Skip our own tweets.
            me = get_client().get_me()
            if me and me.data and tweet["author_id"] == str(me.data.id):
                continue

            reply_text = _generate_trend_reply(tweet["text"], portfolio)
            if not reply_text:
                continue

            sent_id = post_tweet(reply_text, reply_to_id=tweet_id)
            if sent_id:
                state.mark_replied(tweet_id)
                engagements += 1
                log.info(
                    "Trend reply sent on '%s...' (likes: %d): %s",
                    tweet["text"][:40],
                    tweet["like_count"],
                    reply_text[:60],
                )

    return engagements
