#!/usr/bin/env bash
# X18 (2026-07-27): one waking drives every DUE lane, and one lane's failure does not
# take the others with it.
#
# The bug this closes is not a crash, it is a shape: "applied today, never replied".
# GIG_MODEL_CALL_LIMIT=1 meant one pass drove one lane, so apply and reply could not both
# happen in the same waking; EDF then rotated them across passes and the buyer waited.
# The limit came from every worker sharing one browser tab, and measured occupancy was
# 1.3% of the period -- the serialisation protected nothing.
#
# The isolation half matters just as much. With `step ... || exit 1`, the FIRST lane to
# fail aborted the pass, so widening the pass would have been worthless: one broken lane
# would keep swallowing every later lane's turn, which is the old starvation wearing a
# new hat. Here the runner fails on every call, which is the worst case, and every
# selected lane must still be attempted and individually recorded.
set -uo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d /tmp/gig-pass-multi-lane.XXXXXX)
trap 'rm -rf "$TMP"' EXIT
HOME_DIR="$TMP/home"
GIG_DIR="$HOME_DIR/life-manager/skills/earn/gig"
mkdir -p "$GIG_DIR/scripts" "$GIG_DIR/schemas" "$GIG_DIR/config/connectors" \
  "$HOME_DIR/life-manager/runtime/agent-runner" \
  "$HOME_DIR/life-manager/skills/browser/scripts" "$HOME_DIR/gig"

cp "$SKILL_DIR/gig_pass.sh" "$GIG_DIR/gig_pass.sh"
cp "$SKILL_DIR/scripts/gig_paths.sh" "$GIG_DIR/scripts/gig_paths.sh"
cp "$SKILL_DIR/passprep.py" "$GIG_DIR/passprep.py"
cp "$SKILL_DIR/strategy.default.json" "$GIG_DIR/strategy.default.json"
for script in delivery_queue delivery_cadence delivery_identity reply_queue \
              connector_outbox b1_conversation_gate b0_objective b0_result_gate b2_queue_gate \
              b2_result_gate b2_wall_clock lane_health lane_action_runtime lane_productivity; do
  cp "$SKILL_DIR/scripts/$script.py" "$GIG_DIR/scripts/$script.py"
done
cp "$SKILL_DIR/config/connectors/coconala.json" "$GIG_DIR/config/connectors/coconala.json"
cp "$SKILL_DIR/schemas/gig_step_result.schema.json" "$GIG_DIR/schemas/gig_step_result.schema.json"
cp "$SKILL_DIR/schemas/gig_b0_result.schema.json" "$GIG_DIR/schemas/gig_b0_result.schema.json"
# B2's production preflight verifies these two parent-owned helper paths before it spends
# a model call. This test replaces the runner and never invokes browser tooling, so file
# presence is the complete fixture needed to reach and record the B2 attempt.
: > "$GIG_DIR/scripts/cdp_nav_snapshot.py"
cat > "$HOME_DIR/life-manager/skills/browser/scripts/cdp_context_lease.py" <<'PY'
#!/usr/bin/env python3
import os, sys
with open(os.environ["GIG_CONTEXT_LEASE_LOG"], "a", encoding="utf-8") as handle:
    handle.write(" ".join(sys.argv[1:]) + "\n")
PY
printf '%s\n' '{"captured_at":"2026-07-21T00:00:00Z","inbox":{"url":"https://coconala.com/message?fromMyPage=true","not_found":false},"orders":[],"quotes":[],"inquiries":[]}' > "$TMP/empty-snapshot.json"

# The runner records who called it and then fails, so "did this lane get its turn?" is
# answerable independently of whether the lane succeeded.
cat > "$HOME_DIR/life-manager/runtime/agent-runner/agent_runner.py" <<'PY'
#!/usr/bin/env python3
import os, sys
label = ""
argv = sys.argv[1:]
for i, arg in enumerate(argv):
    if arg == "--task-label" and i + 1 < len(argv):
        label = argv[i + 1]
with open(os.environ["GIG_STEP_CALL_LOG"], "a", encoding="utf-8") as handle:
    handle.write(label + "\n")
