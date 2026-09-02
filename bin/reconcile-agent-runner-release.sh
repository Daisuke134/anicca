#!/usr/bin/env bash
# Keep managed runners on one complete pushed-main release without interrupting active loops.
set -euo pipefail

SOURCE_REPO="${LIFE_MANAGER_SOURCE_REPO:-$HOME/Projects/life-manager-main}"
LOOPS_ROOT="${LOOPS_ROOT:-$HOME/loops}"
CURRENT="$LOOPS_ROOT/current"

git -C "$SOURCE_REPO" fetch --quiet origin main
main_sha="$(git -C "$SOURCE_REPO" rev-parse origin/main)"
current_sha="$(jq -r '.sha // ""' "$CURRENT/RELEASE.json" 2>/dev/null || true)"
current_paths="$(jq -r '.release_paths // ""' "$CURRENT/RELEASE.json" 2>/dev/null || true)"
current_complete=0
[ "$current_paths" = "ALL" ] && current_complete=1

if [ "$main_sha" != "$current_sha" ] || [ "$current_complete" -ne 1 ]; then
  cutter="$CURRENT/bin/cut-loop-release.sh"
  [ -x "$cutter" ] || cutter="$SOURCE_REPO/bin/cut-loop-release.sh"
  LIFE_MANAGER_SOURCE_REPO="$SOURCE_REPO" LOOPS_ROOT="$LOOPS_ROOT" LOOPS_RELEASE_PATHS= \
    bash "$cutter" origin/main
fi

RELEASE_ROOT="$(cd "$CURRENT" && pwd -P)"
release_sha="$(jq -r '.sha // ""' "$RELEASE_ROOT/RELEASE.json")"
release_paths="$(jq -r '.release_paths // ""' "$RELEASE_ROOT/RELEASE.json")"
if [ "$release_sha" != "$main_sha" ] || [ "$release_paths" != "ALL" ]; then
  printf 'agent-runner reconcile refused: release is not the full pushed-main build\n' >&2
  exit 1
fi

status=0
if ! LIFE_MANAGER_RELEASE_ROOT="$RELEASE_ROOT" "$RELEASE_ROOT/bin/lm-loop" reconcile shared-agent-runner --loaded-idle-only --loop-id hf-gig-apply-direct; then
  status=1
fi
if ! LIFE_MANAGER_RELEASE_ROOT="$RELEASE_ROOT" "$RELEASE_ROOT/bin/lm-loop" reconcile shared-agent-runner --include-running --loop-id hf-gig-reply-detector; then
  status=1
fi
if ! LIFE_MANAGER_RELEASE_ROOT="$RELEASE_ROOT" "$RELEASE_ROOT/bin/lm-loop" reconcile deterministic --loaded-idle-only --loop-id hf-gig-storefront-direct --loop-id hf-gig-paid-direct --loop-id life-manager-disk-cleanup; then
  status=1
fi
exit "$status"
