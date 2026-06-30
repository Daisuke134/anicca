#!/usr/bin/env bash
# proactive-loop.sh — single 5-min cron entry, 8-step body (sprint-2).
# Per Sutando-derived design. Invoked by per-slot launchd plist.
# SECURITY: ENV VAR pattern (no heredoc $-interpolation per FIND-2-001 sprint-1).
#
# Usage: proactive-loop.sh <slot>
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

export ANICCA_SLOT="${1:-}"
export ANICCA_SHARED_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="${HOME}/.openclaw/logs/${ANICCA_SLOT}-proactive.log"
mkdir -p "$(dirname "$LOG")"
LOCK="${HOME}/loops/${ANICCA_SLOT}/.proactive.lock"
mkdir -p "$(dirname "$LOCK")"

# NFR-3 re-entrancy: flock guards concurrent ticks
exec 200>"$LOCK"
flock -n 200 || { echo "$(date '+%F %T') proactive-loop: another tick in progress, exit"; exit 0; }

exec python3 "$ANICCA_SHARED_DIR/proactive-loop-dispatch.py" 2>&1 | tee -a "$LOG"
