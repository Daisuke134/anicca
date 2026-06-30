#!/usr/bin/env bash
# loop-healthcheck.sh — REQ-A1..A9 self-heal classifier dispatcher.
# Invoked every 5min by launchd plist ai.anicca.<slot>-core-healthcheck.
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
has_session=false
tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null && has_session=true
pane_text=""
$has_session && pane_text="$(tmux -S "$SOCK" capture-pane -t "$SESSION" -p 2>/dev/null || true)"
now_ts=$(date +%s)
last_pass_mtime=""
[ -f "$LAST_PASS" ] && last_pass_mtime=$(stat -f %m "$LAST_PASS")
last_start_mtime=""
[ -f "$LAST_START" ] && last_start_mtime=$(stat -f %m "$LAST_START")
restart_log_entries=""
[ -f "$RESTART_LOG" ] && restart_log_entries=$(tr '\n' ',' < "$RESTART_LOG")

# Dispatch to lib/healthcheck.classify + per-mode action
python3 - <<PYEOF
import os, sys
sys.path.insert(0, "${SHARED_DIR}")
from lib.healthcheck import HealthcheckContext, Mode, classify

ctx = HealthcheckContext(
    slot="${SLOT}",
    pane_text="""${pane_text}""",
    has_session=${has_session^},
    last_pass_mtime=int("${last_pass_mtime}" or 0) or None,
    last_start_mtime=int("${last_start_mtime}" or 0) or None,
    restart_log_entries=[int(t) for t in "${restart_log_entries}".split(",") if t.strip()],
    cron_has_slot_job=True,  # TODO sprint-2: probe CronList for slot-specific job
    now_ts=${now_ts},
)
mode = classify(ctx)
print(f"mode: {mode.value}")
PYEOF
