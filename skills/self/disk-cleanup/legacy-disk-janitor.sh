#!/bin/sh
set -eu

ROOT=${MR_BOT_ROOT:-"$HOME/Projects/mr-bot-main"}
PYTHON_BIN=${PYTHON_BIN:-$(command -v python3 || true)}
GOVERNOR="$ROOT/skills/self/disk-cleanup/disk_cleanup.py"
EMERGENCY_GUARD=${EMERGENCY_GUARD_PATH:-"$HOME/scripts/emergency-disk-guard.sh"}

# The hourly legacy label is a compatibility trigger, not a second cleaner.
# When the host guard is installed, ask that same authority for its bounded
# full pass so deferred worktree/remote checks are eventually serviced. A
# portable Mr.bot checkout without the host adapter keeps the normal
# governor fallback below.
if [ -x "$EMERGENCY_GUARD" ]; then
  exec env EMERGENCY_GUARD_FULL_PASS=1 "$EMERGENCY_GUARD"
fi

[ -x "$PYTHON_BIN" ] || exit 0
[ -f "$GOVERNOR" ] || exit 0
exec "$PYTHON_BIN" "$GOVERNOR" --home "$HOME" --state-dir "$HOME/.openclaw/state"
