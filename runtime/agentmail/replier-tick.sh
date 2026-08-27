#!/bin/bash
# runtime/agentmail/replier-tick.sh — fires every 5 minutes via launchd.
# Drains the webhook queue into SQLite, then runs Anicca's reply loop on any
# unreplied inbound mail.
set -uo pipefail
ENV_FILE="${HOME}/.openclaw/.env"
if [ -f "$ENV_FILE" ]; then set -a; . "$ENV_FILE"; set +a; fi
NODE="${NODE_BIN:-/opt/homebrew/bin/node}"
cd "$(dirname "$0")" || exit 1
LOG="${HOME}/.openclaw/logs/agentmail-replier.log"
mkdir -p "$(dirname "$LOG")"
{
  echo "=== $(date -u +%FT%TZ) tick ==="
  "$NODE" ingest.ts
  "$NODE" replier.ts
} >> "$LOG" 2>&1
