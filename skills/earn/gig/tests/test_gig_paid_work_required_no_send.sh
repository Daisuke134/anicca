#!/usr/bin/env bash
# P0-1: a work_required pass must never reach a buyer-visible send path.
#
# work_required means one thing: the buyer is waiting on an artifact that does
# not exist yet. Three of the four send paths in gig_pass.sh already refuse it
# (run_paid_work's answer branch, the prior-answer recovery guard, and
# route_existing_revision_after_formal). The fourth -- the assess_paid_queue
# call in paid_lane_dispatch -- was gated only on PAID_QUEUE_ALREADY_ASSESSED,
# so a pass whose builder finished without binding the live buyer feedback fell
# through to a free-text browser agent whose prompt only forbids sending for
# action=none. That agent could, and did, turn an absent artifact into a
# promise ("まとまり次第あらためてお送りします").
#
# This pins the gate at the dispatch call site: work_required skips the send,
# progress and formal still send.
set -euo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d /tmp/gig-work-required-no-send.XXXXXX)
trap 'rm -rf "$TMP"' EXIT

# Pull the dispatcher out of the driver rather than sourcing it: gig_pass.sh
# re-execs into the worker launcher on line one.
extract() {
  sed -n "/^$1() {/,/^}$/p" "$SKILL_DIR/gig_pass.sh"
}

HARNESS="$TMP/harness.sh"
{
  printf 'set -uo pipefail\n'
  # Every step the dispatcher can take is recorded, so the assertion is about
  # what actually ran and not about how the guard is spelled.
  cat <<'STUBS'
CALL_LOG="${CALL_LOG:?}"
note() { printf '%s\n' "$1" >> "$CALL_LOG"; }
log() { :; }
record_failure() { note "record_failure:$1"; }
run_paid_work() { note "run_paid_work"; return 0; }
# The builder returned 0 but the refreshed queue still says work_required --
# exactly the live shape: an artifact exists on disk but is not bound to the
# buyer feedback that is open, so nothing sendable was produced.
refresh_paid_queue_after_builder() { note "refresh_paid_queue_after_builder"; return 0; }
assess_paid_queue() { note "BUYER_VISIBLE_SEND:assess_paid_queue"; return "${ASSESS_RC:-0}"; }
record_paid_work_browser_progress() { note "BUYER_VISIBLE_SEND:record_paid_work_browser_progress"; return 0; }
# A4: the project-scoped row for a delivery that was attempted and failed.
record_delivery_attempt_failed() { note "record_delivery_attempt_failed:$1"; }
STUBS
  extract paid_lane_dispatch
} > "$HARNESS"

grep -q '^paid_lane_dispatch() {' "$HARNESS" || { echo 'FAIL: paid_lane_dispatch was not extracted'; exit 1; }
# Pins the call, not one spelling of the guard around it. A4 added a failure
# recorder to the abort path; a canary that pins punctuation would fail for the
# wrong reason whenever that path legitimately grows. What must not drift is
# that the dispatcher aborts on a failed assess, which case 5 below asserts.
grep -q 'assess_paid_queue ||' "$HARNESS" || { echo 'FAIL: the assess call site was not extracted'; exit 1; }

dispatch() {  # dispatch <delivery_action> [workflow_action] -> prints the call log
  local action="$1" workflow="${2:-act}"
  local log_file="$TMP/calls-$action-$workflow-${ASSESS_RC:-0}.log"
  : > "$log_file"
  mkdir -p "$TMP/evidence-$action-$workflow"
  CALL_LOG="$log_file" \
  ASSESS_RC="${ASSESS_RC:-0}" \
  TOP_CLASS=buyer_feedback_or_revision \
  TOP_WORKFLOW_ACTION="$workflow" \
  TOP_ACTION="$action" \
  TOP_ID=4201 \
  TOP_JSON='{"queue_class":"buyer_feedback_or_revision"}' \
  TOP_BLOCKERS="" \
  PAID_QUEUE_ALREADY_ASSESSED=0 \
  PAID_PROGRESS_VALIDATED_CONTINUE_LOWER=0 \
  PAID_PROGRESS_FINALIZE_ONLY=0 \
  EVIDENCE_DIR="$TMP/evidence-$action-$workflow" \
  G="$SKILL_DIR" \
    bash -c ". '$HARNESS'; STEP_SKIPPED_POLICY=(); paid_lane_dispatch" >/dev/null 2>&1
  cat "$log_file"
}

