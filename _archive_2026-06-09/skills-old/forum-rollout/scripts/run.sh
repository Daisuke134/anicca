#!/usr/bin/env bash
# run.sh — cron entry for forum-rollout (#338). --confirm IFF the Dais escape-hatch
# flag ~/.hermes/state/rollout-allow.flag exists; else --dry-run (Wave-1 safe default).
set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
FLAG="${ROLLOUT_ALLOW_FLAG:-$HOME/.hermes/state/rollout-allow.flag}"
if [ -f "$FLAG" ]; then
  exec "$DIR/rollout.sh" --confirm
else
  exec "$DIR/rollout.sh" --dry-run
fi
