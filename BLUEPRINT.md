# @Qwinahh Bot — Complete Blueprint

*A ground-up analysis, strategy, and build plan.*

---

## 1. Current Bot Audit

### What the existing code does
The bot runs on GitHub Actions every 20 minutes, fetches RSS feeds from CoinDesk and The Defiant, funding rounds from DeFiLlama, and TVL movers, scores each item against a 70-point threshold, picks the top candidate, renders a tweet from hardcoded template strings, and posts via Tweepy.

### Critical bugs

**State persistence is broken.** `bot_state.json` is saved via GitHub Actions cache keyed by `run_id`. Each run creates a new key; the restore uses a prefix match. GitHub evicts caches after 7 days of non-use and enforces a 10 GB limit. In practice the state resets unpredictably, meaning the deduplication fingerprints are gone and the daily count silently resets. The bot either re-posts content it already sent or believes it has already hit the daily cap when it hasn't.

**The `passes_value_bar` function blocks valid posts.** The function checks for `"i'm"` (straight apostrophe) in the lowercased tweet text, but the `opinion_reason()` strings use curly/smart apostrophes (`'`). After `.lower()` the two don't match, so `has_opinion` evaluates to False on a large share of posts and the tweet is silently dropped.

**Two tweets per day is far too infrequent.** Growing accounts post 3–6 times daily. At two posts the algorithm deprioritises the account and it almost never surfaces organically.

**Hardcoded template strings repeat.** There are 3–5 `opinion_reason()` strings per topic. With daily posts over weeks, followers see the exact same sentences. This is the core quality problem.

**Random Chinese text (7% probability).** `CHINESE_TAIL_PROB = 0.07` silently appends a Chinese sentence to roughly 1 in 14 posts. On an English crypto account this reads as a glitch. It should be removed.

**No engagement features.** The bot never replies to mentions, never comments on anyone else's posts, and never builds conversations. The X algorithm heavily weights engagement loops; an account that only broadcasts and never responds will not grow.

**RSS is limited to two feeds.** CoinDesk and The Defiant are good but not enough. Key sources like The Block, Blockworks, DL News, Kaito newsletters, and protocol-specific announcements are all missing.

**Market prices are fetched but never used.** CoinGecko data is collected in `fetch_market_snapshot()` but the result is never incorporated into any post. This is wasted work.

### What actually works in the current code

The fingerprint-based deduplication concept is solid. The DeFiLlama integrations (raises + TVL movers) give the bot access to real data that most accounts don't post. The scoring system's structure is sensible — the implementation just needs the bugs fixed and the thresholds retuned. The format variety concept (blunt, info_take, conviction, spotlight) is the right idea.

---

## 2. What Actually Works on Crypto X

### Content that performs

**Original data with a take.** Not "protocol X raised $Y" but "protocol X raised $Y and here's why the investor list matters." Accounts that attach reasoning to data outperform those that just repost news.

**Being first with an angle.** Speed matters less than angle. If you're the fifth account to post about a funding round but the first with an opinion on what it means for the sector, you win.

**Portfolio transparency.** "I entered X at $Y because Z" posts consistently outperform pure analysis. People follow accounts they can learn alongside. The bot can do this once Quin defines positions.

**Thread deep dives.** One 8–12 tweet thread per week on a specific protocol, mechanic, or trend builds authority faster than 50 one-off posts.

**Contrarian takes with receipts.** "Everyone says X but the data shows Y" is one of the highest-engagement formats in crypto. It requires having access to actual data — which this bot does via DeFiLlama.

**Airdrop and points meta.** The account's existing keyword list (`FOCUS_KEYWORDS`) is well-tuned. The audience that follows airdrop/points content is large, active, and will engage if the signal-to-noise ratio is good.

### Posting cadence

Post 4–5 times per day, distributed across active windows. For a crypto audience skewed toward UTC+0 to UTC+8:

- 07:00–09:00 UTC — Asia active, US pre-market
- 13:00–15:00 UTC — US morning, EU afternoon
- 19:00–21:00 UTC — US evening, peak global hours

Vary the exact time within each window by ±30 minutes. An account that posts at exactly 08:00 every day reads as a script.

### Engagement tactics

**Reply to your own posts within 15 minutes.** Adding a follow-up thought as a reply to your first tweet signals activity to the algorithm and keeps the post in circulation longer.

**Comment on high-traffic posts, not just tweets from big accounts.** Find posts that are actively getting replies (not just likes) and add a substantive comment. This is where discoverability comes from.

**Reply to every mention in the first 2 hours.** Even a one-sentence reply dramatically improves algorithmic amplification of the original post.

