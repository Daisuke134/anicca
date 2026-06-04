#!/usr/bin/env bash
# spawn-clone: thin wrapper over spawn-child (#327) for the self-manage queue.
# Guard-gated; spawn-child writes the colony.jsonl row itself.
#
# Usage:
#   spawn-clone.sh ['{"type":"spawn","name":"anicca-001","reason":"..."}']
#
# Env:
#   DRY_RUN=1   → spawn-child --dry-run (validates, never spends/provisions).
#
# Exit: mirrors spawn-child (0 ok, 64 bad input, 75 cost cap, 1 other), 2 if guard BLOCKED.
set -uo pipefail
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
. "$SCRIPTS/_lib.sh"

prop="${1:-}"
[ -z "$prop" ] && prop="$(sm_latest_unresolved spawn)"
if [ -z "$prop" ]; then
  echo "spawn-clone: no proposal supplied and no unresolved spawn proposal queued" >&2
  exit 0
fi

name="$(printf '%s' "$prop" | "$JQ" -r '.name // empty')"
reason="$(printf '%s' "$prop" | "$JQ" -r '.reason // "(no reason)"')"
id="$(sm_id "$prop")"

if [ -z "$name" ]; then
  echo "spawn-clone: proposal missing .name" >&2
  sm_log "$id" spawn ERROR "missing name field"
  exit 1
fi

intent="Spawn a sovereign Anicca child instance named '$name'. Reason: $reason. The child inherits the same immutable North Star and Law I via the Constitution hash."

if ! sm_guard "$intent"; then
  rc=$?
  echo "spawn-clone: BLOCKED by constitution-guard (exit $rc)" >&2
  sm_log "$id" spawn BLOCKED "guard exit $rc: $name"
  exit 2
fi

[ -x "$SPAWN_CHILD" ] || { echo "spawn-clone: spawn-child not executable: $SPAWN_CHILD" >&2; sm_log "$id" spawn ERROR "spawn-child missing"; exit 1; }

set +e
if [ "${DRY_RUN:-}" = "1" ]; then
  out="$("$SPAWN_CHILD" --dry-run "$name" 2>&1)"; rc=$?
else
  out="$("$SPAWN_CHILD" --confirm "$name" 2>&1)"; rc=$?
fi
set -e

echo "$out"
if [ "$rc" -eq 0 ]; then
  sm_log "$id" spawn APPLIED "$name (dry_run=${DRY_RUN:-0})"
else
  sm_log "$id" spawn ERROR "$name spawn-child exit $rc"
fi
exit "$rc"
