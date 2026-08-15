#!/usr/bin/env bash
# A13 exit proof: one jammed order no longer stops the business.
#
# ★ This runs the real gig_pass.sh against SANDBOX COPIES of the real state. ★ HOME is a
# throwaway directory; the live ~/gig is only ever read. No browser, no model call, no
# production entrypoint: the agent runner is a stub that fails, and the paid validator
# docker path is deliberately absent so the builder cannot start.
#
# What it reproduces, measured 2026-08-08 06:02:
#   91000001  eight trailing queue_selected rows, nothing else -- twelve consecutive
#            passes picked it, none of them moved it
#   91000002  a different paying customer, untouched for eight hours behind it
#   B2       "skipped (policy B2:unresolved_higher_priority_queue:...:91000001)"
#
# What it asserts after the change:
#   1. the jam is skipped, and the skip says why, out loud
#   2. the pass reaches 91000002 and produces its delivery decision
#   3. B2 runs with the paid queue in exactly that unresolved state
#   4. the skip is durable in the skipped order's OWN ledger
#   5. one customer never gets two orders in flight at once
#   6. a permanently skipped order escalates
#   7. nothing was sent to anybody
#
# It reads live state, so it is a proof harness rather than a hermetic unit test: it is a
# .sh file and pytest does not collect it. It SKIPs cleanly when the live state is gone.
set -uo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
LIVE="${GIG_LIVE_STATE_DIR:-$HOME/gig}"

SNAPSHOT_SRC=$(ls -t "$LIVE"/evidence/gig-pass-*/marketplace-snapshot.json 2>/dev/null | head -1)
if [ -z "$SNAPSHOT_SRC" ]; then
  echo "SKIP: no live marketplace snapshot under $LIVE/evidence"
  exit 0
fi

TMP=$(mktemp -d /tmp/gig-head-of-line.XXXXXX)
trap 'rm -rf "$TMP"' EXIT
SANDBOX="$TMP/home"
mkdir -p "$SANDBOX/gig/projects" "$SANDBOX/gig/delivery-evidence" \
         "$SANDBOX/anicca/skills/browser/scripts" \
         "$SANDBOX/life-manager/skills/agent-runner"

