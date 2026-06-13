# Beacon (@Qwinahh) — Project Handover

**Date:** June 2026  
**Repo:** https://github.com/Qwinahh/beacon  
**Local path:** `C:\Users\Asus\Documents\Claude\Projects\X Bot`  
**Active branch:** `main` (code lives here) — but workflows run from `master`

---

## What This Project Is

An autonomous crypto X bot for the account **@Qwinahh**. It posts opinionated
DeFi/perps commentary 3–6x per day, engages with large CT accounts, tracks its
own post performance, and maintains an Obsidian knowledge vault as long-term
memory. The persona is a trader/farmer with real skin in the game — specific
opinions, documented positions, calibration discipline.

Runs entirely on **GitHub Actions** (free tier). No server needed.

---

## IMMEDIATE ACTION NEEDED

**The bot is currently running OLD code.** All workflows check out `master`, but
all the new code (new agents, vault expansion, etc.) is on `main`. They diverged.

Run this from the Windows terminal to go live:

```powershell
cd "C:\Users\Asus\Documents\Claude\Projects\X Bot"
git checkout master
git pull origin master
git merge main -m "merge: vault expansion + new agents"
git push origin master
git checkout main
```

If the merge throws conflicts on bot-state files (`data/state.json`,
`data/growth/*.json`, `data/vault/inspiration/`): resolve with
`git checkout --theirs <file>` for each conflict, then `git add -A`,
`git commit --no-edit`, `git push origin master`.

---

## Branch Structure

| Branch | Purpose |
|--------|---------|
| `main` | Where code is developed and merged. Workflows auto-commit bot state here. |
| `master` | What all GitHub Actions workflows actually checkout and run from. |

These diverge regularly because the bot auto-commits state files to whichever
branch it runs from. Periodic merges of `main → master` are needed to keep
the bot running new code.

---

## What Was Built (Full History)

### Foundation (earlier sessions)
- Complete codebase from scratch: orchestrator, scout, analyst, writer, scorer
- Persona system with vault-backed voice and opinions
- LLM fallback chain: Groq → Cerebras → OpenRouter → Anthropic
- Free data sources: RSS, DeFiLlama, Whale Alert, Hyperliquid funding rates,
  token unlocks, Fear & Greed index, Reddit, Discord, X scraping
- Authenticity judge (rejects AI-sounding posts before they go live)
- Shadowban detection and recovery logic
- Strategic follow/unfollow module
- Proactive engagement with target CT accounts
- Thread continuation (multi-tweet threads)

### Content expansion (most recent Cowork sessions)
- `bot/sources/portfolio_diary.py` — personal trade diary posts from `data/portfolio.json`
- `bot/sources/fear_greed.py` — market mood posts triggered by F&G swings ≥15pts
- Quote-tweet logic in `trend.py` (viral posts >500 likes, <2h old)
- Wrong-take hunting: 8 keyword queries to find and correct popular CT mistakes
- Standalone opinion posts (2×/day, no news hook needed)

### Fable session (most recent, largest)
New agents:
- `agents/performance_tracker.py` — fetches X metrics for every post >24h old,
  computes engagement/reply/bookmark rates, writes `performance-log.md`
- `agents/image_agent.py` — generates terminal-aesthetic images via Replicate
  flux-schnell for data posts and thread hooks. Disabled without API token.
- `agents/suggestion_agent.py` — weekly Mondays: synthesizes performance data,
  vault gaps, and CT trends into `data/suggestions/YYYY-WW.md` for Quin

New workflows:
- `track.yml` — daily 06:00 UTC (performance tracking)
- `suggest.yml` — Mondays 07:00 UTC (weekly suggestion report)

Reply personality upgrade:
- Replies now load the relevant project's `Stance` + `X Consensus` from the vault
- Replies inject persona `Strong Positions` — never contradicts documented stances
- Pushes back when a tweet contradicts the bot's known position on a protocol

Post logging:
- Every successful post is appended to `data/performance/post_log.json`
- Performance tracker fills in metrics 24h later

Vault expansion (from research, not training data):
- **20 project files** (was 5): Hyperliquid, EigenLayer, Drift, GMX, Pendle,
  Ethena, Morpho, Aave, Berachain, Monad, Jupiter, Kamino, LayerZero,
  Polymarket, Babylon, Ondo, Lido, Meteora, Kaito, General
- **11 narrative files** (was 3): perps-meta, airdrop-meta, restaking, rwa,
  yield-bearing-stables, btc-l2s, modular-blockchains, liquid-staking,
  prediction-markets, intents-solvers, solana-defi
