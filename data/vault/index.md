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
- Mark a narrative dead → se