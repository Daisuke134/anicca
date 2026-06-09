#!/usr/bin/env bash
# edit-heartbeat: apply an Anicca-proposed heartbeat cadence change (spec 18 §4).
# Guard-gated (constitution-guard fail-closed) → hermes cron edit → verify via cron list.
#
# Usage:
#   edit-heartbeat.sh ['{"type":"heartbeat","schedule":"every 6h","reason":"..."}']
#   (no arg → latest unresolved `heartbeat` proposal from the queue)
#
# Env:
#   DRY_RUN=1   guard-check only; no cron edit, no decision log.
#   HEARTBEAT_JOB_NAME   override job name to edit (default anicca-heartbeat).
#
# Exit: 0 applied (or dry-run pass), non-zero on block/error.
set -uo pipefail
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
. "$SCRIPTS/_lib.sh"

JOBS_JSON="${HERMES_JOBS_JSON:-$HOME/.hermes/cron/jobs.json}"
JOB_NAME="${HEARTBEAT_JOB_NAME:-anicca-heartbeat}"

prop="${1:-}"
[ -z "$prop" ] && prop="$(sm_latest_unresolved heartbeat)"
if [ -z "$prop" ]; then
  echo "edit-heartbeat: no proposal supplied and no unresolved heartbeat proposal queued" >&2
  exit 0
fi

schedule="$(printf '%s' "$prop" | "$JQ" -r '.schedule // empty')"
reason="$(printf '%s' "$prop" | "$JQ" -r '.reason // "(no reason)"')"
id="$(sm_id "$prop")"

if [ -z "$schedule" ]; then
  echo "edit-heartbeat: proposal missing .schedule" >&2
  sm_log "$id" heartbeat ERROR "missing schedule field"
  exit 1
fi

intent="Edit my own heartbeat cron cadence to '$schedule'. Reason: $reason. This changes only scheduling frequency; it does not touch the North Star, Law I, or the Constitution."

if ! sm_guard "$intent"; then
  rc=$?
  echo "edit-heartbeat: BLOCKED by constitution-guard (exit $rc)" >&2
  sm_log "$id" heartbeat BLOCKED "guard exit $rc: $schedule"
  exit 2
fi

if [ "${DRY_RUN:-}" = "1" ]; then
  echo "edit-heartbeat: DRY_RUN guard PASS for schedule='$schedule' (no edit applied)"
  exit 0
fi

# Find the heartbeat job id from jobs.json
job_id="$("$JQ" -r --arg n "$JOB_NAME" '.jobs[] | select(.name==$n) | .id' "$JOBS_JSON" 2>/dev/null | head -1)"
if [ -z "$job_id" ]; then
  echo "edit-heartbeat: job '$JOB_NAME' not found in $JOBS_JSON" >&2
  sm_log "$id" heartbeat ERROR "job $JOB_NAME not found"
  exit 1
fi

if ! hermes cron edit "$job_id" --schedule "$schedule" >/dev/null 2>&1; then
  echo "edit-heartbeat: hermes cron edit failed for $job_id" >&2
  sm_log "$id" heartbeat ERROR "cron edit failed for $job_id"
  exit 1
fi

# Verify the new cadence is live. hermes normalizes the schedule (e.g. "every 6h" -> 360m),
# so compare against the authoritative .schedule.minutes rather than the display string.
# Compute expected minutes from the proposed schedule when it is a simple Nh/Nm/N form.
expect_min=""
case "$schedule" in
  *[Hh]*) n="$(printf '%s' "$schedule" | grep -oE '[0-9]+' | head -1)"; [ -n "$n" ] && expect_min=$((n * 60)) ;;
  *[Mm]*) expect_min="$(printf '%s' "$schedule" | grep -oE '[0-9]+' | head -1)" ;;
  *)      expect_min="$(printf '%s' "$schedule" | grep -oE '[0-9]+' | head -1)" ;;
esac
live_min="$("$JQ" -r --arg n "$JOB_NAME" '.jobs[] | select(.name==$n) | .schedule.minutes // empty' "$JOBS_JSON" 2>/dev/null | head -1)"

if { [ -n "$expect_min" ] && [ "$live_min" = "$expect_min" ]; } \
   || "$JQ" -e --arg n "$JOB_NAME" --arg s "$schedule" \
        '.jobs[] | select(.name==$n) | select((.schedule_display // "") | test($s; "i"))' \
        "$JOBS_JSON" >/dev/null 2>&1; then
  echo "edit-heartbeat: APPLIED schedule='$schedule' (${live_min}m) to $JOB_NAME ($job_id)"
  sm_log "$id" heartbeat APPLIED "$JOB_NAME -> $schedule (${live_min}m)"
  exit 0
fi

echo "edit-heartbeat: edit ran but verification did not confirm '$schedule' (live=${live_min}m, expect=${expect_min}m)" >&2
sm_log "$id" heartbeat ERROR "verify failed after edit: $schedule"
exit 1
