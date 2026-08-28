#!/usr/bin/env bash
# Keep the shared agent runner on pushed main without interrupting active loops.
set -euo pipefail

SOURCE_REPO="${LIFE_MANAGER_SOURCE_REPO:-$HOME/Projects/life-manager-main}"
LOOPS_ROOT="${LOOPS_ROOT:-$HOME/loops}"
CURRENT="$LOOPS_ROOT/current"

git -C "$SOURCE_REPO" fetch --quiet origin main
main_sha="$(git -C "$SOURCE_REPO" rev-parse origin/main)"
current_sha="$(jq -r .sha "$CURRENT/RELEASE.json")"

if [ "$main_sha" != "$current_sha" ]; then
  LOOPS_ROOT="$LOOPS_ROOT" LOOPS_RELEASE_PATHS= \
    bash "$SOURCE_REPO/bin/cut-loop-release.sh" origin/main
fi

exec "$CURRENT/bin/lm-loop" reconcile shared-agent-runner
