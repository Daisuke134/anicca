#!/usr/bin/env bash
# Keep the shared agent runner on pushed main without interrupting active loops.
set -euo pipefail

SOURCE_REPO="${LIFE_MANAGER_SOURCE_REPO:-$HOME/Projects/life-manager-main}"
LOOPS_ROOT="${LOOPS_ROOT:-$HOME/loops}"
CURRENT="$LOOPS_ROOT/current"

# Deliver an already-built release first. This is the fast path and keeps a
# concurrent release build from delaying safe idle-loop rollout.
if "$CURRENT/bin/lm-loop" reconcile shared-agent-runner; then
  :
elif ! "$CURRENT/bin/lm-loop" 2>&1 | grep -q 'reconcile'; then
  printf 'agent-runner reconcile deferred: current release predates reconcile\n' >&2
  exit 0
else
  exit 1
fi

git -C "$SOURCE_REPO" fetch --quiet origin main
main_sha="$(git -C "$SOURCE_REPO" rev-parse origin/main)"
current_sha="$(jq -r .sha "$CURRENT/RELEASE.json")"

if [ "$main_sha" != "$current_sha" ]; then
  LOOPS_ROOT="$LOOPS_ROOT" LOOPS_RELEASE_PATHS= \
    bash "$SOURCE_REPO/bin/cut-loop-release.sh" origin/main
fi

new_sha="$(jq -r .sha "$CURRENT/RELEASE.json")"
if [ "$new_sha" != "$main_sha" ]; then
  printf 'agent-runner reconcile deferred: current changed during release build\n' >&2
  exit 0
fi
exec "$CURRENT/bin/lm-loop" reconcile shared-agent-runner
