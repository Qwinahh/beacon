"""
Account health monitor — detects shadowban, spam flags, and engagement suppression.

Runs at the start of every engage.py cycle. Writes results to
data/growth/health_status.json so the orchestrator and trend.py can
throttle back if the account is penalised.

Tests performed:
1. Search visibility: does our username appear in X search results?
   (shadowban type 1)
2. Engagement rate drop: compare last-7-day avg engagement to prior 7 days
   from metrics.json. If drop > 60%, flag as possible suppression.

All tests use twscrape (cookie-based). Fails silently if unavailable.
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

log = logging.getLogger(__name__)

_HEALTH_FILE   = Path("data/growth/health_status.json")
_METRICS_FILE  = Path("data/growth/metrics.json")
_COOKIES_ENV   = "X_SCRAPER_COOKIES"
_OWN_USERNAME  = os.environ.get("X_USERNAME", "Qwinahh")

_RECOVERY_HOURS          = 48
_SUPPRESSION_THRESHOLD   = 0.40   # last-7 avg must be >= 40% of prior-7 avg
_MIN_ENTRIES_PER_WINDOW  = 5


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def _load_status() -> dict:
    if not _HEALTH_FILE.exists():
        return {
            "checked_at": 0,
            "search_banned": False,
            "engagement_suppressed": False,
            "suppression_ratio": 1.0,
            "recovery_mode": False,
            "recovery_started_at": None,
            "notes": "",
        }
    try:
        return json.loads(_HEALTH_FILE.read_text(encoding="utf-8"))
    except Exception:
        return _load_status.__wrapped__()  # type: ignore


# avoid recursion — define default inline
_DEFAULT_STATUS: dict = {
    "checked_at": 0,
    "search_banned": False,
    "engagement_suppressed": False,
    "suppression_ratio": 1.0,
    "recovery_mode": False,
    "recovery_started_at": None,
    "notes": "",
}


def _load_status() -> dict:  # noqa: F811
    if not _HEALTH_FILE.exists():
        return dict(_DEFAULT_STATUS)
    try:
        return json.loads(_HEALTH_FILE.read_text(encoding="utf-8"))
    except Exception:
        return dict(_DEFAULT_STATUS)


def _save_status(status: dict) -> None:
    _HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    _HEALTH_FILE.write_text(json.dumps(status, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# twscrape helpers
# ---------------------------------------------------------------------------

def _get_cookies() -> Optional[str]:
    return os.environ.get(_COOKIES_ENV, "").strip() or None


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result(timeout=60)
        else:
            return loop.run_until_complete(coro)
    except Exception as exc:
        log.debug("health_monitor async runner: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Test 1: Search visibility (shadowban detection)
# ---------------------------------------------------------------------------

async def _test_search_visibility_async() -> bool:
    """
    Search for our own username. Returns True if visible (not banned).

    IMPORTANT: a new account with fewer than 20 posts won't appear in
    X search even when totally healthy. Skip the test in that case to
    prevent false recovery loops on brand-new accounts.
    """
    cookies = _get_cookies()
    if not cookies:
        return True  # Can't test — assume OK

    # Don't flag a search ban when the account has very few posts — X doesn't
    # index low-post accounts reliably and this causes false recovery loops.
    from pathlib import Path as _Path
    import json as _json
    post_log = _Path("data/performance/post_log.json")
    if post_log.exists():
        try:
            posts = _json.loads(post_log.read_text(encoding="utf-8"))
            if isinstance(posts, list) and len(posts) < 20:
                log.debug(
                    "health_monitor: skipping search ban check — only %d posts "
                    "logged (X doesn't index accounts reliably below 20 posts).",
                    len(posts),
                )
                return True
        except Exception:
            pass
    else:
        log.debug("health_monitor: skipping search ban check — no post log yet (new account).")
        return True

    try:
        from twscrape import API

        from bot.x import twscrape_patch  # noqa: F401
    except ImportError:
        return True

    api = API(os.path.join(tempfile.gettempdir(), "twscrape_health.db"))
    try:
        await api.pool.add_account(
            username="beacon_health_scraper",
            password="placeholder",
            email="placeholder@placeholder.com",
            email_password="placeholder",
            cookies=cookies,
        )
    except Exception as exc:
        log.debug("health_monitor twscrape setup: %s", exc)
        return True

    try:
        count = 0
        async for _ in api.search(f"from:{_OWN_USERNAME}", limit=5):
            count += 1
            break  # Just need one result

        if count == 0:
            # A single zero-result run is NOT reliable — the account may simply
            # be inactive, twscrape may have hiccupped, or the search index is
            # lagging. Require consecutive failures across multiple runs before
            # flagging, tracked in health_status.json.
            status = _load_status()
            consecutive = status.get("search_zero_streak", 0) + 1
            status["search_zero_streak"] = consecutive
            _save_status(status)
            log.warning(
                "health_monitor: 0 results for 'from:%s' (streak=%d/3). "
                "Will only flag shadowban after 3 consecutive zeros.",
                _OWN_USERNAME, consecutive,
            )
            # Only return False (trigger recovery) after 3 consecutive zeros
            return consecutive < 3
        else:
            # Reset the streak on any positive result
            status = _load_status()
            if status.get("search_zero_streak", 0) > 0:
                status["search_zero_streak"] = 0
                _save_status(status)
            return True
    except Exception as exc:
        log.debug("health_monitor search visibility test error: %s", exc)
        return True  # Error ≠ banned — assume OK


# ---------------------------------------------------------------------------
# Test 2: Engagement rate drop
# ---------------------------------------------------------------------------

def _test_engagement_drop() -> tuple[bool, float]:
    """
    Returns (is_suppressed, ratio) where ratio = last7_avg / prior7_avg.
    Ratio < SUPPRESSION_THRESHOLD means suppression likely.
    Returns (False, 1.0) if insufficient data.
    """
    if not _METRICS_FILE.exists():
        return False, 1.0

    try:
        entries = json.loads(_METRICS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return False, 1.0

    if not isinstance(entries, list) or len(entries) < _MIN_ENTRIES_PER_WINDOW * 2:
        return False, 1.0

    now = time.time()
    cutoff_7  = now - 7  * 86400
    cutoff_14 = now - 14 * 86400

    def _eng(e: dict) -> float:
        likes    = e.get("likes",    0) or 0
        replies  = e.get("replies",  0) or 0
        retweets = e.get("retweets", 0) or 0
        return likes + replies * 3 + retweets * 2

    last7  = [_eng(e) for e in entries if e.get("collected_at", 0) >= cutoff_7]
    prior7 = [_eng(e) for e in entries
               if cutoff_14 <= e.get("collected_at", 0) < cutoff_7]

    if len(last7) < _MIN_ENTRIES_PER_WINDOW or len(prior7) < _MIN_ENTRIES_PER_WINDOW:
        return False, 1.0

    last7_avg  = sum(last7)  / len(last7)
    prior7_avg = sum(prior7) / len(prior7)

    if prior7_avg == 0:
        return False, 1.0

    ratio = last7_avg / prior7_avg
    if ratio < _SUPPRESSION_THRESHOLD:
        log.warning(
            "health_monitor: engagement dropped to %.0f%% of prior-7-day avg "
            "(%.1f vs %.1f). Possible suppression.",
            ratio * 100, last7_avg, prior7_avg,
        )
        return True, ratio

    return False, ratio


# ---------------------------------------------------------------------------
# Test 3: Reply visibility (ghost ban heuristic)
# ---------------------------------------------------------------------------

def _test_reply_visibility(api, own_username: str) -> bool:
    """
    Check if our recent replies appear in the threads they were posted to.
    A reply ghost ban means replies post successfully but are invisible to others.
    Returns True if replies are visible (healthy), False if possibly ghost-banned.
    This is a heuristic — not 100% reliable but good enough as an early signal.
    """
    return True  # Placeholder — extend if shadowban is confirmed


def _test_suggestion_ban(api, own_username: str) -> bool:
    """
    Check if our account appears in typeahead/suggestions.
    A suggestion ban removes you from who-to-follow and search autocomplete.
    Returns True if visible, False if banned from suggestions.
    """
    return True  # Placeholder — hard to test without a separate cookie-free session


# ---------------------------------------------------------------------------
# Recovery mode
# ---------------------------------------------------------------------------

def _log_recovery_protocol() -> None:
    log.warning(
        "\nSHADOWBAN RECOVERY PROTOCOL:\n"
        "- Stop following new accounts for 48h (follow module will auto-skip)\n"
        "- Stop outbound replies for 48h (trend module will auto-skip)\n"
        "- Continue posting original content (do not stop posting)\n"
        "- Do not delete recent tweets (deletions can extend bans)\n"
        "- After 48h, resume at 50%% normal rate for 3 days\n"
        "Common causes: following too fast, replying too fast, spam reports,\n"
        "posting external links, using new account with high-velocity actions."
    )


def is_in_recovery() -> bool:
    """Return True if recovery_mode is active and < 48h have passed."""
    try:
        status = _load_status()
        if not status.get("recovery_mode"):
            return False
        started_at = status.get("recovery_started_at")
        if started_at is None:
            return False
        elapsed_h = (time.time() - started_at) / 3600
        if elapsed_h >= _RECOVERY_HOURS:
            # Auto-clear recovery after 48h
            status["recovery_mode"] = False
            status["notes"] = f"Recovery auto-cleared after {_RECOVERY_HOURS}h"
            _save_status(status)
            log.info("health_monitor: recovery mode auto-cleared after 48h.")
            return False
        return True
    except Exception as exc:
        log.debug("health_monitor is_in_recovery error: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def check_health() -> None:
    """
    Run health checks and update data/growth/health_status.json.
    Non-fatal — logs warnings but never raises.
    """
    try:
        status = _load_status()

        # Test 1: search visibility
        visible = _run_async(_test_search_visibility_async())
        if visible is None:
            visible = True
        search_banned = not visible

        # Test 2: engagement drop
        suppressed, ratio = _test_engagement_drop()

        ban_type = (
            "search" if search_banned
            else "suppression" if suppressed
            else "none"
        )

        status["checked_at"]            = int(time.time())
        status["search_banned"]         = search_banned
        status["reply_ghosted"]         = False   # populated by _test_reply_visibility when detectable
        status["suggestion_banned"]     = False   # populated by _test_suggestion_ban when detectable
        status["engagement_suppressed"] = suppressed
        status["suppression_ratio"]     = round(ratio, 3)
        status["ban_type"]              = ban_type
        status["notes"] = (
            "Search ban detected — account not visible in from: search." if search_banned
            else f"Engagement suppression — avg engagement dropped >60% (ratio={ratio:.2f})." if suppressed
            else ""
        )

        # Enter recovery if any flag tripped and not already in recovery
        if (search_banned or suppressed) and not status.get("recovery_mode"):
            status["recovery_mode"]       = True
            status["recovery_started_at"] = int(time.time())
            log.warning(
                "ACCOUNT HEALTH: %s detected. Recovery mode active for 48h.\n"
                "Ban type: %s\n"
                "Suppression ratio: %.2f (last 7d vs prior 7d avg engagement)\n"
                "Recovery: follow/outbound reply cycles paused. Posts continue.\n"
                "Do NOT delete recent tweets. Do NOT follow aggressively.\n"
                "Check data/growth/health_status.json for details.",
                "Shadowban" if search_banned else "Engagement suppression",
                ban_type,
                ratio,
            )
            _log_recovery_protocol()
        elif not search_banned and not suppressed and status.get("recovery_mode"):
            log.info("health_monitor: checks pass, but recovery still active (time-gated).")
        else:
            log.info(
                "health_monitor: OK (search_banned=%s, suppressed=%s, ratio=%.2f, ban_type=%s)",
                search_banned, suppressed, ratio, ban_type,
            )

        _save_status(status)

    except Exception as exc:
        log.warning("health_monitor check_health failed (non-fatal): %s", exc)