- **8+ knowledge files**: crypto-history, defi-primitives, exploit-history,
  narrative-cycles, x-growth-strategy, x-algorithm-2026, post-structure-science,
  reply-strategy, image-strategy, personality-development, growth-playbook,
  voice-integrity
- Enriched `persona.md` with 17 Strong Positions (specific, defensible opinions)
- `SYSTEM.md` — master architecture reference at repo root
- `README.md` — updated

---

## Current File Structure

```
agents/
  orchestrator.py         Main posting pipeline
  scout.py                Content gathering
  analyst.py              Deterministic scoring/filter
  learner_agent.py        Ingests events into vault
  inspiration_agent.py    Daily CT inspiration feed
  growth_agent.py         Follow/engage strategy
  researcher.py           Deep dives into vault projects
  memory_agent.py         Post-success reflection
  performance_tracker.py  NEW — daily metrics tracking
  image_agent.py          NEW — image generation
  suggestion_agent.py     NEW — weekly suggestions for Quin

bot/
  brain/
    writer.py             LLM content generation + format selection
    context.py            Assembles vault context for writer
    authenticity_judge.py Rejects AI-sounding posts
    scorer.py             Deterministic quality scoring
    llm.py                LLM provider chain (Groq→Cerebras→OpenRouter→Anthropic)
  sources/
    fear_greed.py         F&G index + mood swing detection
    portfolio_diary.py    Personal trade diary posts
    xcontext.py           X/CT sentiment scraping
    hyperliquid.py        Funding rates source
    defillama.py          TVL data source
    whale_alert.py        Large transaction alerts
    unlocks.py            Token unlock schedule
    rss.py                News RSS feeds
    [+ others]
  x/
    client.py             X API wrapper (post, media upload, quote-tweet)
    trend.py              Engagement: replies, quote-tweets, wrong-take hunting
    engage.py             Thread replies, own-thread continuation
    follow.py             Strategic follow/unfollow

data/
  vault/                  Obsidian vault (bot's long-term memory)
    persona.md            Voice rules + 17 Strong Positions
    index.md              Vault index
    knowledge/            Reference files (crypto, X strategy, etc.)
    projects/             Per-protocol files (20 files)
    narratives/           Macro thesis files (11 files)
    inspiration/          Auto-written daily by inspiration_agent
    log/                  Daily activity logs
    templates/            Obsidian templates
  portfolio.json          Quin's positions (drives diary posts)
  performance/
    post_log.json         Every post + its metrics (filled by tracker)
  suggestions/            Weekly suggestion reports (Mondays)
  state.json              Bot run state (posts today, timestamps, etc.)
  memory/                 Bot learning memory
  growth/                 Follow/engage state

.github/workflows/
  post.yml                Posts 6×/day (08,11,14,17,20,22 UTC)
  engage.yml              Replies/follows every :30 past the hour
  alpha.yml               Urgent alpha check every 30min
  learn.yml               Learner agent (daily)
  inspiration.yml         Inspiration agent (daily ~07:00 UTC)
  growth.yml              Growth agent
  track.yml               Performance tracker (daily 06:00 UTC)
  suggest.yml             Suggestion agent (Mondays 07:00 UTC)

SYSTEM.md                 Master architecture reference — read this first
README.md                 Quick start guide
bot/config.py             All tunable constants
```

---

## GitHub Secrets Required

| Secret | Purpose | Required |
|--------|---------|----------|
| `X_API_KEY` | X API v2 posting | YES |
| `X_API_SECRET` | X API v2 posting | YES |
| `X_ACCESS_TOKEN` | X API v2 posting | YES |
| `X_ACCESS_SECRET` | X API v2 posting | YES |
| `X_SCRAPER_COOKIES` | twscrape for reading CT | YES |
| `GROQ_API_KEY` | Primary LLM (free, 14400/day) | YES |
| `CEREBRAS_API_KEY` | Fallback LLM | optional |
| `OPENROUTER_API_KEY` | Fallback LLM | optional |
| `ANTHROPIC_API_KEY` | Final fallback LLM | optional |
| `WHALE_ALERT_API_KEY` | Large tx alerts | optional |
| `DROPSTAB_API_KEY` | Token unlock data | optional |
| `REPLICATE_API_TOKEN` | Image generation (~$0.003/image) | optional |

---

## Key Configuration (bot/config.py)

