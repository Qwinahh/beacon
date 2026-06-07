---
title: Community Signals
type: knowledge
category: signals
tags: [knowledge, signals, community]
updated: 2026-06-07
---

# Community Signals

Unconfirmed community sentiment signals — X/CT, Reddit, Discord, Telegram.

**Not facts.** Use as context only. Never as the basis for a factual post.

The learner agent writes signal files here automatically when it ingests community data.
Files are named `YYYY-MM-DD-source-topic.md`.

## Source Tiers

| Tier | Source | Treatment |
|---|---|---|
| CT consensus | Multiple CT accounts making the same claim | Sentiment only |
| Reddit | DeFi/crypto subreddit discussion | Sentiment only |
| Discord / Telegram | Protocol community channels | Sentiment only |
| Anonymous tip | Single unverified source | Discard |

All files here carry `confirmed: false` in frontmatter.
The Dataview query on [[../../dashboard]] surfaces these under "Community Signals."

---

→ [[../README]] · [[../../dashboard]]
