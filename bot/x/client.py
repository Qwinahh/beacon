"""
Authenticated X (Twitter) API client.

Wraps Tweepy and handles rate-limit errors gracefully.
All X operations go through this module — nothing else imports tweepy directly.
"""
from __future__ import annotations

import logging
import os
import tempfile
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


def upload_media(image_bytes: bytes) -> "Optional[str]":
    """
    Upload image bytes via the v1.1 media endpoint and return a media_id
    string, or None on failure. Media upload still requires the v1.1 API
    with OAuth 1.0a (tweepy.API, not tweepy.Client). Non-fatal by design:
    callers post text-only when this returns None.
    """
    try:
        auth = tweepy.OAuth1UserHandler(
            require_env(ENV.x_api_key),
            require_env(ENV.x_api_secret),
            require_env(ENV.x_access_token),
            require_env(ENV.x_access_secret),
        )
        api_v1 = tweepy.API(auth)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name
        try:
            media = api_v1.media_upload(filename=tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        media_id = str(media.media_id)
        log.info("Media uploaded: %s (%d bytes)", media_id, len(image_bytes))
        return media_id
    except tweepy.errors.TweepyException as exc:
        log.warning("Media upload failed (non-fatal): %s", exc)
        return None
    except Exception as exc:
        log.warning("Media upload error (non-fatal): %s", exc)
        return None


def post_tweet(
    text: str,
    reply_to_id: Optional[str] = None,
    quote_tweet_id: Optional[str] = None,
    media_ids: Optional[list[str]] = None,
) -> Optional[str]:
    """
    Post a tweet and return its ID, or None on failure.

    Args:
        text:            The tweet text (≤280 characters).
        reply_to_id:     If set, post as a reply to this tweet ID.
        quote_tweet_id:  If set, post as a quote-tweet of this tweet ID.
                         Quote tweets appear in your own timeline; plain
                         replies do not — use this for high-value viral posts.
        media_ids:       Optional media IDs from upload_media() to attach.
    """
    if len(text) > 280:
        log.error("Tweet exceeds 280 characters (%d). Aborting.", len(text))
        return None

    client = get_client()
    kwargs: dict = {"text": text}
    if reply_to_id:
        kwargs["in_reply_to_tweet_id"] = reply_to_id
    if quote_tweet_id:
        kwargs["quote_tweet_id"] = quote_tweet_id
    if media_ids:
        kwargs["media_ids"] = media_ids

    try:
        response = client.create_tweet(**kwargs)
        tweet_id = str(response.data["id"])
        mode = "quote" if quote_tweet_id else ("reply" if reply_to_id else "post")
        log.info("Posted %s %s: %s", mode, tweet_id, text[:60])
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

    Tries the official API first (Basic tier). On Forbidden, falls back to
    twscrape cookie-based search (Free tier) via X_SCRAPER_COOKIES env var.
    Returns a list of tweet dicts with keys: id, text, author_id, conversation_id.
    """
    # --- Try official API (Basic tier) ---
    client = get_client()
    try:
        me = client.get_me()
        if me and me.data:
            user_id = me.data.id
            kwargs: dict = {
                "id": user_id,
                "tweet_fields": ["conversation_id", "author_id", "created_at"],
                "max_results": 20,
            }
            if since_id:
                kwargs["since_id"] = since_id
            resp = client.get_users_mentions(**kwargs)
            if resp.data:
                return [
                    {
                        "id": str(t.id),
                        "text": t.text,
                        "author_id": str(getattr(t, "author_id", "")),
                        "conversation_id": str(getattr(t, "conversation_id", "")),
                    }
                    for t in resp.data
                ]
            return []
    except tweepy.errors.Forbidden:
        log.info("Official mentions API needs Basic tier — falling back to twscrape.")
    except tweepy.errors.TweepyException as exc:
        log.warning("Official mentions fetch error: %s — trying twscrape.", exc)

    # --- Fallback: twscrape cookie-based search (Free tier) ---
    return _get_mentions_via_twscrape(since_id=since_id)


def _get_mentions_via_twscrape(since_id: Optional[str] = None) -> list[dict]:
    """
    Fetch @Qwinahh mentions using twscrape (cookie-based, no API tier required).
    Returns same format as get_mentions().
    """
    import asyncio
    import concurrent.futures
    import os

    cookies = os.environ.get("X_SCRAPER_COOKIES", "").strip()
    if not cookies:
        log.warning("X_SCRAPER_COOKIES not set — mentions unavailable.")
        return []

    async def _fetch():
        try:
            from twscrape import API
        except ImportError:
            return []

        api = API(os.path.join(tempfile.gettempdir(), "twscrape_pool.db"))
        try:
            await api.pool.add_account(
                username="beacon_mentions_scraper",
                password="placeholder",
                email="placeholder@placeholder.com",
                email_password="placeholder",
                cookies=cookies,
            )
        except Exception as exc:
            log.warning("twscrape mentions setup: %s", exc)
            return []

        results = []
        # Search for recent mentions, exclude our own tweets
        query = "@Qwinahh -from:Qwinahh lang:en"
        try:
            async for tweet in api.search(query, limit=20, kv={"product": "Latest"}):
                tweet_id = str(tweet.id)
                # If since_id given, skip tweets with ID <= since_id
                if since_id and int(tweet_id) <= int(since_id):
                    continue
                results.append({
                    "id": tweet_id,
                    "text": tweet.rawContent or "",
                    "author_id": str(tweet.user.id) if tweet.user else "",
                    "conversation_id": str(getattr(tweet, "conversationId", tweet.id) or tweet.id),
                })
        except Exception as exc:
            log.warning("twscrape mentions search error: %s", exc)

        return results

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, _fetch())
                return future.result(timeout=45) or []
        else:
            return loop.run_until_complete(_fetch()) or []
    except Exception as exc:
        log.warning("twscrape mentions runner error: %s", exc)
        return []


def quote_tweet(text: str, quote_tweet_id: str) -> Optional[str]:
    """
    Post a quote tweet and return its ID, or None on failure.

    Args:
        text:           The commentary text (≤280 characters).
        quote_tweet_id: The ID of the tweet being quoted.
    """
    if len(text) > 280:
        log.error("Quote tweet exceeds 280 characters (%d). Aborting.", len(text))
        return None

    client = get_client()
    try:
        response = client.create_tweet(text=text, quote_tweet_id=quote_tweet_id)
        tweet_id = str(response.data["id"])
        log.info("Quote-tweeted %s → new tweet %s: %s", quote_tweet_id, tweet_id, text[:60])
        return tweet_id
    except tweepy.errors.Forbidden as exc:
        log.error("Quote tweet rejected (Forbidden): %s", exc)
        return None
    except tweepy.errors.TooManyRequests:
        log.warning("Rate limited on quote tweet. Will retry on next run.")
        return None
    except tweepy.errors.TweepyException as exc:
        log.error("Tweepy error posting quote tweet: %s", exc)
        return None


def fetch_tweet_metrics(tweet_id: str) -> Optional[dict]:
    """
    Fetch public engagement metrics for a tweet we posted.

    Returns dict with keys: likes, replies, retweets, impressions (all int, default 0).
    Returns None on any error — callers must handle None gracefully.

    impressions requires Basic/Pro tier and will be 0 on the Free tier.
    """
    client = get_client()
    try:
        resp = client.get_tweet(tweet_id, tweet_fields=["public_metrics"])
        if resp.data is None:
            log.debug("fetch_tweet_metrics: no data for tweet %s.", tweet_id)
            return None
        pm = resp.data.public_metrics or {}
        return {
            "likes":       int(pm.get("like_count",       0) or 0),
            "replies":     int(pm.get("reply_count",      0) or 0),
            "retweets":    int(pm.get("retweet_count",    0) or 0),
            "impressions": int(pm.get("impression_count", 0) or 0),
        }
    except tweepy.errors.NotFound:
        log.debug("fetch_tweet_metrics: tweet %s not found.", tweet_id)
        return None
    except tweepy.errors.Forbidden as exc:
        log.warning("fetch_tweet_metrics forbidden for %s: %s", tweet_id, exc)
        return None
    except tweepy.errors.TooManyRequests:
        log.warning("Rate limited fetching metrics for %s — will retry next run.", tweet_id)
        return None
    except tweepy.errors.TweepyException as exc:
        log.error("fetch_tweet_metrics error for %s: %s", tweet_id, exc)
        return None
