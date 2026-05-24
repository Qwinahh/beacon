"""
Authenticated X (Twitter) API client.

Wraps Tweepy and handles rate-limit errors gracefully.
All X operations go through this module — nothing else imports tweepy directly.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

import tweepy

from bot.config import ENV, require_env

log = logging.getLogger(__name__)

_client: Optional[tweepy.Client] = None


def get_client() -> tweepy.Client:
    """Return a cached, authenticated Tweepy v2 client."""
    global _client
    if _client is None:
        _client = tweepy.Client(
            consumer_key=require_env(ENV.x_api_key),
            consumer_secret=require_env(ENV.x_api_secret),
            access_token=require_env(ENV.x_access_token),
            access_token_secret=require_env(ENV.x_access_secret),
            wait_on_rate_limit=False,
        )
        log.debug("Tweepy client initialised.")
    return _client


def post_tweet(text: str, reply_to_id: Optional[str] = None) -> Optional[str]:
    """
    Post a tweet and return its ID, or None on failure.

    Args:
        text:         The tweet text (≤280 characters).
        reply_to_id:  If set, post as a reply to this tweet ID.
    """
    if len(text) > 280:
        log.error("Tweet exceeds 280 characters (%d). Aborting.", len(text))
        return None

    client = get_client()
    kwargs: dict = {"text": text}
    if reply_to_id:
        kwargs["in_reply_to_tweet_id"] = reply_to_id

    try:
        response = client.create_tweet(**kwargs)
        tweet_id = str(response.data["id"])
        log.info("Posted tweet %s: %s", tweet_id, text[:60])
        return tweet_id
    except tweepy.errors.Forbidden as exc:
        # Duplicate content, suspended account, etc.
        log.error("Tweet rejected (Forbidden): %s", exc)
        return None
    except tweepy.errors.TooManyRequests:
        log.warning("Rate limited. Will retry on next run.")
        return None
    except tweepy.errors.TweepyException as exc:
        log.error("Tweepy error posting tweet: %s", exc)
        return None


def get_mentions(since_id: Optional[str] = None) -> list[dict]:
    """
    Fetch recent mentions of the authenticated account.

    Requires X API Basic tier or above.
    Returns a list of tweet dicts with keys: id, text, author_id, conversation_id.
    """
    client = get_client()
    try:
        me = client.get_me()
        if not me or not me.data:
            return []
        user_id = me.data.id

        kwargs: dict = {
            "id": user_id,
            "tweet_fields": ["conversation_id", "author_id", "created_at"],
            "max_results": 20,
        }
        if since_id:
            kwargs["since_id"] = since_id

        resp = client.get_users_mentions(**kwargs)
        if not resp.data:
            return []

        return [
            {
                "id": str(t.id),
                "text": t.text,
                "author_id": str(t.author_id),
                "conversation_id": str(t.conversation_id),
            }
            for t in resp.data
        ]
    except tweepy.errors.Forbidden:
        log.warning("Mentions access denied — X API Basic tier required.")
        return []
    except tweepy.errors.TweepyException as exc:
        log.error("Error fetching mentions: %s", exc)
        return []
