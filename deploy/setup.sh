#!/bin/bash
# deploy/setup.sh — One-time setup for Beacon X bot on Hetzner (or any Linux VPS)
# Run as: bash deploy/setup.sh
#
# What this does:
#   1. Checks/installs Python 3.12
#   2. Creates a virtualenv and installs requirements
#   3. Prompts you to fill in .env with your secrets
#   4. Configures git to push back to GitHub
#   5. Installs the crontab

set -e
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

echo "=== Beacon X Bot — Hetzner Setup ==="
echo "Repo: $REPO"
echo ""

# ---------------------------------------------------------------------------
# 1. Python 3.12
# ---------------------------------------------------------------------------
if ! command -v python3.12 &>/dev/null; then
    echo "[setup] Python 3.12 not found — installing..."
    apt-get update -qq
    apt-get install -y software-properties-common
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update -qq
    apt-get install -y python3.12 python3.12-venv python3.12-dev
else
    echo "[setup] Python 3.12 found: $(python3.12 --version)"
fi

# ---------------------------------------------------------------------------
# 2. Virtual environment + dependencies
# ---------------------------------------------------------------------------
if [ ! -d "$REPO/venv" ]; then
    echo "[setup] Creating venv..."
    python3.12 -m venv "$REPO/venv"
fi

echo "[setup] Installing requirements..."
"$REPO/venv/bin/pip" install --quiet --upgrade pip
"$REPO/venv/bin/pip" install --quiet -r "$REPO/requirements.txt"
echo "[setup] Requirements installed."

# ---------------------------------------------------------------------------
# 3. .env file
# ---------------------------------------------------------------------------
if [ ! -f "$REPO/.env" ]; then
    echo ""
    echo "[setup] Copying .env.example → .env — FILL THIS IN before the bot starts."
    cp "$REPO/deploy/.env.example" "$REPO/.env"
    echo ""
    echo "  >>> Edit $REPO/.env with your secrets, then re-run this script or"
    echo "      just install the crontab manually: crontab deploy/crontab.txt"
    echo ""
else
    echo "[setup] .env already exists — skipping (edit it manually if keys changed)."
fi

# ---------------------------------------------------------------------------
# 4. Git credentials — embed GH_PAT in the remote URL so pushes work
# ---------------------------------------------------------------------------
source "$REPO/.env" 2>/dev/null || true

if [ -n "$GH_PAT" ]; then
    git remote set-url origin "https://${GH_PAT}@github.com/Qwinahh/beacon.git"
    git config user.name  "qwinahh-bot"
    git config user.email "bot@qwinahh.local"
    echo "[setup] Git remote configured with GH_PAT."
else
    echo "[setup] WARNING: GH_PAT not set in .env — git push will fail. Fill .env first."
fi

# ---------------------------------------------------------------------------
# 5. Make scripts executable
# ---------------------------------------------------------------------------
chmod +x "$REPO/deploy/run.sh"

# ---------------------------------------------------------------------------
# 6. Install crontab
# ---------------------------------------------------------------------------
echo ""
read -p "[setup] Install crontab now? (y/N): " yn
if [[ "$yn" =~ ^[Yy]$ ]]; then
    # Merge with existing crontab (preserve any meridian-bot entries)
    (crontab -l 2>/dev/null; echo ""; cat "$REPO/deploy/crontab.txt") | crontab -
    echo "[setup] Crontab installed. Run 'crontab -l' to verify."
else
    echo "[setup] Skipped. To install manually:"
    echo "  crontab -e   # then paste contents of deploy/crontab.txt"
fi

echo ""
echo "=== Setup complete ==="
echo "Test a single run: bash deploy/run.sh engage"
echo "Logs:              tail -f deploy/logs/<job>.log"