refute() {  # refute <needle> <haystack> <message>
  if printf '%s\n' "$2" | grep -q "$1"; then
    echo "FAIL: $3"
    printf 'calls were:\n%s\n' "$2"
    exit 1
  fi
}

require() {  # require <needle> <haystack> <message>
  if ! printf '%s\n' "$2" | grep -q "$1"; then
    echo "FAIL: $3"
    printf 'calls were:\n%s\n' "$2"
    exit 1
  fi
}

# 1. work_required: the builder still runs (that is the whole point -- the
#    artifact has to get built), but nothing buyer-visible may follow it.
CALLS=$(dispatch work_required)
require '^run_paid_work$' "$CALLS" 'work_required must still reach the builder'
refute 'BUYER_VISIBLE_SEND' "$CALLS" \
  'work_required must never reach a buyer-visible send path (an absent artifact must not become a promise)'

# 2. work_required with no builder pass of its own (workflow action is not
#    "act", so run_paid_work is skipped) must still not send.
CALLS=$(dispatch work_required deliver_existing)
refute 'BUYER_VISIBLE_SEND' "$CALLS" \
  'work_required must not send even when the builder step was skipped this pass'

# 3. The gate must be exactly this narrow: a real artifact still ships.
CALLS=$(dispatch progress)
require 'BUYER_VISIBLE_SEND:assess_paid_queue' "$CALLS" \
  'action=progress must still deliver to the buyer'
CALLS=$(dispatch formal)
require 'BUYER_VISIBLE_SEND:assess_paid_queue' "$CALLS" \
  'action=formal must still deliver to the buyer'

# 4. A4: a delivery that was attempted and failed must leave a project-scoped
#    row. record_failure writes ~/gig/pass-failures.jsonl, which no reader of a
#    project ever opens, so without this the next pass cannot tell a failed send
#    from a send that was never attempted -- and rebuilds. Measured 2026-08-07 on
#    order 91000002: the last project event was paid_work_ready_for_browser, with
#    no row saying sent and none saying not sent.
CALLS=$(ASSESS_RC=1 dispatch formal)
require 'record_delivery_attempt_failed' "$CALLS" \
  'a failed delivery must be recorded in the project ledger, not only in the pass log'
refute 'BUYER_VISIBLE_SEND:record_paid_work_browser_progress' "$CALLS" \
  'a failed assess must abort the dispatch, never fall through to the sent-reconciler'

