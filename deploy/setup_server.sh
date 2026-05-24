#!/usr/bin/env bash
# =============================================================
# Hetzner server setup — run once as root or sudo
#
# Usage:
#   chmod +x deploy/setup_server.sh
#   sudo ./deploy/setup_server.sh /opt/xbot your-github-user/your-repo
# =============================================================
set -euo pipefail

INSTALL_DIR="${1:-/opt/xbot}"
REPO="${2:-}"
BOT_USER="xbot"

echo "=== X Bot Server Setup ==="
echo "Install dir : $INSTALL_DIR"
echo ""

# --- Create dedicated user ---
if ! id "$BOT_USER" &>/dev/null; then
    useradd --system --no-create-home --shell /usr/sbin/nologin "$BOT_USER"
    echo "Created system user: $BOT_USER"
fi

# --- Python 3.12 ---
if ! python3.12 --version &>/dev/null 2>&1; then
    apt-get update -q
    apt-get install -y python3.12 python3.12-venv python3-pip git
fi

# --- Clone or pull repo ---
if [ -n "$REPO" ]; then
    if [ -d "$INSTALL_DIR/.git" ]; then
        echo "Pulling latest..."
        git -C "$INSTALL_DIR" pull
    else
        mkdir -p "$(dirname "$INSTALL_DIR")"
        git clone "https://github.com/$REPO.git" "$INSTALL_DIR"
    fi
else
    mkdir -p "$INSTALL_DIR"
fi

# --- Virtualenv + deps ---
python3.12 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip -q
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q
echo "Dependencies installed."

# --- .env ---
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
    echo ""
    echo "*** ACTION REQUIRED: fill in $INSTALL_DIR/.env with your API keys ***"
fi

# --- Permissions ---
chown -R "$BOT_USER:$BOT_USER" "$INSTALL_DIR"
chmod 600 "$INSTALL_DIR/.env" 2>/dev/null || true
chmod +x "$INSTALL_DIR/run.sh"

# --- Cron ---
CRON_FILE="/etc/cron.d/xbot"
cat > "$CRON_FILE" << CRONEOF
SHELL=/bin/bash
# X Bot — posting schedule (all times UTC)
# Standard windows 4x/day
0  8  * * *  $BOT_USER  $INSTALL_DIR/run.sh post.py >> /var/log/xbot.log 2>&1
0  14 * * *  $BOT_USER  $INSTALL_DIR/run.sh post.py >> /var/log/xbot.log 2>&1
0  20 * * *  $BOT_USER  $INSTALL_DIR/run.sh post.py >> /var/log/xbot.log 2>&1
0  22 * * *  $BOT_USER  $INSTALL_DIR/run.sh post.py >> /var/log/xbot.log 2>&1
# Alpha fast-track: every 30min, only posts urgency-3 signals
*/30 * * * *  $BOT_USER  $INSTALL_DIR/run.sh post.py --alpha-only >> /var/log/xbot_alpha.log 2>&1
# Daily digest: 6 AM
0  6  * * *  $BOT_USER  $INSTALL_DIR/run.sh digest_run.py >> /var/log/xbot.log 2>&1
CRONEOF

chmod 644 "$CRON_FILE"
echo "Cron installed."

# --- Log files ---
touch /var/log/xbot.log /var/log/xbot_alpha.log
chown "$BOT_USER:$BOT_USER" /var/log/xbot.log /var/log/xbot_alpha.log

# --- Log rotation ---
cat > /etc/logrotate.d/xbot << LOGEOF
/var/log/xbot.log /var/log/xbot_alpha.log {
    daily
    rotate 14
    compress
    missingok
    notifempty
}
LOGEOF

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. nano $INSTALL_DIR/.env        — add your API keys"
echo "  2. $INSTALL_DIR/run.sh post.py   — test a manual run"
echo "  3. tail -f /var/log/xbot.log     — watch live logs"
echo "  4. Disable the old GitHub Actions bot (see deploy/STOP_OLD_BOT.md)"
