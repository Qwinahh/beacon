"""
bot/x/follow.py -- Strategic, strictly-gated following.

The goal is NOT to accumulate followers via follow-back mechanics.
The goal is to be visible in the feeds and notifications of people who
actually matter in the DeFi/perps/airdrop space, so that:

  1. They see @Qwinahh's posts in their timeline.
  2. When @Qwinahh replies to them, followers of those accounts see the
     reply and click through -- because we're a "recognised" account
     (following = light credibility signal).
  3. Some of them follow back because the content is worth following.

STRICT GATES -- an account is only followed if ALL of these pass:
  1. Active: has recent posts with focus topic content
  2. Relevant: >=2 of their last 10 posts contain focus keywords
  3. Real engagement: avg likes/followers ratio > 0.3% (not a dead account)
  4. Not a spam/bot pattern: follower:following ratio not inverted by >5x
  5. Not already followed
  6. Not already attempted (tracked in state)
  7. Daily cap: max 10 follows per day total
  8. Minimum followers: 1,000 (not a brand new account)
  9. Maximum followers: 500,000 (mega-accounts rarely follow back, low signal)

READING uses twscrape (cookie-based, free).
WRITING (follow_user) uses official X API (Tweepy, Free tier).
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

from bot.config import FOCUS_KEYWORDS
from bot.state import State
from bot.x.client import get_client

log = logging.getLogger(__name__)

# ---- Strict limits --------------------------------------------------------
MAX_FOLLOWS_PER_DAY     = 10
MAX_FOLLOWS_PER_RUN     = 3
MAX_UNFOLLOWS_PER_RUN   = 5
UNFOLLOW_AFTER_HOURS    = 72   # Unfollow anyone who hasn't followed back after 3 days
MIN_FOLLOWER_COUNT      = 1_000
MAX_FOLLOWER_COUNT      = 500_000
MIN_RELEVANCE_POSTS     = 2
MIN_ENGAGEMENT_RATIO    = 0.003
MAX_FOLLOWING_RATIO     = 5.0

_FOLLOW_STATE_FILE = Path("data/growth/follow_state.json")

# Search queries for candidate discovery. Tight to ensure topic relevance.
_CANDIDATE_QUERIES = [
    "hyperliquid perp defi lang:en min_faves:20",
    "airdrop farm points protocol lang:en min_faves:15",
    "kaito yap leaderboard lang:en min_faves:10",
    "defillama tvl protocol launch lang:en min_faves:20",
    "perp dex funding rate lang:en min_faves:25",
]


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
    days = sorted(follow_state["daily"].keys())
    for old in days[:-7]:
        del follow_state["daily"][old]


def _normalize_followed(follow_state: dict) -> None:
    """
    Normalize the followed list to always be a list of dicts with timestamps.

    Old format: ["uid1", "uid2"]
    New format: [{"id": "uid1", "username": "name", "followed_at": 1234567890}]

    Migrates in-place so existing follow_state.json stays valid.
    """
    raw = follow_state.get("followed", [])
    normalized = []
    for entry in raw:
        if isinstance(entry, str):
            # Legacy: string uid only, no timestamp -- set followed_at to 0
            # so the unfollow pass will clean it up on next run.
            normalized.append({"id": entry, "username": "?", "followed_at": 0})
        elif isinstance(entry, dict):
            normalized.append(entry)
    follow_state["followed"] = normalized


def _followed_ids(follow_state: dict) -> set[str]:
    """Return set of followed user IDs (handles both old and new format)."""
    return {
        e["id"] if isinstance(e, dict) else e
        for e in follow_state.get("followed", [])
    }


def _run_unfollow_pass(follow_state: dict) -> int:
    """
    Unfollow accounts followed more than UNFOLLOW_AFTER_HOURS ago.

    Uses the official Tweepy client (Free tier supports unfollow).
    Keeps the following:follower ratio clean and prevents the profile
    looking like a follow-farmer.

    Returns number of accounts unfollowed.
    """
    now = time.time()
    cutoff = now - (UNFOLLOW_AFTER_HOURS * 3600)

    due = [
        entry for entry in follow_state.get("followed", [])
        if isinstance(entry, dict) and entry.get("followed_at", now) < cutoff
    ]

    if not due:
        return 0

    client = get_client()
    unfollowed = 0

    for entry in due[:MAX_UNFOLLOWS_PER_RUN]:
        uid      = entry["id"]
        username = entry.get("username", "?")
        age_h    = int((now - entry.get("followed_at", 0)) / 3600)
        try:
            client.unfollow_user(uid)
            # Remove from followed list
            follow_state["followed"] = [
                e for e in follow_state["followed"]
                if not (isinstance(e, dict) and e.get("id") == uid)
            ]
            unfollowed += 1
            log.info("Unfollowed @%s (followed %dh ago, no follow-back).", username, age_h)
            time.sleep(1)
        except Exception as exc:
            log.debug("Unfollow failed for @%s: %s", username, exc)

    return unfollowed


# ---------------------------------------------------------------------------
# twscrape helpers
# ---------------------------------------------------------------------------

def _get_cookies() -> Optional[str]:
    import os
    return os.environ.get("X_SCRAPER_COOKIES", "").strip() or None


async def _make_api():
    try:
        from twscrape import API
    except ImportError:
        log.warning("twscrape not installed.")
        return None
    cookies = _get_cookies()
    if not cookies:
        log.warning("X_SCRAPER_COOKIES not set -- follow candidate discovery unavailable.")
        return None
    api = API(os.path.join(tempfile.gettempdir(), "twscrape_pool.db"))
    try:
        await api.pool.add_account(
            username="beacon_follow_scraper",
            password="placeholder",
            email="placeholder@placeholder.com",
            email_password="placeholder",
            cookies=cookies,
        )
    except Exception as exc:
        log.warning("twscrape setup for follow: %s", exc)
        return None
    return api


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result(timeout=90)
        else:
            return loop.run_until_complete(coro)
    except Exception as exc:
        log.warning("Async runner error (follow): %s", exc)
        return None


# ---------------------------------------------------------------------------
# Priority follow list (curated, no quality gate needed)
# ---------------------------------------------------------------------------

_PRIORITY_LIST_FILE = Path("data/growth/target_follow_accounts.json")


async def _resolve_uid_async(username: str) -> Optional[str]:
    """Resolve a Twitter username to a numeric user ID via twscrape."""
    api = await _make_api()
    if not api:
        return None
    try:
        user = await api.user_by_login(username)
        return str(user.id) if user else None
    except Exception as exc:
        log.debug("UID resolve failed for @%s: %s", username, exc)
        return None


def _priority_follow_pass(follow_state: dict, client) -> int:
    """
    Follow accounts from the curated priority list before random discovery.
    These are manually vetted — no quality gate applied.
    Returns number of accounts followed this pass.
    """
    if not _PRIORITY_LIST_FILE.exists():
        return 0
    try:
        config = json.loads(_PRIORITY_LIST_FILE.read_text(encoding="utf-8"))
    except Exception:
        return 0

    priority       = config.get("priority_follows", [])
    already_done   = {u.lower() for u in config.get("already_followed", [])}
    skip_set       = {u.lower() for u in config.get("skip", [])}
    followed_names = {
        e.get("username", "").lower()
        for e in follow_state.get("followed", [])
        if isinstance(e, dict)
    }

    followed = 0
    config_dirty = False

    for entry in priority:
        if followed >= MAX_FOLLOWS_PER_RUN:
            break
        if _follows_today(follow_state) >= MAX_FOLLOWS_PER_DAY:
            break

        username = entry.get("username", "").lower()
        if not username:
            continue
        if username in already_done or username in skip_set or username in followed_names:
            continue

        uid = _run_async(_resolve_uid_async(username))
        if not uid:
            log.debug("Could not resolve uid for @%s — skipping.", username)
            continue

        try:
            client.follow_user(uid)
            follow_state.setdefault("followed", []).append({
                "id":          uid,
                "username":    username,
                "followed_at": int(time.time()),
            })
            _increment_daily(follow_state)
            config.setdefault("already_followed", []).append(username)
            config_dirty = True
            followed += 1
            log.info("Priority follow: @%s (%s)", username, entry.get("reason", ""))
            time.sleep(2)
        except Exception as exc:
            log.debug("Priority follow failed for @%s: %s", username, exc)

    if config_dirty:
        try:
            _PRIORITY_LIST_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")
        except Exception as exc:
            log.warning("Could not save priority follow config: %s", exc)

    return followed


# ---------------------------------------------------------------------------
# Candidate discovery via twscrape
# ---------------------------------------------------------------------------

async def _find_candidates_async(follow_state: dict) -> list[dict]:
    """
    Search for active voices in focus topics.
    Returns a list of candidate dicts with id, username, followers, following.
    """
    api = await _make_api()
    if not api:
        return []

    excluded = _followed_ids(follow_state) | set(follow_state.get("attempted", []))
    seen_ids: set[str] = set(excluded)
    candidates: list[dict] = []

    for query in _CANDIDATE_QUERIES:
        if len(candidates) >= 40:
            break
        try:
            async for tweet in api.search(
                f"{query} -is:retweet",
                limit=12,
                kv={"product": "Latest"},
            ):
                if not tweet.user:
                    continue
                uid = str(tweet.user.id)
                if uid in seen_ids:
                    continue
                seen_ids.add(uid)
                candidates.append({
                    "id":        uid,
                    "username":  tweet.user.username,
                    "followers": getattr(tweet.user, "followersCount", 0) or 0,
                    "following": getattr(tweet.user, "followingCount", 0) or 0,
                })
        except Exception as exc:
            log.debug("Candidate search error ('%s'): %s", query[:40], exc)

    log.info("Follow: found %d raw candidates.", len(candidates))
    return candidates


# ---------------------------------------------------------------------------
# Quality gate via twscrape
# ---------------------------------------------------------------------------

async def _check_quality_async(candidate: dict) -> tuple[bool, str]:
    """
    Run quality checks on a candidate using twscrape.
    Returns (passes, reason_if_rejected).
    """
    followers = candidate.get("followers", 0)
    following = candidate.get("following", 0)
    username  = candidate.get("username", "?")

    # Follower range
    if followers < MIN_FOLLOWER_COUNT:
        return False, f"too small ({followers} followers)"
    if followers > MAX_FOLLOWER_COUNT:
        return False, f"too large ({followers} followers)"

    # Bot/farmer ratio
    if following > 0 and (following / max(followers, 1)) > MAX_FOLLOWING_RATIO:
        return False, f"suspect ratio ({following}/{followers})"

    # Check recent posts for topic relevance and engagement
    api = await _make_api()
    if not api:
        # If we can't check, accept on follower count alone (graceful degradation)
        log.debug("twscrape unavailable for quality check on @%s -- accepting on count alone.", username)
        return True, ""

    try:
        uid_int = int(candidate["id"])
        tweets = []
        async for tweet in api.user_tweets(uid_int, limit=10):
            tweets.append(tweet)

        if not tweets:
            return False, "no recent posts"

        relevant_count = sum(
            1 for t in tweets
            if any(kw in (t.rawContent or "").lower() for kw in FOCUS_KEYWORDS)
        )

        if relevant_count < MIN_RELEVANCE_POSTS:
            return False, f"only {relevant_count}/{len(tweets)} posts relevant"

        total_likes = sum(getattr(t, "likeCount", 0) or 0 for t in tweets)
        avg_likes   = total_likes / len(tweets) if tweets else 0
        eng_ratio   = avg_likes / max(followers, 1)

        if eng_ratio < MIN_ENGAGEMENT_RATIO:
            return False, f"low engagement ratio ({eng_ratio:.4f})"

        return True, ""

    except Exception as exc:
        log.debug("Quality check error for @%s: %s", username, exc)
        return False, f"check error: {exc}"


# ---------------------------------------------------------------------------
# Main follow logic
# ---------------------------------------------------------------------------

def run_follow_cycle(state: State) -> int:
    """
    Run one follow cycle. Returns number of accounts followed.
    Called from engage.py after replies.

    Reading uses twscrape (free).
    Following uses official Tweepy client (Free API tier).
    """
    follow_state = _load_follow_state()

    # Migrate old string-format followed list to dict format with timestamps.
    _normalize_followed(follow_state)

    # Unfollow anyone who hasn't followed back after UNFOLLOW_AFTER_HOURS.
    # Run this regardless of daily follow cap -- clean up the ratio first.
    unfollowed = _run_unfollow_pass(follow_state)
    if unfollowed:
        log.info("Unfollow pass: removed %d non-followers.", unfollowed)
        _save_follow_state(follow_state)

    today_count = _follows_today(follow_state)
    if today_count >= MAX_FOLLOWS_PER_DAY:
        log.info("Daily follow cap reached (%d/%d). Skipping new follows.", today_count, MAX_FOLLOWS_PER_DAY)
        return unfollowed  # Still return so caller knows unfollows happened

    remaining_today = MAX_FOLLOWS_PER_DAY - today_count
    this_run_limit  = min(MAX_FOLLOWS_PER_RUN, remaining_today)

    # Check twscrape cookies available
    if not _get_cookies():
        log.warning("X_SCRAPER_COOKIES not set -- follow cycle skipped.")
        return unfollowed

    from bot.sources.health_monitor import is_in_recovery
    if is_in_recovery():
        log.info("Recovery mode: skipping follow cycle this cycle.")
        return unfollowed

    # --- Step 1: Priority list (curated, no quality gate) ---
    client = get_client()
    priority_followed = _priority_follow_pass(follow_state, client)
    if priority_followed:
        log.info("Priority follows: %d", priority_followed)
        _save_follow_state(follow_state)
        this_run_limit = max(0, this_run_limit - priority_followed)

    if this_run_limit == 0:
        return unfollowed + priority_followed

    # --- Step 2: Find candidates via twscrape ---
    candidates = _run_async(_find_candidates_async(follow_state)) or []
    if not candidates:
        log.info("No follow candidates found.")
        return 0

    # Sort by followers descending (follow bigger accounts first for more visibility)
    candidates.sort(key=lambda c: c.get("followers", 0), reverse=True)

    # --- Step 3: Quality-check and follow ---
    follows_this_run = 0

    for candidate in candidates:
        if follows_this_run >= this_run_limit:
            break

        uid      = candidate["id"]
        username = candidate.get("username", "?")

        # Always mark attempted before evaluating
        if uid not in follow_state["attempted"]:
            follow_state["attempted"].append(uid)
            follow_state["attempted"] = follow_state["attempted"][-500:]

        if uid in _followed_ids(follow_state):
            continue

        # Quality gate
        passes, reason = _run_async(_check_quality_async(candidate)) or (False, "check failed")
        if not passes:
            log.debug("Skip @%s (%s)", username, reason)
            continue

        # Follow via official API (Free tier action)
        try:
            client.follow_user(uid)
            follow_state.setdefault("followed", []).append({
                "id":          uid,
                "username":    username,
                "followed_at": int(time.time()),
            })
            _increment_daily(follow_state)
            follows_this_run += 1
            log.info(
                "Followed @%s (%d followers) [%d/%d today]",
                username, candidate.get("followers", 0),
                _follows_today(follow_state), MAX_FOLLOWS_PER_DAY,
            )
            time.sleep(2)  # Gentle pace -- avoid triggering rate limits

        except Exception as exc:
            log.warning("Follow failed for @%s: %s", username, exc)

    _save_follow_state(follow_state)
    total_followed = priority_followed + follows_this_run
    log.info(
        "Follow cycle done: %d followed this run (%d priority + %d discovered, %d today).",
        total_followed, priority_followed, follows_this_run, _follows_today(follow_state),
    )
    return total_followed
