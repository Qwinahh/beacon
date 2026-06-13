---
title: Knowledge Base Index
type: knowledge
category: index
tags: [knowledge, index]
last_updated: 2026-06-01
updated: 2026-06-07
---

# Knowledge Base Index

Seeded knowledge the bot reads for context when generating posts.
All files in this directory are `confirmed: true` — vetted historical record.

## Files

| File | Content |
|---|---|
| [[crypto-history]] | Major events 2017–2025 by year. Cycle context, key precedents. |
| [[exploit-history]] | DeFi hacks, exploit vectors, security patterns. |
| [[narrative-cycles]] | How narratives rotate, active 2025 narratives, farming meta evolution. |
| [[defi-primitives]] | AMMs, lending, perps, yield sources, stablecoins — how things work. |

## Dynamic Knowledge (Bot-Written)

The bot also learns continuously and writes to:
- `data/vault/projects/` — individual project files (trust scores, observations, thesis)
- `data/vault/log/` — daily post logs
- `data/vault/knowledge/events/` — new confirmed events as they happen
- `data/vault/knowledge/signals/` — unconfirmed community signals (never treated as fact)

## Source Tiers

| Tier | Source | Written as fact? |
|---|---|---|
| 1 | On-chain data, official announcements, SEC filings | ✅ Yes |
| 2 | Established researchers (Delphi, Messari, The Block), major media | ✅ Yes (cited) |
| 3 | CT consensus, Reddit, Discord, Telegram signals | ❌ No — sentiment only |