**Quote tweet sparingly, with genuine additions.** Quote tweets that just say "this" perform poorly. Quote tweets that add a data point, a counterpoint, or a specific example work.

### What to avoid

No hashtags, or at most one per post. No price predictions without reasoning. No "just dropped" or "this is huge" openers. No excessive bolding or formatting within tweets — X renders them as raw characters. No posting the same format twice in a row.

### On authenticity

X's spam detection looks for patterns: identical post timing, identical text structure, bulk follows, bulk unfollows, liking thousands of posts per day. The defences are simple: randomise timing, generate varied text (Claude handles this), limit daily actions to what a very active human would do (~100 likes, ~20 replies, ~5 follows), and never bulk follow/unfollow.

X's Developer Policy requires automated accounts to be identifiable. The account bio should include "bot" or "automated" — this is both a ToS requirement and, counterintuitively, builds trust because it signals the account is a curated data source rather than a human pretending to have opinions they generated in 10 seconds.

---

## 3. New Architecture

### Module layout

```
crypto-x-bot/
├── .github/workflows/
│   ├── post.yml           # Runs 4× daily, posts content
│   └── engage.yml         # Runs hourly, handles engagement
├── bot/
│   ├── config.py          # All constants and settings
│   ├── state.py           # Persistent state (committed to git)
│   ├── sources/
│   │   ├── rss.py         # Multi-feed RSS ingestion
│   │   ├── defillama.py   # Raises + TVL data
│   │   └── prices.py      # CoinGecko price snapshots
│   ├── brain/
│   │   ├── scorer.py      # Item scoring and selection
│   │   └── writer.py      # Claude API content generation
│   ├── x/
│   │   ├── client.py      # Authenticated Tweepy wrapper
│   │   └── engage.py      # Mentions, replies, comments
│   └── portfolio/
│       └── tracker.py     # Positions, airdrops, watchlist
├── data/
│   ├── state.json         # Bot runtime state (auto-updated by CI)
│   ├── portfolio.json     # Quin's positions (you edit this)
│   └── watchlist.json     # Projects to track (you edit this)
├── post.py                # Entry point: find + post best item
├── engage.py              # Entry point: reply + comment run
└── requirements.txt
```

### The key upgrade: Claude API for content

The single highest-leverage change is replacing hardcoded template strings with Claude API calls. Instead of rotating through 4 pre-written sentences, the writer receives a structured prompt with the news item, recent post history (to avoid repetition), and portfolio context, and generates a genuinely varied, opinionated tweet.

This means no two posts ever sound alike, the voice develops over time, and the content passes every "does this sound like a real person" test automatically.

### Multi-agent breakdown

| Agent | Role | Trigger |
|---|---|---|
| Researcher | Pull all sources, score items, select best candidate | Every post run |
| Writer | Take the selected item, generate tweet text via Claude | After researcher selects |
| Engager | Read mentions, find KOL posts to comment on | Hourly |
| Portfolio Manager | Read portfolio.json, generate position updates | Daily + on new entry |

In implementation these are separate Python entry points (`post.py`, `engage.py`) called by separate GitHub Actions workflows. They share state via `data/state.json` committed back to the repo after each run.

### State persistence fix

After every run, the workflow commits `data/state.json` back to the repo with a bot commit. This requires a `GH_PAT` (Personal Access Token) with `repo` write scope added to GitHub Secrets. This is the standard pattern for bots that need durable state without an external database.

```yaml
- name: Commit state
  run: |
    git config user.email "bot@qwinahh"
    git config user.name  "qwinahh-bot"
    git add data/state.json
    git diff --cached --quiet || git commit -m "chore: update bot state [skip ci]"
    git push
  env:
    GITHUB_TOKEN: ${{ secrets.GH_PAT }}
```

The `[skip ci]` tag prevents the commit from triggering another workflow run.

### Portfolio + airdrop tracking

`data/portfolio.json` is a file you maintain manually. The bot reads it and uses it to shape its voice and surface relevant posts.

```json
{
  "positions": [
    {
      "project": "Hyperliquid",
      "ticker": "HYPE",
      "entry_note": "early perps thesis, on-chain activity speaks for itself",
      "tracking_since": "2024-11-01",
      "status": "active"
    }
  ],
  "airdrops": [
    {
      "project": "Lighter",
      "actions": ["trading volume", "liquidity provision"],
      "status": "farming",
      "note": "perp dex on Arbitrum, early stage"
    }
  ],
  "watching": [
    {
      "project": "Meteora",
      "reason": "liquidity layer for Solana, incentives incoming"
    }
  ]
}
```

