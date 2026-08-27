#!/bin/bash
# runtime/agentmail/nudge-tick.sh — daily Reply-Zero sweep. Fires via launchd at 09:00 JST.
set -uo pipefail
ENV_FILE="${HOME}/.openclaw/.env"
if [ -f "$ENV_FILE" ]; then set -a; . "$ENV_FILE"; set +a; fi
NODE="${NODE_BIN:-/opt/homebrew/bin/node}"
cd "$(dirname "$0")" || exit 1
LOG="${HOME}/.openclaw/logs/agentmail-nudge.log"
mkdir -p "$(dirname "$LOG")"
{
  echo "=== $(date -u +%FT%TZ) nudge sweep ==="
  "$NODE" nudge.ts
} >> "$LOG" 2>&1
