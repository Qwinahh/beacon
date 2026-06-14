"""
bot/x/trend.py -- Proactive outbound engagement.

WHY THIS MODULE EXISTS -- the follower acquisition funnel:

  When @Qwinahh replies to a post by an account with 50k-200k followers,
  everyone reading that thread sees the reply. Of those readers:
    ~5-10% click the profile if the reply is specific and credible
    ~10-20% of profile visitors follow if the pinned post + recent posts are good

  Net result: 1 great reply to a 100k-follower account = 5-20 new followers.
  1 mediocre reply = 0 new followers and a slight credibility cost.

  This means:
    - 3-4 EXCELLENT replies per day > 40 mediocre replies
    - Who you reply to matters as much as what you say
    - Timing matters: reply within 60 minutes while the post is still being read

HOW READING WORKS (FREE TIER):
  All tweet discovery uses twscrape -- cookie-based X scraping via GraphQL.
  No X API tier is needed to READ tweets. Only the official API (Tweepy) is
  used for POST /tweet (posting replies), which is available on the Free tier.

  Setup: set X_SCRAPER_COOKIES in GitHub Secrets as:
    ct0=<value>; auth_token=<value>
  Get these from browser DevTools -> Application -> Cookies -> x.com

WHY THE LIMITS ARE WHAT THEY ARE:
  - 6 outbound replies per day cap (combined with state.MAX_REPLIES_PER_DAY=8):
    * More than ~8-10/day looks like spam to followers and to X's algo
    * Engagement rate per reply collapses after 6-8/day
  - 1 hour freshness window for targeted accounts (not 3h):
    * Reply notifications are only seen while the post is active in feeds
    * A reply at 2h is 10x less visible than a reply at 20 minutes
  - Max 1 reply per account per day:
    * Replying twice to the same person looks like following/harassment

TWO ENGAGEMENT MODES:
  1. TARGETED ACCOUNT MONITORING -- curated list of DeFi/perps/airdrop accounts.
  2. KEYWORD SEARCH -- catches high-engagement trending posts not on the watchlist.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import os
import tempfile
import time
from datetime import timezone
from typing import Optional

from bot.brain.llm import complete as llm_complete
from bot.config import CLAUDE_MAX_TOKENS, FOCUS_KEYWORDS
from bot.portfolio.tracker import load_portfolio
from bot.state import State
from bot.x.client import post_tweet

log = logging.getLogger(__name__)

_COOKIES_ENV = "X_SCRAPER_COOKIES"

# Per-run caps
MAX_PER_RUN = 3

# Reply freshness windows (minutes)
TARGETED_FRESHNESS_MINUTES = 60
KEYWORD_FRESHNESS_MINUTES  = 90

MIN_FOLLOWERS_FOR_TARGETED = 5_000

_KEYWORD_QUERIES = [
    # Active niche — posts that are live conversations, not broadcasts
    "hyperliquid perp funding lang:en min_faves:8",
    "defi airdrop points farm lang:en min_faves:5",
    "kaito yap leaderboard lang:en min_faves:5",
    "perp dex funding rate lang:en min_faves:10",
    "solana defi yield lang:en min_faves:8",
    "crypto airdrop criteria snapshot lang:en min_faves:5",
    "pendle yield steth lang:en min_faves:5",
    "hyperliquid vault hlp lang:en min_faves:5",
    "ethena sena usde yield lang:en min_faves:8",
    "morpho aave lending rate lang:en min_faves:8",
    # Wrong-take hunting — high-engagement posts with sloppy analysis.
    # We only reply when we have specific data to back a counter-take.
    "funding rates negative therefore bullish lang:en min_faves:30",
    "funding rates high bearish signal lang:en min_faves:30",
    "defi is dead no one uses it lang:en min_faves:40",
    "bitcoin dominance rising altseason over lang:en min_faves:25",
    "perps dex cant beat cex volume lang:en min_faves:20",
    "stablecoin yield free money lang:en min_faves:15",
]

_DEFAULT_TARGET_ACCOUNTS = [
    "DefiIgnas",
    "HsakaTrades",
    "Founderization",
    "zkDrops",
    "Pentosh1",
    "0xMaki",
    "0xHamz",
    "CroissantEth",
    "SmolRefund",
    "0xSisyphus",
    "Route2FI",
    "thedefiedge",
    "Gainzy222",
    "tayvano_",
    "deFIYIelded",
    "MilkyWayDeFi",
    "functi0nZer0",
    "EigenLayerNews",
]

# Viral posts get quote-tweeted instead of plain replied.
# Quote tweets show up in your own timeline; plain replies don't.
QUOTE_TWEET_LIKES_THRESHOLD  = 500    # >500 likes = genuinely viral in DeFi niche
QUOTE_TWEET_MAX_AGE_MINUTES  = 120    # Only quote posts still in active feeds

_QUOTE_SYSTEM = """\
You write quote-tweets for @Qwinahh -- a crypto account that trades perps,
farms airdrops, and moves into DeFi protocols before narratives form.

