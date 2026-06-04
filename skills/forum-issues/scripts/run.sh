#!/usr/bin/env bash
# run.sh — orchestrator: ② poll (ACK) then ③ respond (one DISCUSS round).
# Idempotent: with no new mentions both stages are no-ops and exit 0.
# Invoked by the forum-issues cron (every 3h) via ~/.hermes/scripts/forum-issues.sh.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== forum-issues run $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
bash "$DIR/poll.sh"
bash "$DIR/respond.sh"
