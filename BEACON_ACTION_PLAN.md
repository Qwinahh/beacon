# Beacon — Audit & Go-Live Action Plan
*Prepared June 13, 2026. Supersedes the merge instructions in HANDOVER.md, which contain a bug that would have stopped the bot from posting.*

---

## TL;DR — read this first

**Do not run the merge from HANDOVER.md as written.** Two problems:

1. **`main`'s `bot/config.py` is truncated** (leftover disk-crash damage that was never restored). It cuts off mid-line and is missing 6 constants the new code imports. Because the missing imports are at **module level** in `bot/x/client.py` (the X posting wrapper) and `bot/x/engage.py` (replies/threads), **the bot cannot post or engage at all** with main's code as-is. `py_compile` passes because import resolution happens at runtime, not compile time — which is why this slipped through.
2. **The handover's conflict rule is backwards.** It says resolve bot-state conflicts with `git checkout --theirs`. When merging `main` into `master`, `--theirs` = `main` = the **stale/corrupt** state. The live state lives on `master` = `--ours`. Using `--theirs` would overwrite live state with corrupt copies.

A repaired, verified `config.py` is provided: **`bot_config_FIXED.py`** (in the outputs folder). Drop it in before going live.

Everything below — the merge, the commits, the push — should be run by **you** in a native terminal or **Claude Code in VS Code**. My sandbox mounts your folder over a network layer that corrupts git's lock files, so I can't safely run git here. File reads/edits and running Python *are* safe, which is how the audit was done.

---

## What I verified