raise SystemExit(42)
PY
chmod +x "$HOME_DIR/life-manager/runtime/agent-runner/agent_runner.py" "$GIG_DIR/gig_pass.sh"

CALL_LOG="$TMP/step-calls.txt"
: > "$CALL_LOG"
CONTEXT_LEASE_LOG="$TMP/context-lease-calls.txt"
: > "$CONTEXT_LEASE_LOG"

# No GIG_LEGACY_MAINTENANCE_ENABLED: the pass must reach its own lane selector. ~/gig is
# brand new, so every lane is past its deadline -- the cold-start shape, and the one that
# used to spend a whole waking on a single lane.
HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/empty-snapshot.json" \
  GIG_LOCK_DIR="$TMP/lock.d" GIG_STEP_CALL_LOG="$CALL_LOG" \
  GIG_CONTEXT_LEASE_LOG="$CONTEXT_LEASE_LOG" \
  bash "$GIG_DIR/gig_pass.sh" >"$TMP/out" 2>"$TMP/err"
rc=$?

fails=0
check() {
  if [ "$2" = "$3" ]; then echo "PASS  $1"
  else echo "FAIL  $1  expected=$2 got=$3"; fails=$((fails+1)); fi
}
called() { grep -c "^gig-$1\$" "$CALL_LOG" 2>/dev/null; true; }
lane_outcome() { # lane outcome -> count of matching rows
  LANE="$1" OUTCOME="$2" python3 - "$HOME_DIR/gig/lane-events.jsonl" <<'PY'
import json, os, sys
n = 0
try:
    for line in open(sys.argv[1], encoding="utf-8"):
        row = json.loads(line)
        if row.get("lane") == os.environ["LANE"] and row.get("outcome") == os.environ["OUTCOME"]:
            n += 1
except OSError:
    pass
print(n)
PY
}

lanes_called=0
for label in B0 PROFILE B1 B2; do
  [ "$(called "$label")" -ge 1 ] && lanes_called=$((lanes_called+1))
done
check "more than one lane gets a turn in a single pass" yes \
  "$([ "$lanes_called" -gt 1 ] && echo yes || echo "no(called=$lanes_called log=$(tr '\n' ',' < "$CALL_LOG"))")"

# The first selected lane fails. Under `|| exit 1` that was the end of the pass.
check "a lane failing does not cancel the lanes after it" 4 "$lanes_called"

# Each lane's own result, not one verdict for the pass. The EDF clock is per lane, so a
# lane whose attempt is never recorded stays maximally overdue and wins forever.
check "the apply lane records its own failure" 1 "$(lane_outcome apply failure)"
check "the reply lane records its own failure" 1 "$(lane_outcome reply failure)"
check "the list lane records its own failure" 1 "$(lane_outcome list failure)"
check "the profile lane records its own failure" 1 "$(lane_outcome profile failure)"

# Seven calls fit all five due lanes and still leave two continuations for a partial
# application pass. The independent token budget remains the runaway ceiling.
check "the raised budget no longer starves a due lane" 1 "$(called LEARN)"
check "parent releases B2 context after a failed agent" yes \
  "$(grep -Eq '^release gig-[0-9]+-B2$' "$CONTEXT_LEASE_LOG" && echo yes || echo no)"

# Isolation is not amnesty. Every lane failed, so the pass is still a failed pass: no
# success heartbeat, and the failure is on the ledger. Only the timing moved.
check "a pass whose lanes all failed still exits nonzero" yes \
  "$([ "$rc" -ne 0 ] && echo yes || echo "no(rc=$rc)")"
check "a failed pass writes no success heartbeat" yes \
  "$([ ! -e "$HOME_DIR/gig/.last-pass" ] && echo yes || echo no)"
check "the failure reaches the failure ledger" yes \
  "$([ -s "$HOME_DIR/gig/pass-failures.jsonl" ] && echo yes || echo no)"
check "the pass releases its lock" yes \
  "$([ ! -d "$TMP/lock.d" ] && echo yes || echo no)"

echo
if [ "$fails" -gt 0 ]; then
  echo "$fails failed"
  echo "--- stderr ---"; tail -30 "$TMP/err"
  exit 1
fi
echo "PASS: one pass drives every due lane and isolates their failures"
