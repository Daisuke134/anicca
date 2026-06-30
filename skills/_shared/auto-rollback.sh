#!/usr/bin/env bash
# auto-rollback.sh — REQ-H3(f) spawn-surface auto-rollback (sprint-2).
# git fetch + checkout last anicca-bot signed commit of _shared/.
# NO human-touch.
#
# Usage: auto-rollback.sh <slot>
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

export ANICCA_SLOT="${1:-}"
LOG="${HOME}/.openclaw/logs/${ANICCA_SLOT}-auto-rollback.log"
mkdir -p "$(dirname "$LOG")"

ANICCA_ROOT="${HOME}/anicca"
cd "$ANICCA_ROOT" || exit 2

# Sprint-2 cycle 2 wires: fetch origin/main; find last commit -S signed by anicca-bot key;
# git checkout <sha> -- skills/_shared/; re-validate verify_spawn_surface.
# Scaffold: log only.
echo "$(date '+%F %T') auto-rollback: scaffold for slot $ANICCA_SLOT (cycle 2 wires)" >> "$LOG"
exit 1