- **All 63 Python files compile.** ✓
- **Only one Python file is truncated:** `bot/config.py` on `main`. All others end cleanly.
- **8 tracked JSON files are corrupt** (truncated mid-write): `data/state.json`, `data/growth/follow_state.json`, `data/growth/target_follow_accounts.json`, `data/growth/health_status.json`, `data/memory/project_observations.json`, `data/memory/signal_patterns.json`, `data/vault/.obsidian/app.json`, `data/vault/.obsidian/community-plugins.json`. **Every loader for these wraps `json.load` in `try/except` and resets to a safe default**, so they are non-fatal — the bot loses that slice of memory once and self-heals on the next save. They are also resolved automatically by the corrected merge (you keep `master`'s valid live versions).
- **`main` genuinely contains `master`'s features** (quote-tweets, portfolio diary, fear & greed, authenticity judge are all present and identical/superset). The handover's "main = new, master = old" is true at the *content* level. The exception is `config.py`, which diverged both ways and is fixed by the provided file.
- **All workflows already use the `GH_PAT` secret** (not just the new ones) and check out `master`. `GH_PAT` is required but missing from the handover's secret table — it's clearly already set since the bot runs.
- **The new agents are well-built** (`performance_tracker`, `image_agent`, `suggestion_agent`) — documented graceful degradation, correct cron, and the workflows use the correct `git pull --no-rebase -X ours` pattern.

### The 6 constants restored in `bot_config_FIXED.py`
| Constant | Value | Why it matters |
|---|---|---|
| `ENV`, `require_env` | (from master) | **Module-level** import in `bot/x/client.py` → without it the bot can't post |
| `BOT_USERNAME` | `"Qwinahh"` | **Module-level** import in `bot/x/engage.py` → without it engage/threads crash |
| `QUOTE_TWEET_COOLDOWN_HOURS` | `6.0` | Same import line in `engage.py` |
| `POST_LOG_PATH` | `data/performance/post_log.json` | `orchestrator._append_post_log` (runs after every post) + both new agents |
| `PERFORMANCE_LOG_MD_PATH` | `data/vault/knowledge/performance-log.md` | performance tracker output |
| `SUGGESTIONS_DIR` | `data/suggestions` | weekly suggestion agent output |
| `VAULT_PERSONA_PATH` | `data/vault/persona.md` | reply Strong-Positions injection (lazy import, non-fatal) |

All 30 names imported `from bot.config` across the repo now resolve against the fixed file. Verified by import, not just compile.

---

## Go-live — corrected steps

Run these in your Windows terminal or Claude Code. There is currently an **unfinished merge sitting in your working tree** (`git status` shows "All conflicts fixed but you are still merging"), so step 0 clears it.

### Step 0 — clear the stale merge
```bash
cd "C:\Users\Asus\Documents\Claude\Projects\X Bot"
git status                       # confirm what's pending
git merge --abort                # safe: local main == origin/main, nothing committed is lost
git status                       # should now be clean (apart from untracked HANDOVER.md / this file)
```

### Step 1 — fix config on `main`, commit
Copy `bot_config_FIXED.py` over `bot/config.py`, then:
```bash
git checkout main
# (copy the fixed file into place: bot/config.py)
python -c "import bot.config as c; print('config OK', c.BOT_USERNAME, c.POST_LOG_PATH)"
git add bot/config.py
git commit -m "fix: restore truncated config.py (ENV/require_env, BOT_USERNAME, tracker paths)"
git push origin main
```

### Step 2 — merge `main` → `master`, keeping live state
```bash
git checkout master
git pull origin master           # pull the bot's auto-committed live state (~20 commits)
git merge main -m "merge: vault expansion + new agents + config fix"
```
If it reports conflicts, resolve with this rule — **code takes `main`, state takes `master`** (the opposite of the old handover for state files):
```bash
# keep live bot state from master (ours):
for p in data/state.json data/growth data/memory data/performance "data/vault/.obsidian"; do
  git checkout --ours -- "$p" 2>/dev/null
done
# take new code from main (theirs) for everything else still conflicted:
git diff --name-only --diff-filter=U | xargs -r -I{} git checkout --theirs -- "{}"
git add -A
git commit --no-edit
```
*(In Claude Code you can just let it resolve conflicts with that rule in plain English.)*

### Step 3 — push and watch
```bash
git push origin master
git checkout main
```
Then watch the **Actions** tab. The next `post.yml` run should post cleanly, and `track.yml` (06:00 UTC) / `suggest.yml` (Mon 07:00 UTC) should stop failing.

---

## Permanent fix — stop the branch divergence

The root cause: the bot auto-commits state to whatever branch it runs from (`master`), while you develop on `main`. They must drift, and a manual merge is needed forever. State files **must** stay tracked — GitHub Actions runners are ephemeral, so committing state is how the bot remembers anything between runs. So the fix isn't to untrack them; it's to **run and develop on the same branch.**

**Recommended: collapse to a single branch (`main`).** Do this *after* go-live is confirmed stable.
1. Make sure `main` is fully correct (config fix applied, Step 1 done).
2. In every workflow under `.github/workflows/` (`post, engage, alpha, learn, inspiration, growth, digest, track, suggest`), change `ref: master` → `ref: main` and every inline `checkout master` / `pull … origin master` / `push origin master` → `main`.
3. On GitHub: **Settings → Branches → default branch → `main`.**
4. Confirm a full day of green runs on `main`, then delete `master` (`git push origin --delete master`).

After this, code and state live on one branch and never diverge. I can generate the edited workflow files on request.

---

## Optional cleanups (low priority)
- The 8 corrupt JSON files on `main` become irrelevant after the corrected merge (you keep `master`'s valid versions). If you ever make `main` the live branch, the bot self-heals them on first run; no action needed.
- `bot/sources/health_monitor.py` has a dead duplicate `_load_status` definition (first one's `except` references a non-existent `__wrapped__`). The second definition shadows it, so it's harmless — worth deleting for tidiness.
- The handover's required-secrets table is missing `GH_PAT` (required by all workflows) and `X_BEARER_TOKEN` (used by the tracker). Add them so the next handover is accurate.

---

## On model delegation (your "orchestrator" ask)
For this job I did the audit inline on the high-reasoning model rather than spawning sub-agents. That **was** the usage-saving choice: each sub-agent starts cold and re-derives the repo context, so fanning out a single connected investigation costs more, not less. Where delegation genuinely saves money is splitting *independent* future work:

- **Opus (me, orchestrator):** planning, the tricky judgment calls (merge strategy, which version wins), and final verification.
- **Sonnet — via Claude Code in VS Code:** the git surgery above and bulk feature-building. Claude Code has native git + push access I lack, so it's the right tool for anything touching the repo's history.
- **Haiku:** cheap mechanical passes — "compile everything", "validate all JSON", "grep for X" — when you want a quick sweep.

So the efficient division going forward: **you drive the git steps in Claude Code (Sonnet); bring results back here for me to verify.** That keeps Opus usage on the parts that need it.
