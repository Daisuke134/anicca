#!/usr/bin/env bash
# content-metrics dispatcher. MODE = daily | zero_view | rollup.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
MODE="${MODE:-daily}"

case "$MODE" in
  daily)     exec bash "$SKILL_DIR/daily.sh" ;;
  zero_view) exec bash "$SKILL_DIR/zero_view.sh" ;;
  rollup)    exec bash "$SKILL_DIR/rollup.sh" ;;
  *)
    echo "Unknown MODE: $MODE (expected daily|zero_view|rollup)" >&2
    exit 64
    ;;
esac
