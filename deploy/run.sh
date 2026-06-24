#!/bin/bash
# deploy/run.sh — Universal job runner for Beacon X bot
#
# Usage:  bash deploy/run.sh <job>
# Jobs:   alpha | post | engage | learn | track | refresh |
#         inspiration | digest | growth | suggest
#
# Each run:
#   1. Acquires a lock (prevents two jobs corrupting state.json simultaneously)
#   2. Pulls the latest from GitHub
#   3. Runs the job's Python command(s)
#   4. Commits changed files with the right paths
#   5. Pulls again to absorb any concurrent pushes, then pushes

JOB="${1:-}"
if [ -z "$JOB" ]; then
    echo "Usage: $0 <job>"
    echo "Jobs: alpha post engage learn track refresh inspiration digest growth suggest"
    exit 1
fi

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a
source "$REPO/.env" 2>/dev/null || { echo "[beacon] ERROR: .env not found at $REPO/.env"; exit 1; }

# ---- Git identity & credentials ----
export GIT_AUTHOR_NAME="qwinahh-bot"
export GIT_AUTHOR_EMAIL="bot@qwinahh.local"
export GIT_COMMITTER_NAME="qwinahh-bot"
export GIT_COMMITTER_EMAIL="bot@qwinahh.local"
git -C "$REPO" remote set-url origin "https://x-access-token:${GH_PAT}@github.com/Qwinahh/beacon.git"

# ---- Logging ----
LOG_DIR="$REPO/deploy/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/${JOB}.log"
MAX_LOG_LINES=2000
# Trim log if it's grown large (keep last 2000 lines)
if [ -f "$LOG" ] && [ "$(wc -l < "$LOG")" -gt "$MAX_LOG_LINES" ]; then
    tail -n "$MAX_LOG_LINES" "$LOG" > "${LOG}.tmp" && mv "${LOG}.tmp" "$LOG"
fi

# ---- Global lock — one bot job at a time ----
LOCKFILE="$REPO/.beacon.lock"
exec 200>"$LOCKFILE"
if ! flock -n 200; then
    echo "[beacon:$JOB] $(date -u '+%Y-%m-%d %H:%M UTC') — skipped (another job running)" >> "$LOG"
    exit 0
fi

# ---- Run everything inside the log ----
{
echo ""
echo "=== [beacon:$JOB] $(date -u '+%Y-%m-%d %H:%M:%S UTC') ==="

cd "$REPO"

# Pull latest state before running
git pull --no-rebase -X theirs origin main 2>&1 || true

# Activate venv
source "$REPO/venv/bin/activate"

# ---- Job dispatch ----
case "$JOB" in

  alpha)
    python post.py --alpha-only
    GIT_ADD="data/state.json data/memory/ data/projects/ data/vault/ data/performance/ data/growth/"
    GIT_MSG="chore: alpha state + vault [skip ci]"
    ;;

  post)
    python post.py
    GIT_ADD="data/state.json data/memory/ data/projects/ data/vault/ data/performance/ data/growth/"
    GIT_MSG="chore: update bot state + vault [skip ci]"
    ;;

  engage)
    python engage.py
    GIT_ADD="data/state.json data/growth/"
    GIT_MSG="chore: update engage + follow state [skip ci]"
    ;;

  learn)
    python -m agents.learner_agent
    GIT_ADD="data/memory/ data/projects/ data/vault/"
    GIT_MSG="chore: update knowledge base [skip ci]"
    ;;

  track)
    python -m agents.performance_tracker
    GIT_ADD="data/performance/ data/vault/knowledge/performance-log.md"
    GIT_MSG="chore: update post performance metrics [skip ci]"
    ;;

  refresh)
    python -m agents.market_updater
    python -m agents.calibration_agent
    GIT_ADD="data/vault/"
    GIT_MSG="chore: refresh live market data + calibration log [skip ci]"
    ;;

  inspiration)
    python -c "from agents.inspiration_agent import run; run()"
    GIT_ADD="data/vault/inspiration/"
    GIT_MSG="chore: daily inspiration feed [skip ci]"
    ;;

  digest)
    python digest_run.py
    GIT_ADD="data/digests/"
    GIT_MSG="chore: daily digest [skip ci]"
    ;;

  growth)
    python -m agents.growth_agent
    GIT_ADD="data/growth/ data/vault/growth/"
    GIT_MSG="growth: weekly analysis + performance context [skip ci]"
    ;;

  suggest)
    python -m agents.suggestion_agent
    GIT_ADD="data/suggestions/"
    GIT_MSG="chore: weekly suggestions report [skip ci]"
    ;;

  retime)
    python -m agents.schedule_optimizer
    GIT_ADD="data/growth/posting_schedule.json"
    GIT_MSG="chore: auto-tune posting schedule [skip ci]"
    ;;

  *)
    echo "Unknown job: $JOB"
    exit 1
    ;;
esac

# ---- Commit + push ----
git add $GIT_ADD
if git diff --cached --quiet; then
    echo "[beacon:$JOB] No changes to commit."
else
    git commit -m "$GIT_MSG"
    echo "[beacon:$JOB] Committed."
fi

git pull --no-rebase -X ours origin main 2>&1 || true
git push origin main 2>&1
echo "[beacon:$JOB] Done."

} >> "$LOG" 2>&1
