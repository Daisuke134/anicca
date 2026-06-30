#!/usr/bin/env bash
# loop-healthcheck.sh — REQ-A1..A9 self-heal classifier dispatcher.
# Invoked every 5min by launchd plist ai.anicca.<slot>-core-healthcheck.
#
# SECURITY: untrusted pane text is passed via ENV VAR (not heredoc interpolation)
# to prevent shell→Python injection. FIND-2-001 fix.
#
# Usage: loop-healthcheck.sh <slot>
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

SLOT="${1:-}"
SOCK="/tmp/anicca-${SLOT}-tmux.sock"
SESSION="anicca-${SLOT}-core"
LAST_PASS="${HOME}/loops/${SLOT}/.last-pass"
LAST_START="${HOME}/loops/${SLOT}/.last-start"
RESTART_LOG="${HOME}/loops/${SLOT}/.restart-log"
SHARED_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Snapshot HealthcheckContext
ANICCA_HAS_SESSION=false
tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null && ANICCA_HAS_SESSION=true
export ANICCA_HAS_SESSION
export ANICCA_PANE_TEXT=""
if [ "$ANICCA_HAS_SESSION" = "true" ]; then
    ANICCA_PANE_TEXT="$(tmux -S "$SOCK" capture-pane -t "$SESSION" -p 2>/dev/null || true)"
    export ANICCA_PANE_TEXT
fi
export ANICCA_NOW_TS=$(date +%s)
export ANICCA_LAST_PASS_MTIME=""
[ -f "$LAST_PASS" ] && export ANICCA_LAST_PASS_MTIME=$(stat -f %m "$LAST_PASS")
export ANICCA_LAST_START_MTIME=""
[ -f "$LAST_START" ] && export ANICCA_LAST_START_MTIME=$(stat -f %m "$LAST_START")
export ANICCA_RESTART_LOG=""
[ -f "$RESTART_LOG" ] && export ANICCA_RESTART_LOG="$(cat "$RESTART_LOG")"
export ANICCA_SLOT="$SLOT"
export ANICCA_SHARED_DIR="$SHARED_DIR"

# Run classifier — Python reads from os.environ, NOT from string interpolation.
exec python3 "$SHARED_DIR/loop-healthcheck-dispatch.py"
