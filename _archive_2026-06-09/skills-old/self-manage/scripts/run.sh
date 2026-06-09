#!/usr/bin/env bash
# run: drain the self-manage proposal queue and dispatch each unresolved proposal by type
# (spec 18 §4). Idempotent — the decisions log is the resolution marker, so re-runs skip
# already-handled proposals.
#
# Emits ONE trace JSONL line to stdout + appends to self-manage.jsonl.
#
# Env:
#   DRY_RUN=1   propagate dry mode to every handler (no cron/PR/spawn/gh writes).
set -uo pipefail
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
. "$SCRIPTS/_lib.sh"

TRACE="$STATE_DIR/self-manage.jsonl"
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

handler_for() {
  case "$1" in
    heartbeat)  echo "$SCRIPTS/edit-heartbeat.sh" ;;
    skill-edit) echo "$SCRIPTS/edit-skill.sh" ;;
    spawn)      echo "$SCRIPTS/spawn-clone.sh" ;;
    arch-shift) echo "$SCRIPTS/architecture-shift.sh" ;;
    *)          echo "" ;;
  esac
}

n_seen=0 n_dispatched=0 n_skipped=0
if [ -s "$PROPOSALS" ]; then
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    n_seen=$((n_seen+1))
    type="$(printf '%s' "$line" | "$JQ" -r '.type // empty' 2>/dev/null)"
    id="$(sm_id "$line")"
    if sm_resolved "$id"; then
      n_skipped=$((n_skipped+1)); continue
    fi
    h="$(handler_for "$type")"
    if [ -z "$h" ] || [ ! -x "$h" ]; then
      echo "run: no handler for type '$type' (id $id)" >&2
      sm_log "$id" "${type:-unknown}" ERROR "no handler for type"
      continue
    fi
    "$h" "$line" >/dev/null 2>&1 || true
    n_dispatched=$((n_dispatched+1))
  done < "$PROPOSALS"
fi

line="$("$JQ" -nc \
  --arg ts "$NOW" \
  --argjson seen "$n_seen" \
  --argjson dispatched "$n_dispatched" \
  --argjson skipped "$n_skipped" \
  --argjson dry "$([ "${DRY_RUN:-}" = "1" ] && echo true || echo false)" \
  '{ts:$ts, seen:$seen, dispatched:$dispatched, skipped:$skipped, dry_run:$dry}')"

printf '%s\n' "$line" >> "$TRACE"
echo "$line"