# ---------------------------------------------------------------------------
# The same rule one level down, inside run_paid_work's answer branch -- and the
# one exception it now has.
#
# work_required refusing to answer is what made the fabricated delivery on order
# 91000002 the cheapest move: the buyer had specified nothing, the builder could
# not build, and the only branch that could have said so out loud was closed.
# So the refusal now yields to exactly one thing: the builder's own BLOCKED
# record for the feedback that is currently open. Nothing else moves.
GUARD="$TMP/guard.sh"
{
  printf 'set -uo pipefail\n'
  cat <<'STUBS'
CALL_LOG="${CALL_LOG:?}"
note() { printf '%s\n' "$1" >> "$CALL_LOG"; }
log() { :; }
record_failure() { note "record_failure:$1"; }
answer_guard() {
  local answer_file="$TOP_PROJECT_ROOT/delivery/paid-answer.json"
  local transaction_ledger="$LEDGER"
STUBS
  # Verbatim from the driver: the assertion is about the shipped guard, not a copy of it.
  awk '/paid_work_fresh_blocked; then$/{f=1} f{print} f && /^    fi$/{exit}' \
    "$SKILL_DIR/gig_pass.sh"
  printf '  note "ANSWER_SENT"\n  return 0\n}\n'
  extract paid_work_fresh_blocked
  # The boolean delegates to the verdict reader, and the guard asks that reader again to
  # choose between the two refusal names. Both have to come along, verbatim.
  extract paid_work_blocked_verdict
} > "$GUARD"

grep -q 'answer_forbidden_for_work_required' "$GUARD" \
  || { echo 'FAIL: the answer guard was not extracted from gig_pass.sh'; exit 1; }
grep -q '^paid_work_fresh_blocked() {' "$GUARD" \
  || { echo 'FAIL: paid_work_fresh_blocked was not extracted'; exit 1; }
grep -q '^paid_work_blocked_verdict() {' "$GUARD" \
  || { echo 'FAIL: paid_work_blocked_verdict was not extracted'; exit 1; }

FRESH_SHA=57b8719d5bd8ff77a7f68614fd9e9e6a4dbc35411094f43fd82891a103bdcfda

make_project() {  # make_project <name> <blocked_sha|none|corrupt> -> prints project root
  local root="$TMP/project-$1"
  mkdir -p "$root/delivery" "$root/requirements" "$root/evidence"
  printf '{"feedback_sha256":"%s"}\n' "$FRESH_SHA" > "$root/requirements/live-buyer-reply.json"
  printf 'question\n' > "$root/delivery/paid-answer.json"
  if [ "$2" = "corrupt" ]; then
    printf '{"version":1,"status":"BLOC' > "$root/evidence/acceptance-blocked.json"
  elif [ "$2" != "none" ]; then
    printf '{"version":1,"status":"BLOCKED","requirements_path":"%s","feedback_sha256":"%s","checks":[{"command":"find .","result":"制作指示がありません。"}],"blocker":"仕様未指定"}\n' \
      "$root/requirements/live-buyer-reply.json" "$2" > "$root/evidence/acceptance-blocked.json"
  fi
  printf '%s\n' "$root"
}

guard() {  # guard <delivery_action> <project_root> -> prints the call log
  local log_file="$TMP/guard-$1-$(basename "$2").log"
  : > "$log_file"
  CALL_LOG="$log_file" \
  LEDGER="$TMP/absent-ledger.json" \
  TOP_ACTION="$1" \
  TOP_TALKROOM_URL="https://coconala.com/talkrooms/4201" \
  TOP_PROJECT_ROOT="$2" \
  G="$SKILL_DIR" \
    bash -c ". '$GUARD'; answer_guard" >/dev/null 2>&1
  cat "$log_file"
}

# 4. work_required with no BLOCKED record is refused exactly as before. This is
#    the proof that the exception below is an exception and not an escape hatch.
CALLS=$(guard work_required "$(make_project plain none)")
require 'record_failure:paid_work_answer_forbidden_for_work_required' "$CALLS" \
  'work_required without a BLOCKED record must still be refused'
refute 'ANSWER_SENT' "$CALLS" 'work_required without a BLOCKED record must not send'

# 3. work_required plus the builder's BLOCKED record for the current feedback:
#    the question travels out on the paid talkroom.
CALLS=$(guard work_required "$(make_project blocked "$FRESH_SHA")")
require 'ANSWER_SENT' "$CALLS" \
  'a blocked paid order must be able to ask its buyer instead of inventing a deliverable'
refute 'record_failure' "$CALLS" 'asking a blocked buyer is not a pass failure'

# A BLOCKED record the buyer has already answered is spent. Without this the
# first unanswerable pass would hold the answer path open forever.
#
# It is refused under its own name. "No record at all" and "a record about a message the
# buyer has already replaced" are different situations, and reporting both as
# paid_work_answer_forbidden_for_work_required is how 91000002 spent five days looking like
# one problem. The stale name is also what the next pass's builder clause keys on.
CALLS=$(guard work_required "$(make_project stale $(printf 'a%.0s' $(seq 64)))")
require 'record_failure:paid_work_answer_forbidden_stale_blocked_record' "$CALLS" \
  'a stale BLOCKED record must not keep the answer path open'
refute 'ANSWER_SENT' "$CALLS" 'a stale BLOCKED record must not send'

# Undeterminable must not unlock. Note this is the OPPOSITE direction from
# validate_paid_work(), where an undeterminable verdict is an error that stops a
# delivery -- here it must simply fail to open the exception. Both say "when we
# cannot see, do not act"; they differ because one gate is asked "may I ship?"
# and this one is asked "may I skip building?".
CALLS=$(guard work_required "$(make_project corrupt corrupt)")
require 'record_failure:paid_work_answer_forbidden_for_work_required' "$CALLS" \
  'an unreadable BLOCKED record must not unlock the answer path'
refute 'ANSWER_SENT' "$CALLS" 'an unreadable BLOCKED record must not send'

# The guard is about work_required only; every other action answers as before.
CALLS=$(guard progress "$(make_project progress none)")
require 'ANSWER_SENT' "$CALLS" 'action=progress must still be able to answer the buyer'

echo 'PASS: work_required reaches the builder and never a buyer-visible send'
echo 'PASS: work_required answers only when the builder is blocked on the current feedback'
