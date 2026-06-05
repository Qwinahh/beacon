# Claude Code Task — Three Changes to X Bot

This is a crypto X bot (repo at `X Bot/`). It posts, replies, and follows automatically via GitHub Actions. Three things need fixing. Implement all three. Do not ask questions — all context is here.

---

## TASK 1 — Performance feedback loop (self-adapting bot)

**Problem:** The bot posts and never checks whether it worked. It has no idea if the "contrarian" format gets 3x the engagement of "data_observation", so it just picks randomly. It needs to learn from its own performance.

**What exists already:**
- `bot/sources/x_metrics.py` — records tweet IDs after posting, has `record_posted_tweet()`. Writes to `data/growth/pending.json` and `data/growth/metrics.json`.
- `agents/growth_agent.py` — weekly analysis, but only works when real X API metrics are available (Basic tier). Currently outputs nothing useful since the account is on Free tier.
- `data/vault/log/YYYY-MM-DD.md` — daily post logs (format, topic, tweet text) written by the bot.
- `data/growth/growth_context.json` — read by the orchestrator to bias topic selection. Currently either empty or not used by the writer.

**What to build:**

### A. Twscrape engagement collector (`bot/sources/engagement_collector.py`)
New file. Uses twscrape (cookie-based, free) to pull engagement on our own recent tweets. Called from the existing `engage.py` run every 30 min.

```python
"""
Collect engagement metrics on our own recent posts via twscrape.
Runs on Free tier — no X API required, just X_SCRAPER_COOKIES.

Writes to data/growth/metrics.json so growth_agent.py can analyse what's working.
Metrics collected per tweet: likes, replies, retweets, bookmarks (if available),
quote_tweets. Also records format and topic from pending.json so we know WHAT
kind of post earned WHAT engagement.
"""
```

Logic:
1. Load `data/growth/pending.json` — list of `{tweet_id, text, format, topic, posted_at}` dicts
2. For each pending tweet older than 2 hours (give it time to accumulate engagement):
   a. Use `api.tweet_details(tweet_id)` from twscrape to get current metrics
   b. Write `{tweet_id, text, format, topic, posted_at, collected_at, likes, replies, retweets, quote_tweets}` to `data/growth/metrics.json`
   c. Remove from pending.json once collected
3. Keep last 200 entries in metrics.json, remove oldest
4. Fail silently if twscrape unavailable or cookies missing

### B. Format performance weights (`bot/brain/format_weights.py`)
New file. Reads metrics.json and computes a weight dict for the writer's format picker.

```python
"""
Compute format performance weights from collected engagement data.
Returns a dict: {format_name: weight_float} where weight > 1.0 means
this format outperforms average, < 1.0 means it underperforms.

Weights are used by _pick_format() in writer.py to bias toward what works.
Falls back to equal weights if insufficient data (< 10 posts per format).
"""
```

Logic:
- Load metrics.json
- Group by format_name
- Score each format: `(replies * 3 + likes + retweets * 2) / post_count`
  (replies weighted highest — X algorithm cares most about replies)
