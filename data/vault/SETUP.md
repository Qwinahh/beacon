# Vault Setup Guide

Get the full experience in 10 minutes. Do these steps once.

---

## Step 1 — Open the vault in Obsidian

1. Download Obsidian from https://obsidian.md if you haven't
2. Open Obsidian → **Open folder as vault**
3. Navigate to your beacon repo and select the **`data/vault`** folder
4. Click Open — you'll see the index page load

---

## Step 2 — Install the 5 plugins

Go to **Settings → Community plugins → Turn on community plugins → Browse**

Search for and install each of these:

### 1. Git (by Vinzent03)
The most important one. Keeps your vault in sync with GitHub automatically.

After installing, go to **Settings → Git** and set:
- Auto commit-and-sync interval: **10** (minutes)
- Auto pull interval: **10** (minutes)
- ✅ Pull on startup
- Commit message: `vault: manual edit`

This means every 10 minutes Obsidian pulls the latest bot updates from GitHub.
When the bot posts and pushes new observations, they appear in your vault
within 10 minutes without you doing anything.

> **Auth setup:** In Git settings, find **Authentication/Commit Author** and
> enter your GitHub username and a Personal Access Token with `repo` scope.
> Generate one at: github.com/settings/tokens

### 2. Dataview (by blacksmithgu)
Powers the live tables in `dashboard.md`.

After installing, go to **Settings → Dataview** and enable:
- ✅ Enable JavaScript queries
- ✅ Enable inline queries

Open **`dashboard.md`** — the tables should now auto-populate from your
project files. Every time the bot updates a project file, the dashboard
reflects it automatically.

### 3. Templater (by SilentVoid)
Lets you create new project/narrative files from templates with today's
date and the filename pre-filled.

After installing, go to **Settings → Templater**:
- Template folder location: **`templates`**
- ✅ Trigger Templater on new file creation

To create a new project: right-click `projects/` folder → **New note from
template** → select `new-project`. The frontmatter fills in automatically.

### 4. Kanban (by mgmeyers)
Visualises `farms-kanban.md` as a drag-and-drop board.

After installing, open **`farms-kanban.md`** — it renders as a board.
Drag cards between columns as farms progress. The underlying markdown
updates, but note: the bot reads `airdrop_status` from individual project
files, not from this board. Use this board as your personal view, and
update the project file frontmatter separately when status changes.

### 5. Calendar (by liamcain)
Turns the `log/` folder into a calendar view.

After installing, click the calendar icon in the left sidebar. Each day
the bot ran shows as an active date. Click any date to open that day's
post log — see exactly what was posted, what was skipped, and what
was researched.

---

## Step 3 — Pin the dashboard

Right-click on **`dashboard.md`** in the file tree → **Pin** (or open it
and click the pin icon). Keep it open as your main tab. It live-updates
whenever Dataview refreshes (every few seconds).

---

## How to edit the vault

The bot reads everything it writes and respects your manual changes.

**Change a project thesis:**
Edit the `## Thesis` section in any project file. The bot uses this text
when generating posts about that project. Changes take effect next run.

**Stop the bot posting about a project:**
Add `blocked: true` to the project's frontmatter. The bot skips blocked
projects entirely when reading vault context.

**Mark a farm as stopped:**
Change `airdrop_status: farming` to `airdrop_status: stopped` in frontmatter.
The dashboard moves it out of Active Farms.

**Add your own observation:**
Add a bullet under `## Observations` above the `<!-- -->` comment.
The bot appends below the comment — your bullets stay above it.

**Change a trust score:**
Edit `trust_score: 4` in the frontmatter. Scale: 1 = noise, 5 = high conviction.
The dashboard sorts by this field.

---

## Workflow once set up

| When | What happens |
|---|---|
| Bot runs (4x/day + 30min alpha) | Posts tweet, appends to today's log, updates project file |
| GitHub push happens | Obsidian Git pulls within 10 min |
| You open Obsidian | Dashboard is current, log shows today's activity |
| You spot a new farm | Create from template in `projects/`, set `airdrop_status: watching` |
| Bot researches it | Overwrites thesis section, adds observations, sets trust score |
| Farm ends | Set `airdrop_status: done`, drag Kanban card to Done column |

---

## Folder structure reference

```
data/vault/
├── SETUP.md                      ← this file
├── dashboard.md                  ← live Dataview tables (open this daily)
├── farms-kanban.md               ← drag-and-drop airdrop board
├── index.md                      ← landing page with wikilinks
├── projects/
│   ├── hyperliquid.md            ← bot writes here after research/posts
│   ├── kaito.md
│   ├── meteora.md
│   └── eigenlayer.md
├── narratives/
│   ├── perps-meta.md
│   ├── airdrop-meta.md
│   └── restaking.md
├── knowledge/
│   ├── README.md                 ← knowledge base index
│   ├── crypto-history.md         ← major events 2017–2025
│   ├── defi-primitives.md        ← how DeFi mechanisms work
│   ├── exploit-history.md        ← hacks, vectors, patterns
│   ├── narrative-cycles.md       ← how narratives rotate
│   ├── x-growth-strategy.md      ← X algorithm and growth tactics
│   ├── events/                   ← bot writes confirmed events here daily
│   └── signals/                  ← bot writes community signals here (unconfirmed)
├── inspiration/
│   ├── trending.md               ← today's top posts, updated ~07:00 UTC daily
│   ├── patterns.md               ← format and topic analysis of what's working
│   └── history/                  ← archive of past trending.md snapshots
├── templates/
│   ├── new-project.md            ← Templater: create new project files
│   └── new-narrative.md          ← Templater: create new narrative files
└── log/
    └── YYYY-MM-DD.md             ← bot writes one per day
```