A QUOTE TWEET IS DIFFERENT FROM A REPLY:
- It shows up in your own timeline, not just buried in the thread
- Your audience sees it independent of the original post
- You must add REAL value -- not just "+1" or "great point"

The best quote tweets do one of:
  A. Extend with data: "This + [specific number/mechanic they missed]"
  B. Reframe: take the same fact but from the angle of someone actually farming it
  C. Contradict with data: "Actually the [specific metric] shows the opposite"
  D. Add implication: "This means [specific thing] for people farming [X]"

HARD RULES:
- Under 240 characters
- Must stand alone -- readers may not click through to the original
- No "Great point", no "This!", no restating what the original already said
- No hashtags, no emojis
- If you cannot add genuine value: respond with SKIP

OUTPUT FORMAT:
  QUOTE: [your quote-tweet text]
  SKIP: [one-word reason]
"""

_REPLY_SYSTEM = """\
You write outbound replies for @Qwinahh -- a crypto account that trades perps,
farms airdrops, and moves into DeFi protocols before narratives form.

THE GOAL OF EVERY REPLY:
Make the person reading it think "who IS this?" and click the profile.
That is the only metric that matters. Not likes. Not agreement. Profile clicks.

The best possible outcome is the original author replies back to you.
X's algorithm weights an author reply-back at 75-150x a like -- it is the
single highest-value engagement signal available. Write something the author
would actually want to respond to: a number they missed, a data point that
reframes their take, or a question that rewards them for answering.

A reply achieves this when it:
1. Adds something the original tweet didn't say -- a specific number,
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
  nothing specific to add: use the SKIP format below.

OUTPUT FORMAT — respond with exactly one of:
  REPLY: [your reply text under 220 chars]
  SKIP: [one-word reason: hostile/spam/vague/no_value]

Examples:
  REPLY: OI up but HLP utilisation still 34%. More TVL than traders right now.
  SKIP: vague

Never output anything else. No explanation before REPLY/SKIP.

EXAMPLES OF REPLIES WORTH SENDING:
Tweet: "Hyperliquid TVL up 40% this week"
Reply: "OI up too but HLP utilisation is only 34%. More TVL than traders to take the other side right now."

Tweet: "Kaito points season 2 is live, time to farm"
Reply: "Engagement-to-point ratio is 3x worse than S1. Farm is already crowded."

Tweet: "DeFi summer vibes with all these new protocols launching"
Reply: SKIP (vague, no data, nothing to add)

EXAMPLES OF REPLIES NOT WORTH SENDING:
"Agreed, this is a really important development for the space." -> SKIP
"Great take, been watching this closely too." -> SKIP
"This!" -> SKIP

