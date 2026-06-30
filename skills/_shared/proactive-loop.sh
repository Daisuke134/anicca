#!/usr/bin/env bash
# proactive-loop.sh — single 5-min cron entry, 8-step body (sprint-2).
# Per Sutando-derived design. Invoked by per-slot launchd plist.
# SECURITY: ENV VAR pattern (no heredoc $-interpolation per FIND-2-001 sprint-1).
# Lock: fcntl in Python (cross-platform: macOS has no flock(1); Linux still works).
#
# Usage: proactive-loop.sh <slot>
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

export ANICCA_SLOT="${1:-}"
export ANICCA_SHARED_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="${HOME}/.openclaw/logs/${ANICCA_SLOT}-proactive.log"
mkdir -p "$(dirname "$LOG")"
: "${ANICCA_LOCK_PATH:=${HOME}/loops/${ANICCA_SLOT}/.proactive.lock}"
export ANICCA_LOCK_PATH
mkdir -p "$(dirname "$ANICCA_LOCK_PATH")"

# NFR-3 re-entrancy: fcntl.flock inside dispatch (cross-platform; macOS has no flock(1)).
exec python3 "$ANICCA_SHARED_DIR/proactive-loop-dispatch.py" 2>&1 | tee -a "$LOG"
