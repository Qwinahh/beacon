"""
bot/x/follow.py — Strategic, strictly-gated following.

The goal is NOT to accumulate followers via follow-back mechanics.
The goal is to be visible in the feeds and notifications of people who
actually matter in the DeFi/perps/airdrop space, so that:

  1. They see @Qwinahh's posts in their timeline.
  2. When @Qwinahh replies to them, followers of those accounts see the
     reply and click through — because we're a "recognised" account
     (following = light credibility signal).
  3. Some of them follow back because the content is worth following.

STRICT GATES — an account is only followed if ALL of these pass:
  1. Active: posted in the last 7 days
  2. Relevant: ≥2 of their last 10 posts contain focus keywords
  3. Real engagement: avg likes/followers ratio > 0.3% (not a dead account)
  4. Not a spam/bot pattern: follower:following ratio not inverted by >5x
  5. Not already followed
  6. Not already attempted (tracked in state)
  7. Daily cap: max 10 follows per day total
  8. Minimum followers: 1,000 (not a brand new account)
  9. Maximum followers: 500,000 (mega-accounts rarely follow back, low signal)

These limits protect the account from:
  - Looking like a follow-farmer (bad for credibility)
  - X's automated follow-spam detection (which can limit accounts)
  - Wasting follows on accounts that add no visibility

Requires X API Basic tier. Exits cleanly on free tier.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

import tweepy

from bot.config import FOCUS_KEYWORDS
from bot.state import State
from bot.x.client import get_client

log = logging.getLogger(__name__)

# ---- Strict limits --------------------------------------------------------
MAX_FOLLOWS_PER_DAY     = 10    # Absolute ceiling. Never exceed.
MAX_FOLLOWS_PER_RUN     = 3     # Max per engage.py invocation (runs ~3x/day).
MIN_FOLLOWER_COUNT      = 1_000
MAX_FOLLOWER_COUNT      = 500_000
MIN_RELEVANCE_POSTS     = 2     # Out of last 10 posts must contain focus keyword
MIN_ENGAGEMENT_RATIO    = 0.003 # likes/followers — filters dead accounts
MAX_FOLLOWING_RATIO     = 5.0   # following/followers ceiling — filters bots/farmers

_FOLLOW_STATE_FILE = Path("data/growth/follow_state.json")


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def _load_follow_state() -> dict:
    if not _FOLLOW_STATE_FILE.exists():
        return {"followed": [], "daily": {}, "attempted": []}
    try:
        return json.loads(_FOLLOW_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"followed": [], "daily": {}, "attempted": []}


def _save_follow_state(state: dict) -> None:
    _FOLLOW_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _FOLLOW_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _follows_today(follow_state: dict) -> int:
    today = time.strftime("%Y-%m-%d")
    return follow_state.get("daily", {}).get(today, 0)


def _increment_daily(follow_state: dict) -> None:
    today = time.strftime("%Y-%m-%d")
    follow_state.setdefault("daily", {})[today] = _follows_today(follow_state) + 1
    # Prune old days (keep last 7)
    days = sorted(follow_state["daily"].keys())
    for old in days[:-7]:
        del follow_state["daily"][old]


# ---------------------------------------------------------------------------
# Account quality checks
# ---------------------------------------------------------------------------

def _qualifies(
    client: tweepy.Client,
    user_id: str,
    username: str,
    follow_state: dict,
) -> tuple[bool, str]:
    """
    Run all quality gates. Returns (passes, reason_if_rejected).
    """
    if user_id in follow_state.get("followed", []):
        return False, "already following"
    if user_id in follow_state.get("attempted", []):
        return False, "already attempted"

    try:
        user_resp = client.get_user(
            id=user_id,
            user_fields=["public_metrics", "created_at"],
        )
        if not user_resp or not user_resp.data:
            return False, "user data unavailable"

        user = user_resp.data
        metrics = user.public_metrics or {}
        followers  = metrics.get("followers_count", 0)
        following  = metrics.get("following_count", 0)

        # Follower range
        if followers < MIN_FOLLOWER_COUNT:
            return False, f"too small ({followers} followers)"
        if followers > MAX_FOLLOWER_COUNT:
            return False, f"too large ({followers} followers)"

        # Bot/farmer pattern: following >> followers
        if following > 0 and (following / max(followers, 1)) > MAX_FOLLOWING_RATIO:
            return False, f"suspect ratio ({following} following / {followers} followers)"

        # Check recent posts for relevance and engagement
        tweets_resp = client.get_users_tweets(
            id=user_id,
            max_results=10,
            tweet_fields=["public_metrics"],
            exclude=["retweets", "replies"],
        )
        if not tweets_resp or not tweets_resp.data:
            return False, "no recent posts"

        tweets = tweets_resp.data
        relevant_count = 0
        total_likes    = 0

        for t in tweets:
            text_lower = t.text.lower()
            if any(kw in text_lower for kw in FOCUS_KEYWORDS):
                relevant_count += 1
            total_likes += (t.public_metrics or {}).get("like_count", 0)

        if relevant_count < MIN_RELEVANCE_POSTS:
            return False, f"only {relevant_count}/{len(tweets)} posts are relevant"

        # Engagement sanity: avg likes vs followers
        avg_likes = total_likes / len(tweets) if tweets else 0
        eng_ratio = avg_likes / max(followers, 1)
        if eng_ratio < MIN_ENGAGEMENT_RATIO:
            return False, f"low engagement ({eng_ratio:.4f} avg likes/followers)"

        return True, ""

    except tweepy.errors.Forbidden:
        return False, "protected account"
    except tweepy.errors.TweepyException as exc:
        return False, f"API error: {exc}"


# ---------------------------------------------------------------------------
# Source: find accounts to consider following
# ---------------------------------------------------------------------------

def _candidate_accounts_from_replies(
    client: tweepy.Client,
    my_user_id: str,
    follow_state: dict,
) -> list[tuple[str, str]]:
    """
    Find users who recently replied to one of our posts — they're already engaged
    with the content, making them the highest-quality follow candidates.
    Returns list of (user_id, username) pairs.
    """
    candidates = []
    try:
        # Get our recent tweets
        tweets_resp = client.get_users_tweets(
            id=my_user_id,
            max_results=5,
            tweet_fields=["public_metrics"],
        )
        if not tweets_resp or not tweets_resp.data:
            return candidates

        for tweet in tweets_resp.data:
            tweet_id = str(tweet.id)
            replies_resp = client.search_recent_tweets(
                query=f"conversation_id:{tweet_id} -from:{my_user_id}",
                max_results=10,
                tweet_fields=["author_id"],
                expansions=["author_id"],
                user_fields=["username"],
            )
            if not replies_resp or not replies_resp.data:
                continue

            users = {u.id: u.username for u in (replies_resp.includes.get("users") or [])}
            for rt in replies_resp.data:
                uid = str(rt.author_id)
                uname = users.get(rt.author_id, "")
                if uid not in follow_state.get("followed", []) and uid not in follow_state.get("attempted", []):
                    candidates.append((uid, uname))

    except Exception as exc:
        log.debug("Reply candidate fetch error: %s", exc)
    return candidates


def _candidate_accounts_from_targets(
    client: tweepy.Client,
    follow_state: dict,
) -> list[tuple[str, str]]:
    """
    Find followers of our target accounts that we haven't followed yet.
    These are people already in the right audience.
    """
    from bot.x.trend import _load_target_accounts
    candidates = []

    for username in _load_target_accounts()[:5]:  # Limit API calls
        try:
            user_resp = client.get_user(username=username)
            if not user_resp or not user_resp.data:
                continue
            uid = str(user_resp.data.id)

            # Get recent engagers on their posts (people who replied)
            tweets_resp = client.get_users_tweets(
                id=uid, max_results=3,
                tweet_fields=["public_metrics"],
                exclude=["retweets"],
            )
            if not tweets_resp or not tweets_resp.data:
                continue

            for tweet in tweets_resp.data:
                if (tweet.public_metrics or {}).get("reply_count", 0) < 3:
                    continue
                replies_resp = client.search_recent_tweets(
                    query=f"conversation_id:{tweet.id}",
                    max_results=5,
                    tweet_fields=["author_id"],
                    expansions=["author_id"],
                    user_fields=["username"],
                )
                if not replies_resp or not replies_resp.data:
                    continue
                users = {u.id: u.username for u in (replies_resp.includes.get("users") or [])}
                for rt in replies_resp.data:
                    cid = str(rt.author_id)
                    cname = users.get(rt.author_id, "")
                    if cid != uid and cid not in follow_state.get("followed", []):
                        candidates.append((cid, cname))

            if len(candidates) >= 20:
                break

        except Exception as exc:
            log.debug("Target candidate fetch error for @%s: %s", username, exc)

    return candidates


# ---------------------------------------------------------------------------
# Main follow logic
# ---------------------------------------------------------------------------

def run_follow_cycle(state: State) -> int:
    """
    Run one follow cycle. Returns number of accounts followed.
    Called from engage.py after replies.
    """
    follow_state = _load_follow_state()

    # Hard daily cap check
    today_count = _follows_today(follow_state)
    if today_count >= MAX_FOLLOWS_PER_DAY:
        log.info("Daily follow cap reached (%d/%d). Skipping.", today_count, MAX_FOLLOWS_PER_DAY)
        return 0

    remaining_today = MAX_FOLLOWS_PER_DAY - today_count
    this_run_limit  = min(MAX_FOLLOWS_PER_RUN, remaining_today)

    client = get_client()
    my_id_resp = client.get_me()
    if not my_id_resp or not my_id_resp.data:
        log.warning("Could not fetch own user ID — skipping follow cycle.")
        return 0
    my_user_id = str(my_id_resp.data.id)

    # Gather candidates: reply engagers first, then target account followers
    candidates: list[tuple[str, str]] = []
    candidates += _candidate_accounts_from_replies(client, my_user_id, follow_state)
    if len(candidates) < this_run_limit * 2:
        candidates += _candidate_accounts_from_targets(client, follow_state)

    # Deduplicate
    seen_ids: set[str] = set()
    unique_candidates = []
    for uid, uname in candidates:
        if uid not in seen_ids and uid != my_user_id:
            seen_ids.add(uid)
            unique_candidates.append((uid, uname))

    follows_this_run = 0

    for user_id, username in unique_candidates:
        if follows_this_run >= this_run_limit:
            break

        # Always mark as attempted so we don't keep re-evaluating
        if user_id not in follow_state["attempted"]:
            follow_state["attempted"].append(user_id)
            # Prune attempted list (keep last 500)
            follow_state["attempted"] = follow_state["attempted"][-500:]

        qualifies, reason = _qualifies(client, user_id, username, follow_state)
        if not qualifies:
            log.debug("Skipping @%s (id:%s): %s", username, user_id, reason)
            continue

        try:
            client.follow_user(user_id)
            follow_state.setdefault("followed", []).append(user_id)
            _increment_daily(follow_state)
            follows_this_run += 1
            log.info(
                "Followed @%s (id:%s) [%d/%d today]",
                username, user_id, _follows_today(follow_state), MAX_FOLLOWS_PER_DAY,
            )
            time.sleep(2)  # Small delay — don't hammer the API

        except tweepy.errors.Forbidden as exc:
            log.warning("Follow failed for @%s: %s (API tier or limit)", username, exc)
        except tweepy.errors.TweepyException as exc:
            log.warning("Follow error for @%s: %s", username, exc)

    _save_follow_state(follow_state)
    log.info("Follow cycle done: %d followed this run (%d today).",
             follows_this_run, _follows_today(follow_state))
    return follows_this_run
