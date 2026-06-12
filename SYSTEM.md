# SYSTEM.md — Beacon (@Qwinahh) Master Reference

## Overview

Beacon is an autonomous crypto X (Twitter) account: @Qwinahh. It posts
opinionated DeFi/perps commentary 3-6x/day, drafts replies to large CT
accounts (human-approved before sending), tracks how every post performs,
and maintains an Obsidian knowledge vault that doubles as its memory.
The persona: a trader/farmer with real positions, documented stances,
and a calibration discipline — verifiably right in public, wrong out loud.

## Architecture

```
                       GitHub Actions (cron)
   post.yml  engage.yml  alpha.yml  learn.yml  track.yml  suggest.yml
      |          |           |          |           |          |
      v          v           v          v           v          v
 +---------+ +--------+ +--------+ +---------+ +-----------+ +-----------+
 | orchest-| | trend/ | | orch.  | | learner | | perform.  | | suggest.  |
 | rator   | | engage | | alpha- | | agent   | | tracker   | | agent     |
 +----+----+ +---+----+ | only   | +----+----+ +-----+-----+ +-----+-----+
      |          |      +--------+      |            |             |
      v          |                      v            v             v
 sources -> scout -> analyst -> writer  vault     post_log     suggestions
 (rss, defillama,    (score,   (LLM +  knowledge/ + perform.   data/sugges-
 whale, unlocks,     filter)   judge)  events     -log.md      tions/WW.md
 fear&greed, x)                  |
                                 v
                       image_agent (optional)
                                 |
                                 v
                        post_tweet (+media)
                                 |
                                 v
                    _post_success_hooks:
                    post_log.json + vault log + memory
```

Data flows: sources → scout (gather) → analyst (deterministic score/filter)
→ writer (single LLM call + authenticity judge) → optional image →
post_tweet → success hooks (post_log.json, vault daily log, memory).
The performance tracker reads post_log.json 24h later and writes metrics
back; the suggestion agent synthesizes everything weekly for Quin.

## Agents Reference

- **orchestrator** (`agents/orchestrator.py`) — the posting pipeline. Pure
  Python orchestration; one LLM call (writer). Handles mood posts, opinion
  posts, portfolio diary, announcements, news-driven posts, threads, image
  attachment, and post logging. Runs on every post.yml/alpha.yml trigger.
- **scout / analyst** (`agents/scout.py`, `agents/analyst.py`) — legacy
  ToolAgent wrappers around gathering/scoring; the orchestrator now embeds
  deterministic versions of both.
- **learner_agent** (`agents/learner_agent.py`) — ingests confirmed events
  (Tier 1/2 sources) into `data/vault/knowledge/events/`. Runs via learn.yml.
- **inspiration_agent** (`agents/inspiration_agent.py`) — daily ~07:00 UTC;
  writes `data/vault/inspiration/` (top CT posts, format patterns).
- **growth_agent** (`agents/growth_agent.py`) — follow/engage strategy state
  in `data/growth/`.
- **researcher** (`agents/researcher.py`) — on-demand deep dives into vault
  project files.
- **memory_agent** (`agents/memory_agent.py`) — post-success reflection into
  `data/memory/`.
- **performance_tracker** (`agents/performance_tracker.py`) — daily 06:00 UTC
  (track.yml). Reads `data/performance/post_log.json`, fetches X metrics for
  posts >24h old (public + non-public via OAuth 1.0a), computes engagement/
  reply/bookmark rates, writes `data/vault/knowledge/performance-log.md`.
- **image_agent** (`agents/image_agent.py`) — inline during posting. Decides
  if a format warrants an image (data_observation/thread_hook yes; takes no),
  generates a terminal-aesthetic PNG via Replicate flux-schnell, returns
  bytes. Disabled without REPLICATE_API_TOKEN; never blocks a post.
- **suggestion_agent** (`agents/suggestion_agent.py`) — Mondays 07:00 UTC
  (suggest.yml). Deterministic weekly report to `data/suggestions/YYYY-WW.md`:
  what worked, what needs attention, narrative gaps, content ideas, actions
  for Quin.

## Vault Reference

`data/vault/` is an Obsidian vault and the bot's long-term memory. The bot
reads persona + knowledge + project stances when writing; it appends
observations and daily logs as it works. Key areas:

- `persona.md` — voice rules + 17 Strong Positions. The writer loads this;
  replies inject its Strong Positions section.
- `knowledge/` — reference knowledge (crypto history, DeFi primitives,
  exploit history) and X intelligence (x-algorithm-2026, post-structure-
  science, reply-strategy, image-strategy, voice-integrity, personality-
  development, growth-playbook). `performance-log.md` is auto-generated.
