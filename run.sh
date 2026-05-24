#!/usr/bin/env bash
# Wrapper used by cron on the Hetzner server.
# Loads .env then runs post.py (or any other script passed as args).
#
# Usage (cron calls this directly):
#   /opt/xbot/run.sh post.py
#   /opt/xbot/run.sh post.py --alpha-only
#   /opt/xbot/run.sh digest_run.py

set -euo pipefail
cd "$(dirname "$0")"

if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

exec .venv/bin/python "$@"
