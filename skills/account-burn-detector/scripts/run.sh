#!/usr/bin/env bash
# account-burn-detector — anicca-socials based, auto-disable cron jobs.
set -uo pipefail
[ -f ~/anicca-monk-factory/.env ] && set -a && source ~/anicca-monk-factory/.env && set +a
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

# Refresh anicca-socials snapshot if older than 25h
SNAP=~/.openclaw/skills/anicca-socials/state/socials_latest.json
if [ -f "$SNAP" ]; then
  AGE_S=$(($(date +%s) - $(stat -f %m "$SNAP" 2>/dev/null || stat -c %Y "$SNAP")))
  if [ "$AGE_S" -gt 90000 ]; then
    echo "⚠️ socials snapshot >25h old, refreshing first..."
    bash ~/.openclaw/skills/anicca-socials/scripts/run.sh || echo "warn: socials refresh failed"
  fi
else
  echo "ℹ️ no socials snapshot yet, running anicca-socials first..."
  bash ~/.openclaw/skills/anicca-socials/scripts/run.sh || { echo "❌ socials refresh failed"; exit 5; }
fi

exec python3 "$(dirname "$0")/run.py"