- `projects/` — one file per protocol: frontmatter flags, Thesis, Stance,
  Risks, Observations (bot-appended), X Consensus. Reply generation loads
  Stance + X Consensus when a tweet mentions the protocol.
- `narratives/` — macro theses with conviction levels that weight topic
  selection.
- `inspiration/`, `log/` — auto-written daily.

Add a new project: copy `templates/project.md` (or let the bot stub it via
`bot/brain/vault.py: add_observation`), fill Thesis/Stance/Risks/X Consensus,
add it to `index.md`. Update persona: edit `persona.md` directly — changes
take effect next run; keep Strong Positions consistent with project files.

## GitHub Actions Reference

All workflows check out and push the `master` branch (the repo default)
with `secrets.GH_PAT`.

| Workflow | Schedule (UTC) | Runs | Key env |
|---|---|---|---|
| post.yml | 8,11,14,17,20,22 daily | `python post.py` (orchestrator) | X keys, LLM keys, REPLICATE_API_TOKEN (opt) |
| engage.yml | (see file) | reply/quote engagement | X keys, X_SCRAPER_COOKIES, LLM keys |
| alpha.yml | (see file) | alpha-only fast lane | same as post |
| learn.yml | (see file) | learner agent | LLM keys |
| track.yml | 06:00 daily | performance_tracker | X keys (+X_BEARER_TOKEN opt) |
| suggest.yml | 07:00 Mondays | suggestion_agent | none required |

## Configuration Reference (bot/config.py)

- `MAX_POSTS_PER_DAY` / `MIN_HOURS_BETWEEN_POSTS` / `POSTING_WINDOWS` /
  `POST_JITTER_SECONDS` — cadence control.
- `POST_SCORE_THRESHOLD`, `TOPIC_MEMORY_SIZE`, `MAX_TOPIC_REPEAT`,
  `FINGERPRINT_MEMORY_SIZE` — quality gate and variety enforcement.
- `FOCUS_KEYWORDS` / `JUNK_PHRASES` — scoring boosts/penalties.
- `RSS_FEEDS`, `DEFILLAMA_*`, `COINGECKO_*`, `RSS_*`, `RAISES_FETCH_LIMIT`,
  `TVL_MIN_CHANGE_PCT` — data source config.
- `CLAUDE_MODEL`, `CLAUDE_MAX_TOKENS`, `TEMPLATE_FALLBACK` — writer LLM.
- `REPLICATE_API_TOKEN`, `IMAGE_GENERATION_ENABLED`, `IMAGE_CHANCE` — image
  agent (auto-disabled when token missing).
- Paths: `STATE_PATH`, `PORTFOLIO_PATH`, `WATCHLIST_PATH`, `PERSONA_PATH`,
  `POST_LOG_PATH`, `PERFORMANCE_LOG_MD_PATH`, `SUGGESTIONS_DIR`,
  `VAULT_PERSONA_PATH`.
- `ENV` / `require_env` — env var names for secrets; never hardcode.

## Adding New Features

1. Read this file + `agents/orchestrator.py` to find the right seam.
2. New data source → `bot/sources/<name>.py`, expose a fetch function,
   add to `_gather_candidates` in a try/except (degrade gracefully).
3. New agent → `agents/<name>.py` with a module docstring (what/when/
   reads/writes/design decisions), `log = logging.getLogger(__name__)`,
   a `main()` entry, plus a workflow yml modeled on track.yml.
4. New config → constants in `bot/config.py`, never magic numbers inline.
5. Rules: INFO for actions, DEBUG for skips; enhancements must never block
   the core post flow; missing API keys must disable the feature, not
   crash it; run `python -m py_compile` on everything you touch.

## Data Files Reference

| Path | Written by | Read by |
|---|---|---|
| data/state.json | orchestrator/state | everything (cadence, dedupe, formats) |
| data/portfolio.json | Quin (manual) | analyst (relevance), diary, replies |
| data/performance/post_log.json | orchestrator (hooks) | performance_tracker, suggestion_agent |
| data/vault/knowledge/performance-log.md | performance_tracker | writer context, Quin |
| data/suggestions/YYYY-WW.md | suggestion_agent | Quin |
| data/growth/* | growth agent, x_metrics, trend | trend (targets), growth agent |
| data/memory/* | memory_agent | writer context |
| data/digests/* | digest_run.py | learner |
| data/research/*.md | research sessions (dated, sourced) | vault authors |
| data/vault/** | bot + Quin | writer, judge, reply generation |
