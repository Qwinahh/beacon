# Beacon Dashboard

*Live view of everything the bot knows and is doing. Powered by Dataview — install the plugin and this page auto-populates.*

---

## 🌾 Active Farms

Projects the bot is currently farming. Sorted by conviction.

```dataview
TABLE
  trust_score AS "Trust",
  worth_farming AS "Worth It",
  last_updated AS "Last Updated"
FROM "projects"
WHERE airdrop_status = "farming"
SORT trust_score DESC
```

---

## 👀 Watching (Not Yet Farming)

```dataview
TABLE
  trust_score AS "Trust",
  category AS "Category",
  last_updated AS "Last Updated"
FROM "projects"
WHERE airdrop_status = "watching"
SORT trust_score DESC
```

---

## 📊 All Projects — Conviction Overview

Full project list sorted by trust score. Low scores = needs research or reconsideration.

```dataview
TABLE
  trust_score AS "Trust (1-5)",
  category AS "Category",
  airdrop_status AS "Airdrop",
  last_updated AS "Updated"
FROM "projects"
WHERE blocked != true
SORT trust_score DESC
```

---

## 🔬 Needs Research

Projects the bot hasn't updated in 7+ days — likely stale.

```dataview
TABLE
  trust_score AS "Trust",
  last_updated AS "Last Updated",
  airdrop_status AS "Status"
FROM "projects"
WHERE blocked != true
  AND (last_updated < date(today) - dur(7 days) OR trust_score = 0)
SORT last_updated ASC
```

---

## 🚫 Low Conviction — Consider Blocking

Projects with trust score ≤ 2. Worth reviewing whether the bot should still post about these.

```dataview
TABLE
  trust_score AS "Trust",
  airdrop_status AS "Airdrop",
  category AS "Category"
FROM "projects"
WHERE trust_score <= 2
  AND blocked != true
SORT trust_score ASC
```

---

## 📅 Recent Posts — Last 7 Days

*Click any date to open that day's full log.*

```dataview
LIST
FROM "log"
SORT file.name DESC
LIMIT 7
```

---

## ✅ Completed / Distributed Airdrops

```dataview
TABLE
  trust_score AS "Trust",
  last_updated AS "Updated"
FROM "projects"
WHERE airdrop_status = "distributed" OR airdrop_status = "done" OR airdrop_status = "stopped"
SORT last_updated DESC
```

---

## 📈 Narrative Tracking

```dataview
TABLE
  conviction AS "Conviction",
  last_updated AS "Updated"
FROM "narratives"
SORT conviction DESC
```

---

## 🧠 Knowledge Base

Confirmed facts the bot has learned. Click any file to read it.

```dataview
TABLE
  category AS "Category",
  last_updated AS "Updated",
  source_tier AS "Source Tier"
FROM "knowledge"
WHERE confirmed = true
  AND type = "knowledge"
SORT last_updated DESC
```

---

## ⚡ Recent Confirmed Events

New confirmed events ingested by the learner agent (Tier 1/2 sources only).

```dataview
TABLE
  date AS "Date",
  source_tier AS "Tier",
  related_project AS "Project"
FROM "knowledge/events"
WHERE confirmed = true
SORT date DESC
LIMIT 20
```

---

## 🔔 Community Signals (Unconfirmed)

Community sentiment signals — Reddit, X/CT, Discord, Telegram.
**Not facts.** Use as context only. Never trade based on these alone.

```dataview
LIST
FROM "knowledge/signals"
SORT file.name DESC
LIMIT 7
```

---

*Dashboard updates automatically when Obsidian Git pulls the latest bot run from GitHub.*
*Learner agent runs 2x per day — knowledge/events/ updates 6am and 5pm UTC.*
*To refresh manually: Cmd/Ctrl+R in Obsidian.*