# ── sandbox copies of the real state ──────────────────────────────────────────────────
# ~/gig/projects is 17GB. Only the two files the admission planner and the queue builder
# read are copied per order; the artifacts stay where they are and are read in place.
cp "$SNAPSHOT_SRC" "$SANDBOX/snapshot.json"
cp "$LIVE"/delivery-evidence/*.json "$SANDBOX/gig/delivery-evidence/" 2>/dev/null
for identity in $(python3 - "$SANDBOX/snapshot.json" <<'PY'
import json, sys
snapshot = json.load(open(sys.argv[1], encoding="utf-8"))
for order in snapshot.get("orders", []):
    value = order.get("request_id") or order.get("talkroom_id") or order.get("contract_id")
    if value:
        print(value)
PY
); do
  [ -d "$LIVE/projects/$identity" ] || continue
  mkdir -p "$SANDBOX/gig/projects/$identity"
  for name in state.json events.jsonl; do
    [ -f "$LIVE/projects/$identity/$name" ] && cp "$LIVE/projects/$identity/$name" \
      "$SANDBOX/gig/projects/$identity/$name"
  done
done

# The reply and follow-up lanes are not what this proves, and keeping them out removes
# every path that could reach a buyer.
python3 - "$SANDBOX/snapshot.json" <<'PY'
import json, sys
path = sys.argv[1]
snapshot = json.load(open(path, encoding="utf-8"))
snapshot["inquiries"] = []
json.dump(snapshot, open(path, "w", encoding="utf-8"), ensure_ascii=False)
PY

cat > "$SANDBOX/life-manager/skills/agent-runner/agent_runner.py" <<'PY'
#!/usr/bin/env python3
"""Records that it was asked, spends nothing, and fails."""
import os, sys
argv = sys.argv[1:]
label = ""
for index, arg in enumerate(argv):
    if arg == "--task-label" and index + 1 < len(argv):
        label = argv[index + 1]
with open(os.environ["GIG_STEP_CALL_LOG"], "a", encoding="utf-8") as handle:
    handle.write(label + "\n")
raise SystemExit(42)
PY
chmod +x "$SANDBOX/life-manager/skills/agent-runner/agent_runner.py"

CALL_LOG="$TMP/model-calls.txt"; : > "$CALL_LOG"

run_pass() { # extra env assignments come from the caller's environment
  HOME="$SANDBOX" \
  GIG_SKILL_DIR="$SKILL_DIR" \
  GIG_AGENT_RUNNER="$SANDBOX/life-manager/skills/agent-runner/agent_runner.py" \
  GIG_QUEUE_FIXTURE="$SANDBOX/snapshot.json" \
  GIG_TODAY="${GIG_TODAY_OVERRIDE:-2026-08-08}" \
  GIG_WORKER_LEASE_ACTIVE=1 \
  GIG_LOCK_DIR="$TMP/lock.d" \
  GIG_STEP_CALL_LOG="$CALL_LOG" \
  GIG_PAID_VALIDATOR_DOCKER="$TMP/there-is-no-docker-here" \
  GIG_PAID_MAX_ORDERS_PER_PASS="${MAX_ORDERS:-1}" \
  bash "$SKILL_DIR/gig_pass.sh" >"$1.out" 2>"$1.err"
  echo $?
}

fails=0
check() { if [ "$2" = "$3" ]; then echo "PASS  $1"; else echo "FAIL  $1  expected=$2 got=$3"; fails=$((fails+1)); fi; }
has()   { grep -qF "$2" "$1" && echo yes || echo no; }

echo "=== pass 1: the jam is still exactly as it is on the live loop ==="
rc=$(run_pass "$TMP/pass1")
ERR="$TMP/pass1.err"

check "the jammed order is skipped, with its reason" yes \
  "$(has "$ERR" 'STEP PAID_ADMISSION skipped id=91000001 reason=no_progress_after_selections')"
check "the skip says how stuck it is" yes \
  "$(grep -qE 'skipped id=91000001 .*selections_without_progress=[2-9]' "$ERR" && echo yes || echo no)"
check "★ the pass reaches the next customer ★" yes \
  "$(grep -qE 'queue top class=[a-z_]+ id=91000002 ' "$ERR" && echo yes || echo no)"
check "and produces its delivery decision" yes \
  "$(grep -qE 'queue top .*id=91000002 action=[a-z_]+' "$ERR" && echo yes || echo no)"
check "★ the apply lane no longer waits on the paid queue ★" no \
  "$(has "$ERR" 'unresolved_higher_priority_queue')"
check "B2 was reached this pass" yes \
  "$(grep -qE 'STEP B2 (start|runs|failed|done)' "$ERR" && echo yes || echo no)"
# The line above passes in this sandbox through the pre-existing PAID_LANE_FAILED branch
# (no docker, so the builder cannot start), so it does not by itself prove the gate
# changed. This does: the gate is asked about the real, unresolved live queue and must
# refuse to name a skip reason. rc 1 = "no policy skip"; rc 0 = "skipped, and here is why".
LIVE_QUEUE=$(ls -t "$LIVE"/evidence/gig-pass-*/delivery-queue.json 2>/dev/null | head -1)
if [ -n "$LIVE_QUEUE" ]; then
  python3 "$SKILL_DIR/scripts/b2_queue_gate.py" "$LIVE_QUEUE" >"$TMP/b2gate.out" 2>&1
  check "★ the gate names no skip reason for the real unresolved paid queue ★" 1 "$?"
  check "and prints nothing" "" "$(cat "$TMP/b2gate.out")"
fi

PLAN=$(ls -t "$SANDBOX"/gig/evidence/gig-pass-*/paid-admission.json 2>/dev/null | head -1)
check "the plan is kept as pass evidence" yes "$([ -n "$PLAN" ] && echo yes || echo no)"
if [ -n "$PLAN" ]; then
  check "the plan admits 91000002" '["91000002"]' \
    "$(python3 -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1]))["admitted"]))' "$PLAN")"
  check "the plan skips 91000001" yes \
    "$(python3 -c 'import json,sys; print("yes" if "91000001" in json.load(open(sys.argv[1]))["skipped"] else "no")' "$PLAN")"
fi

check "★ the skip is durable in the skipped order own ledger ★" yes \
  "$(grep -qF '"event":"queue_skipped"' "$SANDBOX/gig/projects/91000001/events.jsonl" && echo yes || echo no)"
check "one pass records exactly one skip for it" 1 \
  "$(grep -cF '"event":"queue_skipped"' "$SANDBOX/gig/projects/91000001/events.jsonl")"
TRAJ=$(ls -t "$SANDBOX"/gig/evidence/gig-pass-*/trajectory.jsonl 2>/dev/null | head -1)
check "the skip reaches the EV1 trajectory" yes \
  "$([ -n "$TRAJ" ] && grep -qF '"resource_key":"project:91000001","action":"read","result":"skipped"' "$TRAJ" && echo yes || echo no)"

echo
echo "=== nothing left this machine ==="
count_in() { grep -cF "$2" "$1" 2>/dev/null | head -1; }
check "no model call was spent on the paid lane" 0 "$(grep -c 'PAID' "$CALL_LOG" | head -1)"
check "no buyer message was composed for sending" no \
  "$([ -s "$SANDBOX/gig/projects/91000001/delivery/paid-answer.json" ] && echo yes || echo no)"