When the bot is generating a post about Hyperliquid, it knows you have a position and frames the take accordingly. When you add a new airdrop entry, the next post run can generate a thread announcing you're watching it.

**Quin's role in the loop:** When you want to tell the bot about a new investment or project, update `portfolio.json` directly and push. Or tell me in chat — I'll update the file and push, and the bot picks it up on its next run.

---

## 4. Data Sources

| Source | What it provides | API key needed |
|---|---|---|
| CoinDesk RSS | Breaking crypto news | No |
| The Defiant RSS | DeFi-focused analysis | No |
| The Block RSS | Institutional/market news | No |
| Blockworks RSS | Market + macro | No |
| DL News RSS | European/regulatory | No |
| DeFiLlama Raises | Funding rounds (real-time) | No |
| DeFiLlama TVL | Protocol TVL changes | No |
| DeFiLlama Protocols | Chain/category data | No |
| CoinGecko | BTC/ETH/SOL price + change | No (free tier) |
| Anthropic Claude | Tweet text generation | Yes (Anthropic API key) |

Everything except Claude runs on free tiers. Claude's cost on claude-haiku-4-5 for 5 posts/day is approximately $0.01/day — negligible.

---

## 5. What You Need to Do (Action Items)

**Required — do these before the rewrite can run:**

1. **Get an Anthropic API key.** Go to console.anthropic.com, create an API key, add it to GitHub Secrets as `ANTHROPIC_API_KEY`. This unlocks the writer module. Without it the bot falls back to templates.

2. **Create a GitHub Personal Access Token.** Go to GitHub → Settings → Developer Settings → Personal Access Tokens → Fine-grained. Give it read+write access to the `crypto-x-bot` repo. Add to GitHub Secrets as `GH_PAT`. This fixes the state persistence.

3. **Update `data/portfolio.json`.** Add your current positions and what you're farming. The bot will use this to shape its voice. Keep it as honest as you're comfortable with — even partial info is useful.

4. **Update your X bio.** Add "automated" or "bot" somewhere in the bio. This is required by X's Developer Policy and protects the account from suspension. It can be subtle: *"Automated crypto signal tracker | DeFi / perps / airdrops"*

**Optional but high-value:**

5. **Upgrade to X API Basic ($100/mo).** The free tier can post but can't read tweets or search. Engagement features (replying to mentions, finding KOL posts to comment on) require Basic. Without it the engage module is disabled.

6. **Define your watchlist.** Update `data/watchlist.json` with projects you care about. The researcher will weight news about these projects higher.

7. **Set up a cron schedule that fits your timezone.** The default posting windows are UTC-based. Adjust in `bot/config.py` if you want to shift them.

---

## 6. What I Need to Perform at Full Capability

As the AI running this bot, the constraints on my performance are:

**Without Anthropic API key:** Falls back to template-based writing. Posts will be functional but less varied than Claude-generated content.

**Without X API Basic:** Can post but cannot read mentions, cannot search for posts to engage with, cannot build conversation loops. The account grows much more slowly.

**Without portfolio.json populated:** The bot has no personal voice or position to argue from. It's just a news aggregator. Populated portfolio data is what transforms it from a feed reader into an account with a point of view.

**Without watchlist.json populated:** The researcher has no bias toward specific projects, so focus drifts based purely on what's in the news. A watchlist keeps the account in its lane even during quiet news cycles.

**With all of the above in place:** The bot can post 4–5 times daily with Claude-generated content anchored to your actual positions and interests, engage with mentions hourly, comment on relevant threads, and surface airdrop/farming opportunities within your specific focus areas.

---

## 7. Build Order

### Phase 1 — Foundation (current session)
- Modular code rewrite
- Fix state persistence via git commits
- Claude API integration for content
- Expanded RSS feeds
- Improved scoring (lower threshold, fix value_bar bug)
- Remove Chinese tail feature
- 4–5 posts/day on randomised schedule
- Clean GitHub Actions workflows

### Phase 2 — Voice
- Portfolio tracker live (reads portfolio.json)
- Daily portfolio update posts
- "I'm watching X because Y" posts for new watchlist entries
- Thread format for deep dives
- Quote tweet support

### Phase 3 — Engagement (requires X API Basic)
- Reply to mentions within 2 hours
- Find and comment on KOL posts in focus areas
- Smart reply to own posts (self-thread first reply)

### Phase 4 — Intelligence
- Dune Analytics integration (on-chain data)
- Whale alert signals (large transactions)
- Kaito mindshare data
- Airdrop opportunity scoring model