- Normalise so average = 1.0
- Return dict. If a format has < 3 data points, give it weight 1.0 (neutral, not penalised)
- Cache result for 1 hour (don't re-read the file on every writer call)

### C. Update `_pick_format()` in `bot/brain/writer.py`
Currently picks randomly from non-recently-used formats. Update it to use weights:

```python
def _pick_format(recent_formats: list[str]) -> tuple[str, str]:
    """Pick a format, weighted by past performance. Avoids last 2 used."""
    from bot.brain.format_weights import get_weights
    recent = set((recent_formats or [])[-2:])
    options = [(n, i) for n, i in _FORMAT_PALETTE if n not in recent]
    if not options:
        options = _FORMAT_PALETTE
    
    weights = get_weights()
    w = [weights.get(n, 1.0) for n, _ in options]
    return _random.choices(options, weights=w, k=1)[0]
```

### D. Wire engagement collector into `engage.py` (root)
Add a call to the collector at the start of `main()` before any other engagement steps:

```python
from bot.sources.engagement_collector import collect_pending
collect_pending()   # Non-fatal — fails silently
```

This means: every time the engage workflow runs (every 30 min), it also picks up engagement on posts that are now 2h+ old. No extra workflow needed.

---

## TASK 2 — Fix 0/0/0/0 outreach (nothing is happening)

**Problem:** Every engage run returns 0 mentions replied, 0 outbound replies, 0 thread replies, 0 follows. The bot is running but not doing anything.

**Root causes to fix:**

### A. `X_SCRAPER_COOKIES` is the gatekeeper — add clear diagnostics
In `engage.py` (root), at the top of `main()` before anything else, add:

```python
import os
cookies = os.environ.get("X_SCRAPER_COOKIES", "").strip()
if not cookies:
    log.warning(
        "X_SCRAPER_COOKIES is not set. Mentions, outbound replies, thread replies, "
        "and follow candidate discovery are ALL disabled. "
        "Set this secret in GitHub → Settings → Secrets → Actions. "
        "Get it from browser DevTools → Application → Cookies → x.com: "
        "copy ct0 and auth_token values as: ct0=VALUE; auth_token=VALUE"
    )
else:
    log.info("X_SCRAPER_COOKIES: set (%d chars)", len(cookies))
```

### B. Lower engagement thresholds in `bot/x/trend.py`
The current keyword queries require min_faves:40 and min_faves:50. For niche DeFi topics these are too high — there may be zero qualifying tweets. Lower them significantly:

Replace the `_KEYWORD_QUERIES` list with:
```python
_KEYWORD_QUERIES = [
    "hyperliquid perp funding lang:en min_faves:8",
    "defi airdrop points farm lang:en min_faves:5",
    "kaito yap leaderboard lang:en min_faves:5",
    "defillama tvl protocol lang:en min_faves:8",
    "perp dex funding rate lang:en min_faves:10",
    "solana defi yield farm lang:en min_faves:8",
    "crypto airdrop criteria snapshot lang:en min_faves:5",
]
```

Also lower `MIN_FOLLOWERS_FOR_TARGETED` from `10_000` to `5_000`. Many good DeFi voices have 5k-10k followers.

Also lower the engagement floor in `_engage_targeted_async`:
```python
# Change: if likes < 3 and replies < 1:
# To:
if likes < 1 and replies < 1:
```

### C. Lower engagement floor in keyword mode in `bot/x/trend.py`
In `_engage_keyword_async`, change:
```python
# Change: if likes < 40 and retweets < 8:
# To:
if likes < 8 and retweets < 2:
```

### D. Add diagnostics when nothing is found
At the end of `_engage_targeted_async` and `_engage_keyword_async`, add a log line when `sent == 0`:
```python
if sent == 0:
    log.info("Targeted engagement: 0 sent. Reasons: cookie=%s, candidates checked=%d", 
             bool(cookies), len(target_accounts))
```

### E. Increase MAX_PER_RUN in `bot/x/trend.py`
Change from `MAX_PER_RUN = 2` to `MAX_PER_RUN = 3`. With thresholds lowered, more candidates will qualify — allow sending a few more per run.

---

## TASK 3 — Strategic follow list (accounts that benefit the bot)

**Goal:** Follow accounts that post alpha the bot can learn from AND whose followers are the target audience. Two categories:
1. **Alpha sources** — accounts the bot should monitor and whose followers would follow back
2. **Peer accounts** — similar-sized crypto accounts who might notice and follow back

**A. Create `data/growth/target_follow_accounts.json`**

This is a curated list the follow cycle prioritises BEFORE random discovery. Format:

```json
{
  "priority_follows": [
    {"username": "DefiIgnas",      "reason": "defi alpha, airdrop analysis, 80k followers"},
    {"username": "0xSisyphus",     "reason": "perps and market structure, quality posts"},
    {"username": "Founderization", "reason": "airdrop meta, points economy analysis"},
    {"username": "zkDrops",        "reason": "airdrop tracking, points farming"},
    {"username": "Pentosh1",       "reason": "market structure, perps, options"},
    {"username": "0xMaki",         "reason": "DeFi protocols, TVL analysis"},
    {"username": "HsakaTrades",    "reason": "perps, macro, high engagement threads"},
    {"username": "CroissantEth",   "reason": "DeFi protocols, yield farming"},
    {"username": "0xHamz",         "reason": "DeFi alpha, airdrop hunting"},
    {"username": "SmolRefund",     "reason": "airdrop farming, points meta"},
    {"username": "deFIYIelded",    "reason": "yield farming, defi protocol analysis"},
    {"username": "Route2FI",       "reason": "DeFi education, strategy posts"},
    {"username": "0xCygaar",       "reason": "Ethereum dev, protocol mechanics"},
    {"username": "tayvano_",       "reason": "security, wallet safety, exploit analysis"},
    {"username": "functi0nZer0",   "reason": "MEV, on-chain analysis"},
    {"username": "EigenLayerNews", "reason": "restaking narrative, AVS updates"},
    {"username": "MilkyWayDeFi",   "reason": "liquid staking, points programs"},
    {"username": "Gainzy222",      "reason": "airdrop farming, points meta"},
    {"username": "thedefiedge",    "reason": "DeFi education, protocol breakdowns"},
    {"username": "DeFiMoon_",      "reason": "defi opportunities, yield strategies"}
  ],
  "already_followed": [],
  "skip": []
}
```

**B. Update `bot/x/follow.py` to use priority list first**

Add a new function `_priority_follow_pass(follow_state, client)` that runs BEFORE the twscrape candidate discovery:

```python
def _priority_follow_pass(follow_state: dict, client) -> int:
    """
    Follow accounts from the curated priority list first.
    These are manually vetted as high-value — no quality check needed.
    Returns number of accounts followed.
    """
    path = Path("data/growth/target_follow_accounts.json")
    if not path.exists():
        return 0
    try:
        config = json.loads(path.read_text())
    except Exception:
        return 0

    priority = config.get("priority_follows", [])
    already_followed_ids = _followed_ids(follow_state)
    already_attempted = set(follow_state.get("attempted", []))

    # Get usernames already in our followed/attempted lists
    followed_usernames = {
        e.get("username", "").lower()
        for e in follow_state.get("followed", [])
        if isinstance(e, dict)
    }
    skip = {u.lower() for u in config.get("skip", [])}
    done = {u.lower() for u in config.get("already_followed", [])}

    followed = 0
    for entry in priority:
        username = entry.get("username", "").lower()
        if followed >= MAX_FOLLOWS_PER_RUN:
            break
        if _follows_today(follow_state) >= MAX_FOLLOWS_PER_DAY:
            break
        if username in followed_usernames or username in skip or username in done:
            continue

        # Need to resolve username → uid via twscrape to call follow_user(uid)
        # Store username in "already_followed" in the config once done
        # For now: use the twscrape _make_api() pattern to resolve uid
        # This runs async — call via _run_async
        uid = _run_async(_resolve_uid_async(username))
        if not uid:
            log.debug("Could not resolve uid for @%s", username)
            continue

        try:
            client.follow_user(uid)
            follow_state.setdefault("followed", []).append({
                "id": uid, "username": username,
                "followed_at": int(time.time()),
            })
            _increment_daily(follow_state)
            # Mark as done in config file so we don't retry next run
            config.setdefault("already_followed", []).append(username)
            path.write_text(json.dumps(config, indent=2))
            followed += 1
            log.info("Priority follow: @%s (%s)", username, entry.get("reason", ""))
            time.sleep(2)
        except Exception as exc:
            log.debug("Priority follow failed for @%s: %s", username, exc)

    return followed
```

Add `_resolve_uid_async(username)`:
```python
async def _resolve_uid_async(username: str) -> Optional[str]:
    """Resolve a username to a user ID via twscrape."""
    api = await _make_api()
    if not api:
        return None
    try:
        user = await api.user_by_login(username)
        return str(user.id) if user else None
    except Exception:
        return None
```

Wire it into `run_follow_cycle()` right after the unfollow pass and before the twscrape discovery:
```python
# Priority follows (curated list) — no quality gate needed
client = get_client()
priority_followed = _priority_follow_pass(follow_state, client)
if priority_followed:
    log.info("Priority follows: %d", priority_followed)
    _save_follow_state(follow_state)
```

**C. Update `_DEFAULT_TARGET_ACCOUNTS` in `bot/x/trend.py`**
Replace the current target accounts list with a better one focused on the actual DeFi/perps/airdrop community:

```python
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
```

---

## Implementation notes

- All changes must fail silently — the bot runs in GitHub Actions and a crash stops everything
- Use `try/except Exception as exc: log.warning(...)` around any new network calls
- twscrape account names: use unique names (`beacon_collector_scraper`, `beacon_uid_resolver`) to avoid conflicts with existing scraper instances
- The priority follow list in target_follow_accounts.json is append-only for `already_followed` — never remove entries from it
- Test nothing — just implement cleanly. The bot tests itself in production.

## Files to create/modify summary

**Create:**
- `bot/sources/engagement_collector.py`
- `bot/brain/format_weights.py`
- `data/growth/target_follow_accounts.json`

**Modify:**
- `bot/brain/writer.py` — update `_pick_format()` to use weights
- `bot/x/trend.py` — lower thresholds, update target accounts, increase MAX_PER_RUN
- `bot/x/follow.py` — add `_priority_follow_pass()`, `_resolve_uid_async()`, wire in
- `engage.py` (root) — add cookie diagnostics, call `collect_pending()`
