#!/bin/sh
set -eu

ROOT=${LIFE_MANAGER_ROOT:-"$HOME/Projects/life-manager-main"}
PYTHON_BIN=${PYTHON_BIN:-$(command -v python3 || true)}
GOVERNOR="$ROOT/skills/self/disk-cleanup/disk_cleanup.py"

[ -x "$PYTHON_BIN" ] || exit 0
[ -f "$GOVERNOR" ] || exit 0
exec "$PYTHON_BIN" "$GOVERNOR" --home "$HOME" --state-dir "$HOME/.openclaw/state"