```python
MAX_POSTS_PER_DAY = 6          # Posts per day cap
MIN_HOURS_BETWEEN_POSTS = 1.5  # Min gap between posts
POST_SCORE_THRESHOLD = 58      # Raise to 62 once account has daily engagement
IMAGE_CHANCE = 0.35            # 35% of eligible posts attempt image generation
TOPIC_MEMORY_SIZE = 30         # Recent topics tracked for variety
MAX_TOPIC_REPEAT = 2           # Max times same topic appears before skip
```

---

## How the Posting Pipeline Works

```
GitHub Actions (cron) → post.yml
  → checkout master
  → python post.py
    → orchestrator.run_post_cycle()

run_post_cycle() flow:
  Step 0a: _maybe_market_mood_post()     ← if F&G swung ≥15pts in 24h
  Step 0b: _maybe_standalone_opinion()   ← 30% random chance
  Step 0c: maybe_diary_post()            ← if portfolio.json has content
  Step 0:  Portfolio announcements
  Step 1:  Scout (gather items from all sources)
  Step 2:  Analyst (score + filter)
  Step 3:  Writer (LLM → format → authenticity judge)
  Step 4:  [optional] image_agent.maybe_generate_image()
  Step 5:  post_tweet()
  Step 6:  _post_success_hooks()
           → log to data/performance/post_log.json
           → append to vault daily log
           → memory_agent reflection
           → [if thread_hook format] post thread continuation
```

---

## What to Work On Next

### Immediate
1. **Merge main → master** (see top of this doc) so the bot runs new code
2. **Update `data/portfolio.json`** with real positions — the portfolio diary
   source reads this for authentic posts. Current file has persona-consistent
   seeds but they should reflect Quin's actual trades.
3. **Add `REPLICATE_API_TOKEN`** to GitHub Secrets if you want images

### Near-term improvements
- The `suggest.yml` workflow will start generating weekly reports every Monday
  to `data/suggestions/`. These surface what's working, narrative gaps, and
  specific actions. Check them.
- The `track.yml` performance tracker needs real post data to be useful — it
  will start producing `performance-log.md` once posts accumulate.
- `data/vault/projects/` files have Observations sections where the bot should
  be appending dated notes as it tracks protocols. Verify the learner agent is
  doing this.

### Future features (not yet built)
- "I was wrong" weekly post reviewing past predictions that didn't play out
- Expanding wrong-take keyword queries as patterns emerge
- Auto-updating vault project files with live DeFiLlama/CoinGecko data
- Bio optimisation based on what content is performing best

---

## Known Issues / Technical Context

**Branch divergence** is a recurring operational issue. The bot auto-commits
state files (`state.json`, growth state, vault logs) to whichever branch it
runs from (master). Meanwhile code development happens on main. Merging
main → master is a manual step that needs to happen whenever new features
are added. Consider eventually deleting master and making main the default so
everything is on one branch.

**LLM provider fallback chain:** Groq is primary (free, 14,400 req/day).
If Groq fails → Cerebras → OpenRouter → Anthropic. The bot will still post
even if the primary is down.

**twscrape for X reading:** The bot reads X content (for engagement, trending
topics, inspiration) via twscrape, which uses cookie-based auth stored in
`X_SCRAPER_COOKIES` secret. This occasionally needs refreshing when cookies
expire. Signs of expiry: engage.yml fails with auth errors.

**Shadowban detection:** The bot checks periodically whether its own posts
are getting impressions. If it detects suppression, it enters a recovery mode
(posts less, avoids certain content patterns). This is in `bot/sources/health_monitor.py`.

**Disk crash context:** During the Fable session, a disk crash corrupted 16
Python files mid-write. All were restored from git history. The codebase should
be clean — all `.py` files compile, all JSON parses. If anything seems broken,
check git log for the "fix: restore 13 corrupted python files" commit.

---

## Reading the Vault

The vault at `data/vault/` is an Obsidian vault — open it in Obsidian for
the best experience (graph view, wikilinks, dataview queries). The bot also
reads it programmatically via `bot/brain/context.py`.

Key files to understand the bot's "opinions":
- `data/vault/persona.md` — voice rules + 17 Strong Positions on current protocols
- `data/vault/projects/hyperliquid.md` — gold standard for project file format
- `data/vault/narratives/perps-meta.md` — gold standard for narrative file format
- `data/vault/knowledge/x-growth-strategy.md` — why the bot does what it does on X

---

## SYSTEM.md

The file `SYSTEM.md` at the repo root is the master architecture reference.
Read it before making any significant changes — it covers the full agent
reference, vault structure, configuration reference, and how to extend the bot.
