#!/usr/bin/env bash
# E2E: synthetic heartbeat proposal "every 6h" → edit-heartbeat.sh → constitution-guard PASS
# → hermes cron edit applied → verify cron shows the new cadence → REVERT to "every 3h".
#
# This test makes a REAL (but reverted) edit to the anicca-heartbeat cron so it proves the
# whole path. It isolates the proposal/decision state under a temp STATE_DIR; the cron edit
# itself is global and is restored in cleanup.
set -uo pipefail
SCRIPTS="$(cd "$(dirname "$0")/../scripts" && pwd)"
JQ=/usr/bin/jq
JOB_NAME=anicca-heartbeat
JOBS_JSON="$HOME/.hermes/cron/jobs.json"

pass=0; fail=0
ok()   { echo "PASS: $1"; pass=$((pass+1)); }
bad()  { echo "FAIL: $1"; fail=$((fail+1)); }

# Capture the original schedule so cleanup restores EXACTLY what was there.
ORIG_MIN="$("$JQ" -r --arg n "$JOB_NAME" '.jobs[]|select(.name==$n)|.schedule.minutes' "$JOBS_JSON" 2>/dev/null)"
ORIG_DISPLAY="$("$JQ" -r --arg n "$JOB_NAME" '.jobs[]|select(.name==$n)|.schedule_display' "$JOBS_JSON" 2>/dev/null)"
JOB_ID="$("$JQ" -r --arg n "$JOB_NAME" '.jobs[]|select(.name==$n)|.id' "$JOBS_JSON" 2>/dev/null)"

# Isolated state dir for proposals/decisions (cron is global, handled separately).
export STATE_DIR; STATE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/sm-e2e-XXXX" 2>/dev/null || mktemp -d)"

restore() {
  # Revert the heartbeat cron back to its original cadence if we have a job id + original.
  if [ -n "${JOB_ID:-}" ] && [ -n "${ORIG_MIN:-}" ] && [ "${ORIG_MIN}" != "null" ]; then
    hermes cron edit "$JOB_ID" --schedule "every ${ORIG_MIN}m" >/dev/null 2>&1 || true
  fi
  rm -rf "$STATE_DIR" 2>/dev/null || true
}
trap restore EXIT

# ---- Guard sanity: a Law-I / North-Star-touching intent must be BLOCKED, a cadence one OK.
if [ -z "$JOB_ID" ] || [ "$JOB_ID" = "null" ]; then
  bad "could not find $JOB_NAME job id in $JOBS_JSON (cannot run cron E2E)"
  echo "RESULT: $pass passed, $fail failed"; [ "$fail" -eq 0 ]; exit $?
fi

# ---- 1. Queue a synthetic heartbeat proposal in the isolated STATE_DIR.
PROP='{"type":"heartbeat","schedule":"every 6h","reason":"reduce LLM cost"}'
printf '%s\n' "$PROP" > "$STATE_DIR/self-manage-proposals.jsonl"

# ---- 2. Run the orchestrator (real cron edit, isolated decision log).
HEARTBEAT_JOB_NAME="$JOB_NAME" bash "$SCRIPTS/run.sh" >/dev/null 2>&1 || true

# ---- 3. Verify the decision log recorded APPLIED for a heartbeat proposal.
if [ -s "$STATE_DIR/self-manage-decisions.jsonl" ] && \
   "$JQ" -e 'select(.type=="heartbeat" and .decision=="APPLIED")' \
        "$STATE_DIR/self-manage-decisions.jsonl" >/dev/null 2>&1; then
  ok "decision log has APPLIED heartbeat row"
else
  bad "no APPLIED heartbeat row in decision log"
  echo "--- decisions ---"; cat "$STATE_DIR/self-manage-decisions.jsonl" 2>/dev/null
fi

# ---- 4. Verify the live cron cadence is now 360m (every 6h).
NEW_MIN="$("$JQ" -r --arg n "$JOB_NAME" '.jobs[]|select(.name==$n)|.schedule.minutes' "$JOBS_JSON" 2>/dev/null)"
if [ "$NEW_MIN" = "360" ]; then
  ok "cron cadence applied: $JOB_NAME = ${NEW_MIN}m (every 6h)"
else
  bad "cron cadence not applied: expected 360m, got ${NEW_MIN}m"
fi

# ---- 5. Idempotency: re-run should SKIP (already resolved), no second APPLIED row.
BEFORE="$(wc -l < "$STATE_DIR/self-manage-decisions.jsonl" 2>/dev/null || echo 0)"
HEARTBEAT_JOB_NAME="$JOB_NAME" bash "$SCRIPTS/run.sh" >/dev/null 2>&1 || true
AFTER="$(wc -l < "$STATE_DIR/self-manage-decisions.jsonl" 2>/dev/null || echo 0)"
if [ "$BEFORE" = "$AFTER" ]; then
  ok "idempotent re-run added no new decision rows ($AFTER)"
else
  bad "re-run was not idempotent (before=$BEFORE after=$AFTER)"
fi

# ---- 6. Verify revert path works (explicit, before trap also runs it).
hermes cron edit "$JOB_ID" --schedule "every ${ORIG_MIN}m" >/dev/null 2>&1 || true
REV_MIN="$("$JQ" -r --arg n "$JOB_NAME" '.jobs[]|select(.name==$n)|.schedule.minutes' "$JOBS_JSON" 2>/dev/null)"
if [ "$REV_MIN" = "$ORIG_MIN" ]; then
  ok "reverted cadence to original ${ORIG_MIN}m"
else
  bad "revert failed: expected ${ORIG_MIN}m, got ${REV_MIN}m"
fi

echo "RESULT: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
