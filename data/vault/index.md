# Beacon — Bot Knowledge Base

This vault is built and maintained by the Beacon bot (@Qwinahh).
It updates after every post cycle. Pull the repo and open this folder
in Obsidian to browse what the bot knows and how its views are evolving.

You can edit any file here — the bot will pick up your changes on the
next run. Useful for correcting a thesis or flagging a farm to stop.

---

## Projects

The bot tracks these projects. Each file has a thesis, trust score,
observations, and airdrop status.

- [[projects/hyperliquid|Hyperliquid]] — perps DEX, long-term constructive
- [[projects/kaito|Kaito]] — InfoFi, farming-oriented
- [[projects/meteora|Meteora]] — Solana CLMM, actively farming
- [[projects/eigenlayer|EigenLayer]] — restaking, watching

*New projects are added automatically as the bot discovers them.*

---

## Narratives

Macro-level thesis tracking across projects.

- [[narratives/perps-meta|Perps Meta]] — on-chain perps winning thesis
- [[narratives/airdrop-meta|Airdrop Meta]] — farming strategy framework
- [[narratives/restaking|Restaking / EigenLayer]] — AVS economics

---

## Daily Inspiration

What's performing well in the DeFi/crypto space today — updated ~07:00 UTC.

- [[inspiration/trending|Today's Top Posts]] — top posts by engagement with links
- [[inspiration/patterns|What's Working]] — format and topic breakdown

---

## Daily Log

The bot logs every post cycle here. What was posted, what was skipped,
what was researched.

*Latest entries are in the [[log/]] folder — sorted by date.*

---

## How to edit

- **Change a thesis:** edit the `## Thesis` section in the project file.
- **Mark a farm stopped:** change `airdrop_status: farming` to `airdrop_status: stopped` in the frontmatter.
- **Add a note:** add a bullet under `## Observations` — the bot won't overwrite existing bullets.
- **Block a project:** add `blocked: true` to the frontmatter — bot will skip it.

---

→ [[dashboard]] · [[knowledge/crypto-history]] · [[knowledge/defi-primitives]] · [[knowledge/exploit-history]] · [[knowledge/narrative-cycles]] · [[knowledge/x-growth-strategy]]
