"""
Main posting entry point.

Delegates the full posting cycle to the OrchestratorAgent. The orchestrator
coordinates Scout → Analyst → Writer and makes the final call on what to post.

Usage:
    python post.py               # Normal posting window check
    python post.py --alpha-only  # Only post urgency-3 signals (runs every 30min)
"""
from __future__ import annotations

import argparse
import logging
import random
import sys
import time

from agents.orchestrator import run_post_cycle
from bot.config import (
    MAX_POSTS_PER_DAY,
    MIN_HOURS_BETWEEN_POSTS,
    POSTING_WINDOWS,
    POST_JITTER_SECONDS,
    THREAD_CHANCE,
)
from bot.state import State

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# In alpha-only mode, enforce a shorter cooldown so urgent news can break through.
ALPHA_MIN_HOURS_BETWEEN_POSTS = 1.0


def _within_posting_window() -> bool:
    import datetime
    hour = datetime.datetime.now(datetime.timezone.utc).hour
    return any(start <= hour < end for start, end in POSTING_WINDOWS)


def _hours_since(ts: float) -> float:
    return (time.time() - ts) / 3600.0


def _has_urgent_alpha() -> bool:
    """
    Quick pre-check: are there any urgency-3 signals right now?
    Used to bail out of the 30-min alpha workflow early without spinning up
    the full agent pipeline.
    """
    try:
        from bot.sources.alpha import detect_all
        signals = detect_all()
        return any(s.urgency >= 3 for s in signals)
    except Exception as exc:
        log.warning("Alpha pre-check failed: %s", exc)
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--alpha-only",
        action="store_true",
        help="Only post if there is an urgency-3 alpha signal. "
             "Used by the 30-minute fast-track workflow.",
    )
    args = parser.parse_args()
    alpha_only = args.alpha_only

    state = State()
    state.load()

    # Daily cap applies in all modes.
    if state.posts_today() >= MAX_POSTS_PER_DAY:
        log.info("Daily cap reached (%d). Exiting.", MAX_POSTS_PER_DAY)
        sys.exit(0)

    # Cooldown check — shorter window in alpha mode so breaking news can land.
    last_ts = state.last_post_timestamp()
    cooldown = ALPHA_MIN_HOURS_BETWEEN_POSTS if alpha_only else MIN_HOURS_BETWEEN_POSTS
    if last_ts and _hours_since(last_ts) < cooldown:
        log.info(
            "Too soon since last post (%.1fh ago, cooldown %.1fh). Exiting.",
            _hours_since(last_ts), cooldown,
        )
        sys.exit(0)

    if alpha_only:
        # Fast pre-check before spinning up the full agent pipeline.
        if not _has_urgent_alpha():
            log.info("Alpha-only mode: no urgency-3 signals found. Exiting.")
            sys.exit(0)
        log.info("Alpha-only mode: urgency-3 signal detected — proceeding.")
    else:
        # Normal mode: respect posting windows.
        if not _within_posting_window():
            log.info("Outside posting windows. Exiting.")
            sys.exit(0)

    # Random jitter so posts never look mechanical (shorter in alpha mode).
    max_jitter = min(POST_JITTER_SECONDS, 120) if alpha_only else POST_JITTER_SECONDS
    jitter = random.randint(0, max_jitter)
    if jitter:
        log.info("Jitter: waiting %ds.", jitter)
        time.sleep(jitter)

    # THREAD MODE: 15% of normal cycles attempt a 3-5 tweet thread.
    # Checked before freeform — falls through to freeform (then normal pipeline) on failure.
    if not alpha_only and random.random() < THREAD_CHANCE:
        try:
            import json as _json
            from bot.brain.writer import generate_thread
            from bot.config import PORTFOLIO_PATH
            from bot.x.client import get_client, post_tweet
            log.info("Post cycle: attempting thread post (%.0f%% mode)", THREAD_CHANCE * 100)
            _portfolio: dict = {}
            try:
                with open(PORTFOLIO_PATH) as _f:
                    _portfolio = _json.load(_f)
            except Exception:
                pass
            thread_tweets = generate_thread(
                item=None,
                portfolio=_portfolio,
                recent_formats=state.recent_formats(),
            )
            if thread_tweets:
                tweet_ids: list[str] = []
                prev_id = None
                failed = False
                for i, tweet_text in enumerate(thread_tweets):
                    if i == 0:
                        tid = post_tweet(tweet_text)
                    else:
                        if prev_id is None:
                            failed = True
                            break
                        try:
                            resp = get_client().create_tweet(
                                text=tweet_text,
                                in_reply_to_tweet_id=prev_id,
                            )
                            tid = str(resp.data["id"])
                            log.info("Thread tweet %d/%d: %s", i + 1, len(thread_tweets), tweet_text[:60])
                        except Exception as exc:
                            log.warning("Thread tweet %d failed: %s", i + 1, exc)
                            failed = True
                            break
                    if tid is None:
                        failed = True
                        break
                    tweet_ids.append(str(tid))
                    prev_id = str(tid)

                if not failed and tweet_ids:
                    state.increment_post_count()
                    state.set_last_post_timestamp(time.time())
                    fp = state.fingerprint(thread_tweets[0].lower())
                    state.mark_seen(fp)
                    state.record_topic("opinion")
                    state.record_format("thread")
                    ids_list: list = state._data.setdefault("thread_tweet_ids", [])
                    ids_list.append({"ts": time.time(), "ids": tweet_ids})
                    state._data["thread_tweet_ids"] = ids_list[-20:]
                    try:
                        from bot.brain.vault import log_post
                        log_post(thread_tweets[0], "opinion", "thread")
                    except Exception:
                        pass
                    state.save()
                    log.info("Thread posted (%d tweets): %s", len(tweet_ids), thread_tweets[0][:80])
                    return
                elif tweet_ids:
                    log.debug("Thread partial (%d/%d) — not recording, falling through", len(tweet_ids), len(thread_tweets))
            log.debug("Thread attempt: no qualifying thread generated, falling through to freeform")
        except Exception as exc:
            log.warning("Thread mode failed: %s — falling through to freeform", exc)

    # FREEFORM MODE: 30% of normal cycles post a pure opinion instead of data-driven content.
    # Top accounts post this way constantly — not tied to any specific event.
    # Never in alpha-only mode (breaking news takes full priority).
    if not alpha_only and random.random() < 0.30:
        try:
            from bot.brain.freeform_writer import generate_freeform
            from bot.x.client import post_tweet
            log.info("Post cycle: attempting freeform opinion post (30% mode)")
            freeform_text = generate_freeform(
                recent_formats=state.recent_formats(),
                recent_topics=state.recent_topics(),
            )
            if freeform_text:
                tweet_id = post_tweet(freeform_text)
                if tweet_id:
                    state.increment_post_count()
                    state.set_last_post_timestamp(time.time())
                    fp = state.fingerprint(freeform_text.lower())
                    state.mark_seen(fp)
                    state.record_topic("opinion")
                    state.record_format("freeform")
                    try:
                        from bot.brain.vault import log_post
                        log_post(freeform_text, "opinion", "freeform")
                    except Exception:
                        pass
                    state.save()
                    log.info("Freeform post sent: %s", freeform_text[:80])
                    return
            log.debug("Freeform attempt: no qualifying post generated, falling through to normal pipeline")
        except Exception as exc:
            log.warning("Freeform mode failed: %s — falling through to normal pipeline", exc)

    result = run_post_cycle(state, alpha_only=alpha_only)

    action = result.get("action", "skipped")
    log.info("Done. Action: %s | %s", action, result.get("reason", "")[:100])

    # Guaranteed fallback: if the full pipeline found nothing AND it has been
    # over 6 hours since the last post, generate a freeform opinion post.
    # Ensures the bot always posts on schedule during slow news days.
    if action == "skipped" and not alpha_only and _hours_since(state.last_post_timestamp()) > 6.0:
        try:
            from bot.brain.freeform_writer import generate_freeform
            from bot.x.client import post_tweet
            fallback_text = generate_freeform(state.recent_formats(), state.recent_topics())
            if fallback_text:
                posted = post_tweet(fallback_text)
                if posted:
                    state.increment_post_count()
                    state.set_last_post_timestamp(time.time())
                    state.record_format("short_take")
                    state.record_topic("freeform")
                    state.save()
                    log.info("Guaranteed fallback post used — normal pipeline found nothing")
                    sys.exit(0)
        except Exception as exc:
            log.warning("Guaranteed fallback failed: %s", exc)

    state.save()

    if action == "skipped":
        sys.exit(0)


if __name__ == "__main__":
    main()
