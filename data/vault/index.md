# Beacon Vault — Map

This vault is built and maintained by the Beacon bot (@Qwinahh).
It updates after every post cycle. Pull the repo and open this folder in Obsidian to browse what the bot knows and how its views are evolving.

You can edit any file — the bot picks up your changes on the next run. Changes to thesis blocks, stance, or frontmatter flags (`blocked: true`, `airdrop_status`) take effect immediately.

---

## Navigation

| File | Purpose |
|---|---|
| [[dashboard]] | Live Dataview overview — active farms, conviction scores, recent posts |
| [[persona]] | Voice, tone, and style rules governing all posts |
| [[farms-kanban]] | Kanban board — Watching / Farming / Claiming / Done |

---

## Projects

Individual project files with thesis, trust score, observations, and airdrop status.
Dataview on [[dashboard]] queries these automatically.

| Project | Chain | Status | Trust |
|---|---|---|---|
| [[projects/hyperliquid\|Hyperliquid]] | Hyperliquid L1 | distributed | 4/5 |
| [[projects/kaito\|Kaito]] | Ethereum | watching | 3/5 |
| [[projects/meteora\|Meteora]] | Solana | farming | 4/5 |
| [[projects/eigenlayer\|EigenLayer]] | Ethereum | watching | 3/5 |
| [[projects/general\|General]] | various | — | overflow |

*New projects are added automatically as the bot discovers them.*

**How to use:**
- Change a thesis → edit `## Thesis` in the project file
- Stop a farm → set `airdrop_status: stopped` in frontmatter
- Block a project → add `blocked: true` in frontmatter
- Add a note → add a bullet under `## Observations` (bot won't overwrite existing bullets)

---

## Narratives

Macro-level thesis tracking. `conviction` values drive post weighting in the orchestrator.

- [[narratives/perps-meta\|Perps Meta]] — on-chain perps winning thesis · `conviction: high`
- [[narratives/airdrop-meta\|Airdrop Meta]] — farming strategy framework · `conviction: high`
- [[narratives/restaking\|Restaking / EigenLayer]] — AVS economics, watching fee vs TVL divergence · `conviction: medium`

**How to use:**
- Mark a narrative dead → set `conviction: dead` in frontmatter
- Add a signal pattern → add a bullet under `## Signal Patterns`

---

## Knowledge

Seeded reference knowledge. All files confirmed Tier 1/2 sourced.
The bot reads these for context when generating posts.

### Core References

- [[knowledge/narrative-cycles\|Narrative Cycles]] — lifecycle model (Discovery → Resolution), historical precedents, peaking/early signals
- [[knowledge/crypto-history\|Crypto History]] — major events 2017–2025, cross-cycle patterns, key precedents
- [[knowledge/defi-primitives\|DeFi Primitives]] — AMMs, lending, perps, yield sources, stablecoins — how things work
- [[knowledge/exploit-history\|Exploit History]] — DeFi hacks by vector: bridges, flash loans, smart contracts, oracle manipulation
- [[knowledge/x-growth-strategy\|X Growth Strategy]] — algorithm mechanics, post architecture, engagement signals, what builds trust

### Dynamic Knowledge (Bot-Written)

- `knowledge/events/` — confirmed events ingested by the learner agent (Tier 1/2 sources only)
- `knowledge/signals/` — unconfirmed community signals (sentiment only, never treated as fact)

### Source Tiers

| Tier | Source | Written as fact? |
|---|---|---|
| 1 | On-chain data, official announcements, SEC filings | Yes |
| 2 | Established researchers (Delphi, Messari, The Block) | Yes (cited) |
| 3 | CT consensus, Reddit, Discord, Telegram | No — sentiment only |
| 4 | Anonymous tips, single-source rumors | No — discarded |

---

## Daily Log

Post-by-post record of every cycle — what was posted, what was skipped, what was researched.

Browse the `log/` folder sorted by date. Most recent: check [[log/]] in the file browser.

---

## Daily Inspiration

Updated ~07:00 UTC by the inspiration agent. Raw material for content strategy.

- [[inspiration/trending\|Today's Top Posts]] — top posts by engagement from monitored accounts, with links
- [[inspiration/patterns\|What's Working]] — format breakdown, trending topics, editorial brief

---

→ [[dashboard]] · [[persona]] · [[farms-kanban]]