WRONG-TAKE REPLIES (highest engagement on CT):
When the original tweet makes a claim you have specific data to contradict,
you can push back. The key: you must have DATA, not just an opinion.
  "funding negative = bullish" tweets -> counter with: "negative funding
    means shorts are paying longs. historically flip to positive before moves."
  "tvl up = price up" tweets -> counter with: "TVL and price decouple constantly.
    check hyperliquid Q1: tvl 3x'd, HYPE -40%."
  "defi dead" tweets -> counter with: real TVL/volume numbers from defillama
If you don't have specific data to back a counter: SKIP, don't opinion-only disagree.
"""


# ---------------------------------------------------------------------------
# Content quality helpers
# ---------------------------------------------------------------------------

_CRYPTO_HARD_SIGNALS = [
    "$", "btc", "eth", "sol", "defi", "perp", "airdrop", "tvl",
    "yield", "liquidity", "protocol", "token", "blockchain", "dex",
    "funding", "leverage", "long", "short", "farm", "points", "kaito",
    "hyperliquid", "arbitrum", "base chain", "layer 2",
]


def _is_crypto_tweet(text: str) -> bool:
    """Basic check that a tweet is about crypto/DeFi, not a coincidental keyword match."""
    lower = text.lower()
    return any(s in lower for s in _CRYPTO_HARD_SIGNALS)


# ---------------------------------------------------------------------------
# twscrape helpers
# ---------------------------------------------------------------------------

def _get_cookies() -> Optional[str]:
    return os.environ.get(_COOKIES_ENV, "").strip() or None


async def _make_api():
    """Create and authenticate a twscrape API instance."""
    try:
        from twscrape import API
    except ImportError:
        log.warning("twscrape not installed. Run: pip install twscrape")
        return None

    cookies = _get_cookies()
    if not cookies:
        log.warning("X_SCRAPER_COOKIES not set -- engagement reading unavailable.")
        return None

    api = API(os.path.join(tempfile.gettempdir(), "twscrape_pool.db"))
    try:
        await api.pool.add_account(
            username="beacon_scraper",
            password="placeholder",
            email="placeholder@placeholder.com",
            email_password="placeholder",
            cookies=cookies,
        )
    except Exception as exc:
        log.warning("twscrape account setup failed: %s", exc)
        return None
    return api


def _age_minutes(tweet_date) -> float:
    """Return age in minutes of a twscrape tweet.date (timezone-aware datetime)."""
    if not tweet_date:
        return 0.0
    try:
        now = time.time()
        ts = tweet_date.timestamp()
        return (now - ts) / 60.0
    except Exception:
        return 0.0


def _run_async(coro):
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
        log.warning("Async runner error: %s", exc)
        return None


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


# ---------------------------------------------------------------------------
# Vault personality injection -- replies must be consistent with documented
# positions (data/vault/projects/*.md Stance + X Consensus sections and the
# persona's Strong Positions). See data/vault/knowledge/reply-strategy.md.
# ---------------------------------------------------------------------------

_persona_positions_cache: Optional[str] = None


def _persona_positions() -> str:
    """Strong Positions section of the vault persona, cached per process."""
    global _persona_positions_cache
    if _persona_positions_cache is not None:
        return _persona_positions_cache
    try:
        from pathlib import Path
        from bot.config import VAULT_PERSONA_PATH
        text = Path(VAULT_PERSONA_PATH).read_text(encoding="utf-8")
        section = ""
        capture = False
        for line in text.splitlines():
            if line.startswith("## "):
                capture = line.strip().lower() == "## strong positions"
                continue
            if capture:
                section += line + "\n"
        _persona_positions_cache = section.strip()[:2000]
    except Exception as exc:
        log.debug("Persona positions unavailable: %s", exc)
        _persona_positions_cache = ""
    return _persona_positions_cache


def _vault_reply_context(tweet_text: str) -> str:
    """
    If the tweet mentions a protocol we have a vault project file for,
    return that project's documented Stance and X Consensus so the reply
    is consistent with -- and can push back using -- our positions.
    """
    try:
        from bot.brain.vault import PROJ_DIR, read_project
    except Exception:
        return ""

    lower = tweet_text.lower()
    parts: list = []
    try:
        for path in sorted(PROJ_DIR.glob("*.md")):
            name = path.stem
            if name in ("general",) or len(name) < 3:
                continue
            if name not in lower and name.replace("-", " ") not in lower:
                continue
            data = read_project(name)
            if not data:
                continue
            seg = ["YOUR DOCUMENTED POSITION ON %s:" % data["name"].upper()]
            if data.get("stance"):
                seg.append("Stance: " + " ".join(data["stance"].split())[:400])
            if data.get("x_consensus"):
                seg.append("Where CT consensus is wrong: "
                           + " ".join(data["x_consensus"].split())[:300])
            if len(seg) > 1:
                parts.append("\n".join(seg))
            if len(parts) >= 2:
                break
    except Exception as exc:
        log.debug("Vault reply context failed (non-fatal): %s", exc)

    return "\n\n".join(parts)



def _parse_reply(raw: str) -> Optional[str]:
    """Parse structured REPLY:/SKIP: response from LLM."""
    if not raw:
        return None
    raw = raw.strip()

    if raw.upper().startswith("REPLY:"):
        text = raw[6:].strip()
        return text if len(text) >= 15 else None

    if raw.upper().startswith("SKIP"):
        return None

    # Fallback: treat unstructured output as a reply if it looks like one
    if len(raw) <= 280 and not any(
        raw.lower().startswith(w) for w in ["i'll skip", "skipping", "not worth", "no value"]
    ):
        return raw if len(raw) >= 15 else None

    return None


def _generate_quote_tweet(tweet_text: str, author_username: str, portfolio: dict):
    """Generate a quote-tweet for a viral post. Returns text or None."""
    portfolio_ctx = _portfolio_context(portfolio)
    prompt = (
        f"Viral tweet by @{author_username} ({tweet_text[:280]})\n\n"
        f"{portfolio_ctx}\n\n"
        "Write a quote-tweet that adds real value for someone actively farming or trading DeFi. "
        "Use the QUOTE:/SKIP: format."
    )
    raw = llm_complete(system=_QUOTE_SYSTEM, user=prompt, max_tokens=CLAUDE_MAX_TOKENS, temperature=0.75)
    if not raw:
        return None
    raw = raw.strip()
    if raw.upper().startswith("QUOTE:"):
        text = raw[6:].strip()
        if len(text) < 15:
            return None
        if len(text) > 280:
            text = text[:276].rsplit(".", 1)[0] + "."
        try:
            from bot.brain.authenticity_judge import passes as judge_passes
            ok, result = judge_passes(text, content_type="reply")
            if not ok:
                log.info("Quote-tweet failed authenticity (score=%d): %s", result["score"], text[:60])
                return None
        except Exception as exc:
            log.debug("Quote judge error: %s -- proceeding", exc)
        return text
    return None


def _generate_reply(tweet_text: str, author_username: str, portfolio: dict) -> Optional[str]:
    portfolio_ctx = _portfolio_context(portfolio)
    prompt = f"Tweet by @{author_username}:\n\n{tweet_text}"
    if portfolio_ctx:
        prompt += f"\n\n{portfolio_ctx}"

    # Inject documented vault positions so the reply is consistent with --
    # and pushes back using -- our stances, not generic takes.
    vault_ctx = _vault_reply_context(tweet_text)
    if vault_ctx:
        prompt += (
            f"\n\n{vault_ctx}\n\n"
            "Your reply MUST be consistent with the documented position above. "
            "If the tweet contradicts your stance, push back with the documented "
            "view and its data -- politely, once, no beef."
        )

    positions = _persona_positions()
    if positions:
        prompt += (
            "\n\nYOUR STANDING POSITIONS (persona -- stay consistent with these):\n"
            + positions[:1200]
        )

    prompt += (
        "\n\nWrite a reply that would make someone click the profile. "
        "Use the REPLY:/SKIP: format from the system prompt."
    )
    raw = llm_complete(system=_REPLY_SYSTEM, user=prompt, max_tokens=CLAUDE_MAX_TOKENS, temperature=0.72)
    reply = _parse_reply(raw)
    if reply and len(reply) > 280:
        reply = reply[:276].rsplit(".", 1)[0] + "."
    return reply


# ---------------------------------------------------------------------------
# Mode 1: Targeted account monitoring (twscrape)
# ---------------------------------------------------------------------------

async def _engage_targeted_async(state: State, portfolio: dict, budget: int) -> int:
    api = await _make_api()
    if not api:
        return 0

    target_accounts = _load_target_accounts()
    already_replied = state.last_replied_to()
    sent = 0

    for username in target_accounts:
        if sent >= budget or state.at_daily_reply_cap():
            break

        if state.times_engaged_account_recently(username, window=20) >= 1:
            log.debug("Already engaged @%s recently, skipping.", username)
            continue

        try:
            user = await api.user_by_login(username)
            if not user:
                continue

            followers = getattr(user, "followersCount", 0) or 0
            if followers < MIN_FOLLOWERS_FOR_TARGETED:
                log.debug("@%s has %d followers, below minimum.", username, followers)
                continue

            user_id = user.id
            collected = []
            async for tweet in api.user_tweets(user_id, limit=5):
                collected.append(tweet)
                if len(collected) >= 5:
                    break

            for tweet in collected:
                tweet_id = str(tweet.id)
                if tweet_id in already_replied:
                    continue

                age = _age_minutes(getattr(tweet, "date", None))
                if age > TARGETED_FRESHNESS_MINUTES:
                    continue

                # Skip retweets
                content = tweet.rawContent or ""
                if content.startswith("RT @"):
                    continue

                # Only skip hard non-crypto content (FOCUS_KEYWORDS gate removed —
                # we curated these accounts; their non-keyword posts are still on-topic)
                if not _is_crypto_tweet(content):
                    log.debug("Skipping non-crypto tweet from @%s", username)
                    continue

                # Engagement floor (not a dud post)
                likes   = getattr(tweet, "likeCount", 0) or 0
                replies = getattr(tweet, "replyCount", 0) or 0
                if likes < 1 and replies < 1:
                    continue

                # High-engagement posts get quote-tweeted (show in own timeline).
                # Plain replies are buried; quote tweets surface to our followers.
                is_viral = (
                    likes >= QUOTE_TWEET_LIKES_THRESHOLD
                    and age <= QUOTE_TWEET_MAX_AGE_MINUTES
                )
                if is_viral:
                    quote_text = _generate_quote_tweet(content, username, portfolio)
                    if quote_text:
                        sent_id = post_tweet(quote_text, quote_tweet_id=tweet_id)
                        if sent_id:
                            state.mark_replied(tweet_id)
                            state.increment_reply_count()
                            state.mark_engaged_account(username)
                            sent += 1
                            log.info(
                                "Quote-tweeted @%s (%d likes, %.0fmin old): %s",
                                username, likes, age, quote_text[:70],
                            )
                            break
                    # Fall through to plain reply if quote generation failed

                reply_text = _generate_reply(content, username, portfolio)
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
                        "Replied to @%s (%dk followers, %.0fmin old): %s",
                        username, followers // 1000, age, reply_text[:70],
                    )
                    break  # One reply per account per run

        except Exception as exc:
            log.debug("Error processing @%s: %s", username, exc)
            continue

    if sent == 0:
        log.info(
            "Targeted engagement: 0 sent. cookie=%s, accounts_checked=%d",
            bool(_get_cookies()), len(target_accounts),
        )
    return sent


# ---------------------------------------------------------------------------
# Mode 2: Keyword search (twscrape)
# ---------------------------------------------------------------------------

async def _engage_keyword_async(state: State, portfolio: dict, budget: int) -> int:
    api = await _make_api()
    if not api:
        return 0

    already_replied = state.last_replied_to()
    sent = 0

    for query in _KEYWORD_QUERIES:
        if sent >= budget or state.at_daily_reply_cap():
            break

        try:
            collected = []
            async for tweet in api.search(
                f"{query} -is:retweet",
                limit=15,
                kv={"product": "Latest"},
            ):
                collected.append(tweet)

            # Sort by engagement (likes + retweets)
            collected.sort(
                key=lambda t: (getattr(t, "likeCount", 0) or 0) + (getattr(t, "retweetCount", 0) or 0),
                reverse=True,
            )

            for tweet in collected:
                if sent >= budget or state.at_daily_reply_cap():
                    break

                tweet_id = str(tweet.id)
                if tweet_id in already_replied:
                    continue

                age = _age_minutes(getattr(tweet, "date", None))
                if age > KEYWORD_FRESHNESS_MINUTES:
                    continue

                likes    = getattr(tweet, "likeCount", 0) or 0
                retweets = getattr(tweet, "retweetCount", 0) or 0
                if likes < 8 and retweets < 2:
                    continue

                author_username = tweet.user.username if tweet.user else "unknown"
                author_followers = (getattr(tweet.user, "followersCount", 0) or 0) if tweet.user else 0

                if state.times_engaged_account_recently(author_username, window=20) >= 1:
                    continue

                content = tweet.rawContent or ""
                if not _is_crypto_tweet(content):
                    log.debug("Skipping non-crypto tweet from @%s", author_username)
                    continue

                reply_text = _generate_reply(content, author_username, portfolio)
                if not reply_text:
                    continue

                sent_id = post_tweet(reply_text, reply_to_id=tweet_id)
                if sent_id:
                    state.mark_replied(tweet_id)
                    state.increment_reply_count()
                    state.mark_engaged_account(author_username)
                    sent += 1
                    log.info(
                        "Keyword reply -> @%s (%dk followers, likes:%d): %s",
                        author_username, author_followers // 1000, likes, reply_text[:70],
                    )

        except Exception as exc:
            log.warning("Keyword search error for '%s': %s", query, exc)

    if sent == 0:
        log.info(
            "Keyword engagement: 0 sent. cookie=%s, queries_run=%d",
            bool(_get_cookies()), len(_KEYWORD_QUERIES),
        )
    return sent


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(state: State) -> int:
    """
    Proactive outbound engagement.

    Uses twscrape (cookie-based, free) for reading tweets.
    Uses official X API (Tweepy) for posting replies only.
    No Basic API tier required.

    Returns total replies sent this run.
    """
    if state.at_daily_reply_cap():
        log.info(
            "Daily reply cap reached (%d/%d). No outbound engagement this run.",
            state.replies_today(), State.MAX_REPLIES_PER_DAY,
        )
        return 0

    cookies = _get_cookies()
    if not cookies:
        log.warning(
            "X_SCRAPER_COOKIES not set. Engagement reading disabled. "
            "Set this secret to enable targeted + keyword replies."
        )
        return 0

    from bot.sources.health_monitor import is_in_recovery
    recovery = is_in_recovery()
    if recovery:
        # Throttle to 1 reply per run rather than hard-block — complete silence
        # during recovery looks worse to the algorithm than low-volume genuine engagement.
        log.info("Recovery mode active: limiting to 1 outbound reply this cycle.")

    log.info(
        "Outbound engagement: %d/%d replies used today.",
        state.replies_today(), State.MAX_REPLIES_PER_DAY,
    )

    portfolio  = load_portfolio()
    run_budget = 1 if recovery else MAX_PER_RUN

    targeted  = _run_async(_engage_targeted_async(state, portfolio, run_budget)) or 0
    remaining = max(0, run_budget - targeted)
    keyword   = _run_async(_engage_keyword_async(state, portfolio, remaining)) or 0

    total = targeted + keyword
    log.info(
        "Outbound: %d targeted + %d keyword = %d total | %d/%d used today.",
        targeted, keyword, total, state.replies_today(), State.MAX_REPLIES_PER_DAY,
    )
    return total