check "the live project ledger was not written" 0 \
  "$(count_in "$LIVE/projects/91000001/events.jsonl" '"event":"queue_skipped"')"
check "the live escalation ledger was not created" no \
  "$([ -e "$LIVE/paid-lane-escalations.jsonl" ] && echo yes || echo no)"
check "nothing reached the telegram outbox" no \
  "$([ -s "$SANDBOX/gig/telegram-outbox.sqlite3" ] && sqlite3 "$SANDBOX/gig/telegram-outbox.sqlite3" \
      "select count(*) from sqlite_master where type='table'" 2>/dev/null | grep -qv '^0$' && \
      [ "$(sqlite3 "$SANDBOX/gig/telegram-outbox.sqlite3" 'select count(*) from messages' 2>/dev/null || echo 0)" != "0" ] \
      && echo yes || echo no)"

echo
echo "=== one customer, one order in flight ==="
python3 - "$SANDBOX/snapshot.json" "$TMP/two-orders-one-buyer.json" <<'PY'
import copy, json, sys
snapshot = json.load(open(sys.argv[1], encoding="utf-8"))
orders = [o for o in snapshot.get("orders", []) if str(o.get("request_id")) == "91000002"]
if orders:
    twin = copy.deepcopy(orders[0])
    twin["request_id"] = "91000103"
    twin["talkroom_id"] = "90000003"
    twin["contract_id"] = "offer:92000014"
    snapshot["orders"] = orders + [twin]
json.dump(snapshot, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)
PY
cp "$TMP/two-orders-one-buyer.json" "$SANDBOX/snapshot.json"
MAX_ORDERS=3 rc2=$(MAX_ORDERS=3 run_pass "$TMP/pass2")
PLAN2=$(ls -t "$SANDBOX"/gig/evidence/gig-pass-*/paid-admission.json 2>/dev/null | head -1)
check "★ two orders from one buyer do not both go in flight ★" 1 \
  "$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["admitted"]))' "$PLAN2" 2>/dev/null || echo unreadable)"
check "and the second one says why it waited" customer_slot_taken \
  "$(python3 -c '
import json,sys
plan=json.load(open(sys.argv[1]))
print(next((r["reason"] for r in plan["decisions"] if r["decision"]=="skip"), "none"))' "$PLAN2" 2>/dev/null || echo unreadable)"

echo
echo "=== a permanently skipped order escalates ==="
python3 - "$SANDBOX/gig/projects/91000001" <<'PY'
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
state = json.loads((root / "state.json").read_text(encoding="utf-8"))
state.pop("last_skip_pass_id", None)
(root / "state.json").write_text(json.dumps(state) + "\n", encoding="utf-8")
row = json.dumps({"ts": 1.0, "request_id": "91000001", "adapter": "coconala",
                  "event": "queue_skipped", "state": state})
with (root / "events.jsonl").open("a", encoding="utf-8") as handle:
    # 11 prior skips already on the ledger; this pass's skip is the twelfth.
    for _ in range(10):
        handle.write(row + "\n")
PY
cp "$TMP/pass1.out" /dev/null 2>/dev/null
python3 - "$SANDBOX/snapshot.json" "$TMP/original.json" <<'PY'
import json, shutil, sys
shutil.copyfile(sys.argv[1], sys.argv[2])
PY
cp "$SNAPSHOT_SRC" "$SANDBOX/snapshot.json"
python3 - "$SANDBOX/snapshot.json" <<'PY'
import json, sys
path = sys.argv[1]
snapshot = json.load(open(path, encoding="utf-8"))
snapshot["inquiries"] = []
json.dump(snapshot, open(path, "w", encoding="utf-8"), ensure_ascii=False)
PY
rc3=$(run_pass "$TMP/pass3")
check "★ the escalation fires ★" yes \
  "$(has "$TMP/pass3.err" 'ESCALATION id=91000001')"
check "and is durable where a report can read it" yes \
  "$([ -s "$SANDBOX/gig/paid-lane-escalations.jsonl" ] && echo yes || echo no)"
check "and rides the existing failure channel" yes \
  "$(grep -qF 'paid_order_stuck_escalated' "$SANDBOX/gig/pass-failures.jsonl" 2>/dev/null && echo yes || echo no)"

echo
if [ "$fails" -gt 0 ]; then
  echo "$fails failed"
  echo "--- pass1 stderr tail ---"; tail -40 "$TMP/pass1.err"
  exit 1
fi
echo "PASS: a jammed order is skipped over, the next customer is worked, and the apply lane runs"
