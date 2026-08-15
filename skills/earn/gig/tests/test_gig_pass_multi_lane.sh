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
  "$HOME_DIR/life-manager/skills/agent-runner" \
  "$HOME_DIR/anicca/skills/browser/scripts" "$HOME_DIR/gig"

cp "$SKILL_DIR/gig_pass.sh" "$GIG_DIR/gig_pass.sh"
cp "$SKILL_DIR/passprep.py" "$GIG_DIR/passprep.py"
cp "$SKILL_DIR/strategy.default.json" "$GIG_DIR/strategy.default.json"
for script in delivery_queue delivery_cadence delivery_identity delivery_project project_ledger reply_queue \
              connector_outbox project_effect_fence application_parent application_effect_fence \
              application_snapshot application_planner market_snapshot buyer_voice proposal_feedback \
              b1_conversation_gate b0_objective b0_result_gate b2_queue_gate \
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
cat > "$HOME_DIR/anicca/skills/browser/scripts/cdp_context_lease.py" <<'PY'
#!/usr/bin/env python3
import json
import os, sys
with open(os.environ["GIG_CONTEXT_LEASE_LOG"], "a", encoding="utf-8") as handle:
    handle.write(" ".join(sys.argv[1:3]) + "\n")
if sys.argv[1:2] == ["acquire"]:
    print(json.dumps({"ok": True, "ws": "ws://127.0.0.1:1", "token": "0" * 32, "generation": 1}))
elif sys.argv[1:2] in (["release"], ["heartbeat"]):
    print(json.dumps({"ok": True}))
PY
printf '%s\n' '{"captured_at":"2026-07-21T00:00:00Z","inbox":{"url":"https://coconala.com/message?fromMyPage=true","not_found":false},"orders":[],"quotes":[],"inquiries":[]}' > "$TMP/empty-snapshot.json"
cat > "$GIG_DIR/scripts/paid_admission.py" <<'PY'
#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
call_log = os.environ.get("GIG_ADMISSION_CALL_LOG")
if call_log and "--queue" in args:
    Path(call_log).open("a", encoding="utf-8").write("paid_admission\n")
if call_log and "--record" in args:
    Path(call_log).open("a", encoding="utf-8").write("record\n")
queue = Path(args[args.index("--queue") + 1])
items = json.loads(queue.read_text(encoding="utf-8")).get("items", [])
def ident(item):
    return str(item.get("request_id") or item.get("talkroom_id") or item.get("contract_id") or "")
summary = {"admitted": [ident(items[0])] if items else [], "decisions": [], "escalated": [], "probe_every": 1}
Path(args[args.index("--output") + 1]).write_text(json.dumps(summary) + "\n", encoding="utf-8")
print(json.dumps(summary))
PY
chmod +x "$GIG_DIR/scripts/paid_admission.py"

# The runner records who called it and then fails, so "did this lane get its turn?" is
# answerable independently of whether the lane succeeded.
cat > "$HOME_DIR/life-manager/skills/agent-runner/agent_runner.py" <<'PY'
#!/usr/bin/env python3
import json
import os
import re
import sys
from pathlib import Path
label = ""
argv = sys.argv[1:]
for i, arg in enumerate(argv):
    if arg == "--task-label" and i + 1 < len(argv):
        label = argv[i + 1]
with open(os.environ["GIG_STEP_CALL_LOG"], "a", encoding="utf-8") as handle:
    handle.write(label + "\n")
workdir = ""
if "--workdir" in argv:
    workdir = argv[argv.index("--workdir") + 1]
metadata = os.environ.get("GIG_P0C_RUNNER_METADATA_LOG")
if metadata and label == "gig-PAID_WORK":
    Path(metadata).open("a", encoding="utf-8").write(
        json.dumps({"label": label, "workdir": workdir}, sort_keys=True) + "\n"
    )
if label == "gig-PAID_WORK_MODE" and os.environ.get("GIG_P0C_ACTIONABLE") == "1":
    prompt = ""
    if "--prompt-file" in argv:
        prompt = Path(argv[argv.index("--prompt-file") + 1]).read_text(encoding="utf-8")
    feedback = ""
    match = re.search(r"feedback SHA256[^$]*?([0-9a-f]{64})", prompt)
    if match:
        feedback = match.group(1)
    mode = Path(workdir) / "delivery" / "paid-work-mode.json"
    mode.parent.mkdir(parents=True, exist_ok=True)
    mode.write_text(json.dumps({
        "version": 1, "status": "ok", "feedback_sha256": feedback,
        "mode": "answer", "reason": "test-only no-effect runner",
    }) + "\n", encoding="utf-8")
    raise SystemExit(0)
raise SystemExit(42)
PY
chmod +x "$HOME_DIR/life-manager/skills/agent-runner/agent_runner.py" "$GIG_DIR/gig_pass.sh"

CALL_LOG="$TMP/step-calls.txt"
: > "$CALL_LOG"
LEGACY_ADMISSION_LOG="$TMP/legacy-admission.log"
: > "$LEGACY_ADMISSION_LOG"
CONTEXT_LEASE_LOG="$TMP/context-lease-calls.txt"
: > "$CONTEXT_LEASE_LOG"

# No GIG_LEGACY_MAINTENANCE_ENABLED: the pass must reach its own lane selector. ~/gig is
# brand new, so every lane is past its deadline -- the cold-start shape, and the one that
# used to spend a whole waking on a single lane.
HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/empty-snapshot.json" \
  GIG_LOCK_DIR="$TMP/lock.d" GIG_STEP_CALL_LOG="$CALL_LOG" \
  GIG_CONTEXT_LEASE_LOG="$CONTEXT_LEASE_LOG" GIG_ADMISSION_CALL_LOG="$LEGACY_ADMISSION_LOG" \
  bash "$GIG_DIR/gig_pass.sh" >"$TMP/out" 2>"$TMP/err"
rc=$?

fails=0
check() {
  if [ "$2" = "$3" ]; then echo "PASS  $1"
  else echo "FAIL  $1  expected=$2 got=$3"; fails=$((fails+1)); fi
}
called() { grep -c "^gig-$1\$" "$CALL_LOG" 2>/dev/null; true; }
admission_calls() { grep -c '^paid_admission$' "$1" 2>/dev/null || true; }
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
for label in PROFILE B1; do
  [ "$(called "$label")" -ge 1 ] && lanes_called=$((lanes_called+1))
done
# B2 is parent-owned in the current pass. It does not invoke agent_runner, so its
# real attempt is the fenced parent lease acquisition rather than a runner label.
[ "$(grep -Ec '^acquire gig-[0-9]+-B2-parent$' "$CONTEXT_LEASE_LOG" 2>/dev/null || true)" -ge 1 ] \
  && lanes_called=$((lanes_called+1))
check "more than one lane gets a turn in a single pass" yes \
  "$([ "$lanes_called" -gt 1 ] && echo yes || echo "no(called=$lanes_called log=$(tr '\n' ',' < "$CALL_LOG"))")"

# The first selected lane fails. Under `|| exit 1` that was the end of the pass.
check "a lane failing does not cancel the lanes after it" 3 "$lanes_called"

# Each lane's own result, not one verdict for the pass. The EDF clock is per lane, so a
# lane whose attempt is never recorded stays maximally overdue and wins forever.
check "the apply lane records its own failure" 1 "$(lane_outcome apply failure)"
check "the reply lane records its own failure" 1 "$(lane_outcome reply failure)"
check "the retired list lane records no failure" 0 "$(lane_outcome list failure)"
check "the profile lane records its own failure" 1 "$(lane_outcome profile failure)"

# Seven calls fit all five due lanes and still leave two continuations for a partial
# application pass. The independent token budget remains the runaway ceiling.
check "the raised budget no longer starves a due lane" 1 "$(called LEARN)"
check "parent releases B2 context after a failed agent" yes \
  "$(grep -Eq '^release gig-[0-9]+-B2(-parent)?$' "$CONTEXT_LEASE_LOG" && echo yes || echo no)"

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
check "legacy pass records paid admission once" 1 "$(admission_calls "$LEGACY_ADMISSION_LOG")"

# The canary contract covers every revenue lane, not only the two legacy Hermes lanes.
# Attachment-probe mode stops after the shared snapshot boundary, so this validates the
# process-boundary allowlist without requiring a browser or model fixture.
for forced_step in B1 PAID_WORK; do
  set +e
  canary_truth="$TMP/canary-$forced_step-truth.json"
  HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_P0C_TEST_FIXTURES=1 GIG_TEST_CDP_ALIVE=1 \
    GIG_QUEUE_FIXTURE="$TMP/empty-snapshot.json" \
    GIG_LOCK_DIR="$TMP/canary-$forced_step-lock.d" GIG_EVIDENCE_DIR="$TMP/canary-$forced_step-evidence" \
    GIG_HERMES_TRUTH_PATH="$canary_truth" \
    GIG_ATTACHMENT_PROBE_ONLY=1 GIG_HERMES_FORCED_STEP="$forced_step" \
    GIG_HERMES_OWNED_STEPS="$forced_step" timeout 20 bash "$GIG_DIR/gig_pass.sh" \
    >"$TMP/canary-$forced_step-out" 2>"$TMP/canary-$forced_step-err"
  canary_rc=$?
  set -e
  check "canary accepts forced $forced_step" 0 "$canary_rc"
  truth_structured=no
  if [ -s "$canary_truth" ]; then
    truth_structured=$(python3 - "$canary_truth" <<'PY'
import json, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))
print("yes" if isinstance(value, dict) and "status" in value and "coverage_complete" in value else "no")
PY
    ) || truth_structured=no
  fi
  check "forced $forced_step writes structured truth" yes "$truth_structured"
  truth_status=$(python3 - "$canary_truth" <<'PY'
import json, sys
try:
    print(json.load(open(sys.argv[1], encoding="utf-8")).get("status", "missing"))
except (OSError, ValueError):
    print("missing")
PY
  )
  check "forced $forced_step marks missing authoritative source blocked" blocked "$truth_status"
done

# A forced B1 wake owns only the reply lane. Its runner is allowed to fail in this
# fixture; the call-label log still proves which lane crossed the model boundary.
FORCED_B1_CALL_LOG="$TMP/forced-b1-calls.log"
: > "$FORCED_B1_CALL_LOG"
set +e
HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/empty-snapshot.json" \
  GIG_LOCK_DIR="$TMP/forced-b1-lock.d" GIG_EVIDENCE_DIR="$TMP/forced-b1-evidence" \
  GIG_STEP_CALL_LOG="$FORCED_B1_CALL_LOG" GIG_CONTEXT_LEASE_LOG="$CONTEXT_LEASE_LOG" \
  GIG_TEST_CDP_ALIVE=1 GIG_HERMES_FORCED_STEP=B1 GIG_HERMES_OWNED_STEPS=B1 \
  timeout 20 bash "$GIG_DIR/gig_pass.sh" >"$TMP/forced-b1-out" 2>"$TMP/forced-b1-err"
forced_b1_rc=$?
set -e
check "forced B1 reaches its runner" 1 \
  "$(grep -c '^gig-B1$' "$FORCED_B1_CALL_LOG" 2>/dev/null || true)"
check "forced B1 bypasses B0/B2/paid runners" 0 \
  "$(grep -Ec '^(gig-B0|gig-B2|gig-PAID_WORK|gig-paid-queue-assess)$' "$FORCED_B1_CALL_LOG" 2>/dev/null || true)"

# A non-forced Hermes-owned pass can select only B1 while B2 remains owned by Hermes.
# The parent boundary must honor that selection before its special B2 branch acquires a
# lease; the old ordering entered run_parent_b2 first and called the parent anyway.
NON_FORCED_PARENT_LOG="$TMP/non-forced-b2-parent.log"
: > "$NON_FORCED_PARENT_LOG"
cat > "$GIG_DIR/scripts/lane_health.py" <<'PY'
#!/usr/bin/env python3
import json
import sys
if sys.argv[1:2] == ["select"]:
    print(json.dumps({"due": [{"step": "B1", "lane": "reply"}]}))
PY
cat > "$GIG_DIR/scripts/application_parent.py" <<'PY'
#!/usr/bin/env python3
import os
from pathlib import Path
Path(os.environ["GIG_PARENT_RUN_LOG"]).open("a", encoding="utf-8").write("called\n")
raise SystemExit(71)
PY
chmod +x "$GIG_DIR/scripts/lane_health.py" "$GIG_DIR/scripts/application_parent.py"
set +e
HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/empty-snapshot.json" \
  GIG_LOCK_DIR="$TMP/non-forced-lock.d" GIG_EVIDENCE_DIR="$TMP/non-forced-evidence" \
  GIG_STEP_CALL_LOG="$CALL_LOG" GIG_CONTEXT_LEASE_LOG="$CONTEXT_LEASE_LOG" \
  GIG_PARENT_RUN_LOG="$NON_FORCED_PARENT_LOG" GIG_HERMES_OWNED_STEPS="B2" \
  timeout 20 bash "$GIG_DIR/gig_pass.sh" >"$TMP/non-forced-out" 2>"$TMP/non-forced-err"
non_forced_rc=$?
set -e
check "selected B1 never enters the B2 parent boundary" 0 \
  "$(wc -c < "$NON_FORCED_PARENT_LOG" | tr -d ' ')"

# A forced B2 wake must reach the parent boundary even when a fixture queue policy
# would otherwise close the apply lane for the nonempty paid queue. The parent stub
# exits before browser/model work; the observable contract is the B2 boundary log and
# the absence of a queue-gate call.
cat > "$TMP/paid-snapshot.json" <<'JSON'
{
  "source": "authenticated_coconala_hidden_default_context_dom",
  "read_only": true,
  "collector_mode": "orders-only",
  "observed_sources": ["orders"],
  "open_orders_list_observed": true,
  "captured_at": "2026-07-21T00:00:00Z",
  "inbox": {"url": "https://coconala.com/message?fromMyPage=true", "not_found": false, "observed": true},
  "orders": [{
    "contract_id": "talkroom:4201", "talkroom_id": "4201", "marketplace_url": "https://coconala.com/talkrooms/4201", "buyer": "fixture",
    "title": "forced B2 queue item", "status": "paid", "price_jpy": 17000,
    "price_source": "structured_order_label",
    "delivery_date": "2026-08-01", "talkroom_state": "取引中",
    "buyer_feedback_pending_artifact": true, "buyer_visible_artifact_observed": false,
    "formal_delivery_observed": false,
    "talkroom_evidence_file": "/tmp/gig-pass-multi-lane-placeholder-talkroom.json",
    "talkroom_observed_at": "2026-07-21T00:00:00Z"
  }],
  "quotes": [], "inquiries": [{
    "talkroom_id": "5101", "talkroom_url": "https://coconala.com/talkrooms/5101",
    "reply_required": true, "last_message_side": "buyer",
    "buyer_sent_at": "2026-07-21T00:00:00Z", "message_id": "fixture-reply-1"
  }],
  "source_receipt": {
    "source": "orders",
    "requested_route": "https://coconala.com/mypage/received_orders/open",
    "final_route": "https://coconala.com/mypage/received_orders/open",
    "login_redirect": false,
    "cards_count": 1,
    "empty_state_present": false,
    "coverage_complete": true
  }
}
JSON
printf '%s\n' '{"url":"https://coconala.com/talkrooms/4201","not_found":false,"observed":true}' \
  > "$TMP/gig-pass-multi-lane-placeholder-talkroom.json"
python3 - "$TMP/paid-snapshot.json" "$TMP/gig-pass-multi-lane-placeholder-talkroom.json" <<'PY'
import json
import sys
snapshot_path, evidence_path = sys.argv[1:]
snapshot = json.load(open(snapshot_path, encoding="utf-8"))
for order in snapshot["orders"]:
    order["talkroom_evidence_file"] = evidence_path
json.dump(snapshot, open(snapshot_path, "w", encoding="utf-8"))
PY

cat > "$TMP/targeted-snapshot.json" <<'JSON'
{
  "source": "authenticated_coconala_hidden_default_context_dom",
  "read_only": true,
  "collector_mode": "selected-talkroom-only",
  "observed_sources": ["selected_talkroom"],
  "captured_at": "2026-07-21T00:00:01Z",
  "talkroom_id": "4201",
  "orders": [{
    "contract_id": "talkroom:4201", "talkroom_id": "4201", "marketplace_url": "https://coconala.com/talkrooms/4201",
    "buyer": "fixture", "title": "forced paid target", "status": "paid", "price_jpy": 17000,
    "price_source": "structured_order_label", "talkroom_state": "取引中",
    "buyer_feedback_pending_artifact": true, "buyer_visible_artifact_observed": false,
    "selection_stage": "targeted", "targeted_readback_required": false
  }],
  "quotes": [],
  "source_receipt": {
    "source": "selected_talkroom",
    "requested_route": "https://coconala.com/talkrooms/4201",
    "final_route": "https://coconala.com/talkrooms/4201",
    "login_redirect": false,
    "coverage_complete": true
  }
}
JSON

# PAID_WORK is the only owner allowed to cross the paid builder boundary. The fixture
# runner exits before any browser action; its label is enough to prove admission, while
# every lower revenue lane must remain untouched.
FORCED_PAID_CALL_LOG="$TMP/forced-paid-calls.log"
: > "$FORCED_PAID_CALL_LOG"
FORCED_PAID_ADMISSION_LOG="$TMP/forced-paid-admission.log"
: > "$FORCED_PAID_ADMISSION_LOG"
set +e
HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_P0C_TEST_FIXTURES=1 \
  GIG_QUEUE_FIXTURE="$TMP/paid-snapshot.json" \
  GIG_FORCED_PAID_TARGETED_FIXTURE="$TMP/targeted-snapshot.json" \
  GIG_LOCK_DIR="$TMP/forced-paid-lock.d" GIG_EVIDENCE_DIR="$TMP/forced-paid-evidence" \
  GIG_STEP_CALL_LOG="$FORCED_PAID_CALL_LOG" GIG_CONTEXT_LEASE_LOG="$CONTEXT_LEASE_LOG" \
  GIG_ADMISSION_CALL_LOG="$FORCED_PAID_ADMISSION_LOG" \
  GIG_TEST_CDP_ALIVE=1 GIG_HERMES_FORCED_STEP=PAID_WORK GIG_HERMES_OWNED_STEPS=PAID_WORK \
  timeout 20 bash "$GIG_DIR/gig_pass.sh" >"$TMP/forced-paid-out" 2>"$TMP/forced-paid-err"
forced_paid_rc=$?
set -e
check "forced PAID_WORK selects its owned lane" yes \
  "$(grep -q 'Hermes forced lane selected: PAID_WORK (lane=fulfill)' "$TMP/forced-paid-err" && echo yes || echo no)"
check "forced PAID_WORK bypasses reply/B0/B1/B2 runners" 0 \
  "$(grep -Ec '^(gig-B0|gig-B1|gig-B2)$' "$FORCED_PAID_CALL_LOG" 2>/dev/null || true)"
check "forced PAID_WORK records paid admission once" 1 "$(admission_calls "$FORCED_PAID_ADMISSION_LOG")"

# B0 is retired from the shared pass. A forced rollback attempt must fail before
# queue, runner, browser, or paid admission work.
FORCED_B0_CALL_LOG="$TMP/forced-b0-calls.log"
: > "$FORCED_B0_CALL_LOG"
FORCED_B0_ADMISSION_LOG="$TMP/forced-b0-admission.log"
: > "$FORCED_B0_ADMISSION_LOG"
set +e
HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/paid-snapshot.json" \
  GIG_LOCK_DIR="$TMP/forced-b0-lock.d" GIG_EVIDENCE_DIR="$TMP/forced-b0-evidence" \
  GIG_STEP_CALL_LOG="$FORCED_B0_CALL_LOG" GIG_CONTEXT_LEASE_LOG="$CONTEXT_LEASE_LOG" \
  GIG_ADMISSION_CALL_LOG="$FORCED_B0_ADMISSION_LOG" \
  GIG_TEST_CDP_ALIVE=1 GIG_HERMES_FORCED_STEP=B0 GIG_HERMES_OWNED_STEPS=B0 \
  timeout 20 bash "$GIG_DIR/gig_pass.sh" >"$TMP/forced-b0-out" 2>"$TMP/forced-b0-err"
forced_b0_rc=$?
set -e
check "forced B0 is rejected at the process boundary" 64 "$forced_b0_rc"
check "forced B0 never reaches its runner" 0 \
  "$(grep -c '^gig-B0$' "$FORCED_B0_CALL_LOG" 2>/dev/null || true)"
check "forced B0 never reaches paid worker" 0 \
  "$(grep -Ec '^(gig-PAID_WORK|gig-paid-queue-assess)$' "$FORCED_B0_CALL_LOG" 2>/dev/null || true)"
check "forced B0 does not record paid admission" 0 "$(admission_calls "$FORCED_B0_ADMISSION_LOG")"

cat > "$GIG_DIR/scripts/b2_queue_gate.py" <<'PY'
#!/usr/bin/env python3
import os
from pathlib import Path
Path(os.environ["GIG_B2_GATE_LOG"]).open("a", encoding="utf-8").write("called\n")
print("fixture_paid_queue_gate")
raise SystemExit(0)
PY
chmod +x "$GIG_DIR/scripts/b2_queue_gate.py"
cat > "$GIG_DIR/scripts/application_parent.py" <<'PY'
#!/usr/bin/env python3
import os
from pathlib import Path
Path(os.environ["GIG_PARENT_RUN_LOG"]).open("a", encoding="utf-8").write("called\n")
raise SystemExit(71)
PY
chmod +x "$GIG_DIR/scripts/application_parent.py"
# The production queue builder sees this inquiry; only the reply lane is stubbed so its
# call is observable without touching a browser.
cat > "$GIG_DIR/scripts/reply_lane.py" <<'PY'
#!/usr/bin/env python3
import os
import sys
from pathlib import Path

Path(os.environ["GIG_REPLY_LANE_CALL_LOG"]).open("a", encoding="utf-8").write("called\n")
output = Path(sys.argv[sys.argv.index("--output") + 1])
output.write_text('{"status":"ok","model_calls":1,"events":[]}\n', encoding="utf-8")
PY
chmod +x "$GIG_DIR/scripts/reply_lane.py"
cat > "$GIG_DIR/scripts/paid_lane_observe.py" <<'PY'
#!/usr/bin/env python3
import json
print(json.dumps({"ok": True, "snapshot_missing": False, "orders_seen": 0,
                  "rooms_enumerated": 0, "dropped": 0, "collector_suspect": False,
                  "errors": [], "open_liabilities": 0, "oldest_age_passes": 0,
                  "owed_jpy": 0}))
PY
chmod +x "$GIG_DIR/scripts/paid_lane_observe.py"

# A forced B1 pass still needs the paid-talkroom fence, but must not claim a paid
# candidate. Point post-reply recollection at the same fixture so both load sites are
# exercised by this real pass.
FORCED_B1_ADMISSION_LOG="$TMP/forced-b1-admission.log"
: > "$FORCED_B1_ADMISSION_LOG"
set +e
HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/paid-snapshot.json" \
  GIG_POST_REPLY_QUEUE_FIXTURE="$TMP/paid-snapshot.json" \
  GIG_LOCK_DIR="$TMP/forced-b1-admission-lock.d" GIG_EVIDENCE_DIR="$TMP/forced-b1-admission-evidence" \
  GIG_STEP_CALL_LOG="$TMP/forced-b1-admission-calls.log" GIG_CONTEXT_LEASE_LOG="$CONTEXT_LEASE_LOG" \
  GIG_ADMISSION_CALL_LOG="$FORCED_B1_ADMISSION_LOG" GIG_REPLY_LANE_CALL_LOG="$TMP/forced-b1-admission-reply.log" \
  GIG_TEST_CDP_ALIVE=1 GIG_HERMES_FORCED_STEP=B1 GIG_HERMES_OWNED_STEPS=B1 \
  timeout 20 bash "$GIG_DIR/gig_pass.sh" >"$TMP/forced-b1-admission-out" 2>"$TMP/forced-b1-admission-err"
forced_b1_admission_rc=$?
set -e
check "forced B1 does not record paid admission" 0 "$(admission_calls "$FORCED_B1_ADMISSION_LOG")"

FORCED_GATE_LOG="$TMP/forced-b2-gate.log"
FORCED_PARENT_LOG="$TMP/forced-b2-parent.log"
FORCED_CALL_LOG="$TMP/forced-b2-calls.log"
FORCED_REPLY_LOG="$TMP/forced-b2-reply.log"
: > "$FORCED_GATE_LOG"
: > "$FORCED_PARENT_LOG"
: > "$FORCED_CALL_LOG"
: > "$FORCED_REPLY_LOG"
FORCED_B2_ADMISSION_LOG="$TMP/forced-b2-admission.log"
: > "$FORCED_B2_ADMISSION_LOG"

# Non-B2 forced wakes must not even evaluate the B2 policy gate. Run the real pass
# harness for both owners and inspect the gate stub's call log, rather than extracting
# the conditional into a unit-shaped shell fragment.
for forced_non_b2 in B1 PAID_WORK; do
  forced_non_b2_gate_log="$TMP/forced-$forced_non_b2-gate.log"
  : > "$forced_non_b2_gate_log"
  : > "$TMP/forced-$forced_non_b2-calls.log"
  : > "$TMP/forced-$forced_non_b2-reply.log"
  set +e
  HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/empty-snapshot.json" \
    GIG_LOCK_DIR="$TMP/forced-$forced_non_b2-lock.d" \
    GIG_EVIDENCE_DIR="$TMP/forced-$forced_non_b2-evidence" \
    GIG_STEP_CALL_LOG="$TMP/forced-$forced_non_b2-calls.log" \
    GIG_CONTEXT_LEASE_LOG="$CONTEXT_LEASE_LOG" GIG_B2_GATE_LOG="$forced_non_b2_gate_log" \
    GIG_PARENT_RUN_LOG="$TMP/forced-$forced_non_b2-parent.log" \
    GIG_REPLY_LANE_CALL_LOG="$TMP/forced-$forced_non_b2-reply.log" \
    GIG_TEST_CDP_ALIVE=1 GIG_HERMES_FORCED_STEP="$forced_non_b2" \
    GIG_HERMES_OWNED_STEPS="$forced_non_b2" timeout 20 bash "$GIG_DIR/gig_pass.sh" \
    >"$TMP/forced-$forced_non_b2-out" 2>"$TMP/forced-$forced_non_b2-err"
  forced_non_b2_rc=$?
  set -e
  check "forced $forced_non_b2 skips B2 policy gate" 0 \
    "$(wc -c < "$forced_non_b2_gate_log" | tr -d ' ')"
done

set +e
HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/paid-snapshot.json" \
  GIG_LOCK_DIR="$TMP/forced-b2-lock.d" GIG_EVIDENCE_DIR="$TMP/forced-b2-evidence" \
  GIG_STEP_CALL_LOG="$FORCED_CALL_LOG" GIG_CONTEXT_LEASE_LOG="$CONTEXT_LEASE_LOG" \
  GIG_B2_GATE_LOG="$FORCED_GATE_LOG" GIG_PARENT_RUN_LOG="$FORCED_PARENT_LOG" \
  GIG_REPLY_LANE_CALL_LOG="$FORCED_REPLY_LOG" \
  GIG_ADMISSION_CALL_LOG="$FORCED_B2_ADMISSION_LOG" \
  GIG_HERMES_FORCED_STEP=B2 GIG_HERMES_OWNED_STEPS=B2 \
  timeout 20 bash "$GIG_DIR/gig_pass.sh" >"$TMP/forced-b2-out" 2>"$TMP/forced-b2-err"
forced_b2_rc=$?
set -e
check "forced B2 reaches parent boundary" yes "$([ -s "$FORCED_PARENT_LOG" ] && echo yes || echo no)"
check "forced B2 bypasses paid queue gate" yes "$([ ! -s "$FORCED_GATE_LOG" ] && echo yes || echo no)"
check "forced B2 does not enter paid worker" yes \
  "$([ ! -s "$FORCED_CALL_LOG" ] && echo yes || echo no)"
check "forced B2 does not enter reply lane" 0 "$(wc -l < "$FORCED_REPLY_LOG" | tr -d ' ')"
check "forced B2 emits its boundary start" yes \
  "$(grep -q 'STEP B2 start' "$TMP/forced-b2-err" && echo yes || echo no)"
check "forced B2 does not record paid admission" 0 "$(admission_calls "$FORCED_B2_ADMISSION_LOG")"

# Concurrent GC may remove a step directory between the parent failure and its
# diagnostic redirect.  Every redirect must recreate that directory immediately
# before writing, including the retry-failure path.
check "parent failure redirects recreate their step directory" yes "$(python3 - "$GIG_DIR/gig_pass.sh" <<'PY'
import sys
lines = open(sys.argv[1], encoding="utf-8").read().splitlines()
redirects = [i for i, line in enumerate(lines)
             if 'tail -n 1' in line and 'parent-error.json' in line]
ok = bool(redirects) and all(
    any('mkdir -p "$step_evidence"' in lines[j] for j in range(max(0, i - 5), i))
    for i in redirects
)
print("yes" if ok else "no")
PY
)"

# P3-b: Hermes owns the deterministic preparation boundary as well as the external
# runner.  Replace the prep scripts with call-log stubs and run the real pass for every
# forced lane.  This intentionally comes after the legacy/allowlist checks above so the
# same fixture still proves the old (unforced) all-prep path before the lane-specific
# isolation assertions.
cat > "$GIG_DIR/scripts/prep_call_stub.py" <<'PY'
#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

name = Path(__file__).stem
args = sys.argv[1:]
log = os.environ.get("GIG_PREP_CALL_LOG")

def record(label):
    if log:
        Path(log).open("a", encoding="utf-8").write(label + "\n")

def output_path():
    if "--output" in args:
        return Path(args[args.index("--output") + 1])
    return None

def record_decisions(result, **kwargs):
    record("paid_admission_record")
    return {"recorded": True}

if name == "paid_lane_observe":
    record("paid_observe")
    print(json.dumps({"ok": True, "snapshot_missing": False, "orders_seen": 0,
                      "rooms_enumerated": 0, "dropped": 0, "collector_suspect": False,
                      "errors": [], "open_liabilities": 0, "oldest_age_passes": 0,
                      "owed_jpy": 0}))
elif name == "paid_admission" and os.environ.get("GIG_PAID_ADMISSION_LIBRARY") != "1":
    record("paid_admission")
    admission_mode = os.environ.get("GIG_ADMISSION_RESULT", "valid")
    if admission_mode == "failure":
        raise SystemExit(23)
    queue = Path(args[args.index("--queue") + 1])
    items = json.loads(queue.read_text(encoding="utf-8")).get("items", [])
    identity = str(items[0].get("request_id") or items[0].get("talkroom_id") or "") if items else ""
    admitted = [identity] if identity else []
    if admission_mode == "multiple":
        admitted = [identity, "unknown-second"]
    elif admission_mode == "unknown":
        admitted = ["unknown-admitted-id"]
    elif admission_mode in {"empty", "all-skipped"}:
        admitted = []
    value = {"admitted": admitted, "decisions": [],
             "escalated": [], "probe_every": 1}
    target = output_path()
    if target:
        target.write_text(json.dumps(value) + "\n", encoding="utf-8")
    print(json.dumps(value))
elif name == "project_effect_fence":
    if args[:1] == ["build-paid"]:
        record("project_fence")
        target = output_path()
        if target:
            target.write_text('{"version":1,"projects":{}}\n', encoding="utf-8")
elif name == "reply_queue":
    if args[:1] == ["build"]:
        record("reply_build")
        target = output_path()
        if target:
            target.write_text('{"version":1,"items":[]}\n', encoding="utf-8")
    elif args[:1] == ["enqueue"]:
        record("reply_enqueue")
        print('{"enqueued":0,"revived":0,"dead_lettered":0}')
elif name == "b1_conversation_gate":
    if args[:1] == ["build"]:
        record("b1_context")
        target = output_path()
        if target:
            target.write_text('{"version":1,"items":[]}\n', encoding="utf-8")
elif name == "passprep":
    record("passprep")
    print(json.dumps({"target_apply_per_pass": 0, "target_retainer_applications": 0,
                      "required_search_source_ids": []}))
elif name == "b2_result_gate":
    if args[:1] == ["build"]:
        record("b2_context")
        target = output_path()
        if target:
            target.write_text('{"version":1,"target_apply_per_pass":0}\n', encoding="utf-8")
elif name == "b0_objective":
    record("b0_decision")
    print(json.dumps({"action": "inspect_storefront",
                      "objective": "Inspect the storefront."}))
elif name == "b0_result_gate":
    if args[:1] == ["build"]:
        record("b0_context")
        target = output_path()
        if target:
            target.write_text('{"version":1,"objective":"Inspect the storefront."}\n', encoding="utf-8")
PY
chmod +x "$GIG_DIR/scripts/prep_call_stub.py"
for prep_script in paid_lane_observe paid_admission project_effect_fence reply_queue \
                   b1_conversation_gate b2_result_gate b0_result_gate; do
  cp "$GIG_DIR/scripts/prep_call_stub.py" "$GIG_DIR/scripts/$prep_script.py"
done
cp "$GIG_DIR/scripts/prep_call_stub.py" "$GIG_DIR/passprep.py"
cp "$GIG_DIR/scripts/prep_call_stub.py" "$GIG_DIR/scripts/b0_objective.py"

# The forced B2 boundary must stop before browser/model execution, and every other
# forced lane's runner fails fast; this keeps the call-log contract deterministic.
cat > "$GIG_DIR/scripts/application_parent.py" <<'PY'
#!/usr/bin/env python3
import os
from pathlib import Path
target = os.environ.get("GIG_PARENT_RUN_LOG")
if target:
    Path(target).open("a", encoding="utf-8").write("called\n")
raise SystemExit(71)
PY
chmod +x "$GIG_DIR/scripts/application_parent.py"

prep_count() { grep -c "^$1$" "$2" 2>/dev/null || true; }
run_forced_prep_pass() {
  local forced="$1" log_path="$TMP/prep-$1.log"
  : > "$log_path"
  set +e
  HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_P0C_TEST_FIXTURES=1 \
    GIG_QUEUE_FIXTURE="$TMP/paid-snapshot.json" \
    GIG_FORCED_PAID_TARGETED_FIXTURE="$TMP/targeted-snapshot.json" \
    GIG_LOCK_DIR="$TMP/prep-$forced-lock.d" GIG_EVIDENCE_DIR="$TMP/prep-$forced-evidence" \
    GIG_STEP_CALL_LOG="$TMP/prep-$forced-runner.log" GIG_CONTEXT_LEASE_LOG="$CONTEXT_LEASE_LOG" \
    GIG_PARENT_RUN_LOG="$TMP/prep-$forced-parent.log" GIG_PREP_CALL_LOG="$log_path" \
    GIG_TEST_CDP_ALIVE=1 GIG_HERMES_FORCED_STEP="$forced" \
    GIG_HERMES_OWNED_STEPS="$forced" timeout 20 bash "$GIG_DIR/gig_pass.sh" \
    >"$TMP/prep-$forced-out" 2>"$TMP/prep-$forced-err"
  PREP_PASS_RC=$?
  set -e
}

run_forced_prep_pass PAID_WORK
check "forced PAID_WORK observes paid queue once" 1 "$(prep_count paid_observe "$TMP/prep-PAID_WORK.log")"
check "forced PAID_WORK admits paid queue once" 1 "$(prep_count paid_admission "$TMP/prep-PAID_WORK.log")"
for forbidden in project_fence reply_build reply_enqueue b1_context passprep b2_context b0_decision b0_context; do
  check "forced PAID_WORK skips $forbidden prep" 0 "$(prep_count "$forbidden" "$TMP/prep-PAID_WORK.log")"
done

run_forced_prep_pass B1
check "forced B1 builds project fence once" 1 "$(prep_count project_fence "$TMP/prep-B1.log")"
check "forced B1 builds reply queue once" 1 "$(prep_count reply_build "$TMP/prep-B1.log")"
check "forced B1 enqueues reply queue once" 1 "$(prep_count reply_enqueue "$TMP/prep-B1.log")"
check "forced B1 builds B1 context once" 1 "$(prep_count b1_context "$TMP/prep-B1.log")"
for forbidden in paid_observe paid_admission passprep b2_context b0_decision b0_context; do
  check "forced B1 skips $forbidden prep" 0 "$(prep_count "$forbidden" "$TMP/prep-B1.log")"
done

run_forced_prep_pass B2
check "forced B2 runs passprep once" 1 "$(prep_count passprep "$TMP/prep-B2.log")"
check "forced B2 builds B2 context once" 1 "$(prep_count b2_context "$TMP/prep-B2.log")"
for forbidden in paid_observe paid_admission project_fence reply_build reply_enqueue b1_context b0_decision b0_context; do
  check "forced B2 skips $forbidden prep" 0 "$(prep_count "$forbidden" "$TMP/prep-B2.log")"
done

run_forced_prep_pass B0
check "forced B0 prep is rejected" 64 "$PREP_PASS_RC"
check "forced B0 computes no B0 decision" 0 "$(prep_count b0_decision "$TMP/prep-B0.log")"
check "forced B0 builds no B0 context" 0 "$(prep_count b0_context "$TMP/prep-B0.log")"
for forbidden in paid_observe paid_admission project_fence reply_build reply_enqueue b1_context passprep b2_context; do
  check "forced B0 skips $forbidden prep" 0 "$(prep_count "$forbidden" "$TMP/prep-B0.log")"
done

# Legacy unforced control: every deterministic prep remains reachable in one pass.
LEGACY_PREP_LOG="$TMP/prep-legacy.log"
: > "$LEGACY_PREP_LOG"
set +e
HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/empty-snapshot.json" \
  GIG_LOCK_DIR="$TMP/prep-legacy-lock.d" GIG_EVIDENCE_DIR="$TMP/prep-legacy-evidence" \
  GIG_STEP_CALL_LOG="$TMP/prep-legacy-runner.log" GIG_CONTEXT_LEASE_LOG="$CONTEXT_LEASE_LOG" \
  GIG_PARENT_RUN_LOG="$TMP/prep-legacy-parent.log" GIG_PREP_CALL_LOG="$LEGACY_PREP_LOG" \
  GIG_TEST_CDP_ALIVE=1 GIG_STEP_COOLDOWN_STATE_DIR="$TMP/prep-legacy-cooldown" \
  GIG_MODEL_CALL_LIMIT=7 timeout 20 bash "$GIG_DIR/gig_pass.sh" \
  >"$TMP/prep-legacy-out" 2>"$TMP/prep-legacy-err"
legacy_prep_rc=$?
set -e
for required in paid_observe paid_admission project_fence reply_build reply_enqueue b1_context passprep b2_context; do
  check "legacy prep keeps $required" 1 "$( [ "$(prep_count "$required" "$LEGACY_PREP_LOG")" -ge 1 ] && echo 1 || echo 0 )"
done
check "legacy prep does not rebuild B0 context" 0 "$(prep_count b0_context "$LEGACY_PREP_LOG")"
check "legacy prep does not compute B0 decisions" 0 "$(prep_count b0_decision "$LEGACY_PREP_LOG")"

# P0c: forced PAID_WORK is a pinned two-stage path. Replace only the queue builder with a
# bounded fixture stub so the real pass still owns admission and orchestration, while no
# browser/model/customer effect is reachable. The first command is preliminary selection;
# the second is the one strict targeted rebuild.
STAGE_CALL_LOG="$TMP/p0c-stage-calls.log"
cat > "$GIG_DIR/scripts/delivery_queue.py" <<'PY'
#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
command = args[0] if args else ""
def value(flag):
    return args[args.index(flag) + 1]
def log(name):
    path = os.environ.get("GIG_STAGE_CALL_LOG")
    if path:
        Path(path).open("a", encoding="utf-8").write(name + "\n")
def output(payload):
    Path(value("--output")).write_text(json.dumps(payload) + "\n", encoding="utf-8")

snapshot = json.loads(Path(value("--snapshot")).read_text(encoding="utf-8"))
orders = snapshot.get("orders") or []
if command == "preliminary":
    log("preliminary")
    item = dict(orders[0]) if orders else {}
    item.update({
        "selection_stage": "preliminary", "targeted_readback_required": True,
        "queue_class": "other_paid_work", "delivery_action": "none",
        "blockers": ["targeted_talkroom_readback_required"],
    })
    output({"version": 1, "selection_stage": "preliminary", "items": [item] if item else []})
elif command == "build":
    log("build")
    if os.environ.get("GIG_P0C_TARGETED_QUEUE_EMPTY") == "1":
        output({"version": 1, "items": []})
        raise SystemExit(0)
    item = dict(orders[0]) if orders else {}
    actionable = os.environ.get("GIG_P0C_ACTIONABLE") == "1"
    item.update({"selection_stage": "targeted", "targeted_readback_required": False,
                 "queue_class": "buyer_feedback_or_revision", "delivery_action": "progress" if actionable else "none",
                 "blockers": []})
    output({"version": 1, "selection_stage": "targeted", "items": [item] if item else []})
else:
    raise SystemExit("unexpected delivery_queue command")
PY
chmod +x "$GIG_DIR/scripts/delivery_queue.py"

# P0c collector seam: exercise both production collector invocations and capture
# their exact selected-room arguments without opening a browser.
cat > "$GIG_DIR/scripts/coconala_queue_snapshot.py" <<'PY'
#!/usr/bin/env python3
import argparse
import copy
import json
import os
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--mode", default="full")
parser.add_argument("--talkroom-id")
parser.add_argument("--project-id")
parser.add_argument("--selected-order-input")
parser.add_argument("--output", required=True)
parser.add_argument("--evidence-dir")
parser.add_argument("--projects-root")
args = parser.parse_args()

selected_input = {}
if args.selected_order_input:
    selected_input = json.loads(Path(args.selected_order_input).read_text(encoding="utf-8"))
call = {
    "mode": args.mode,
    "talkroom_id": args.talkroom_id or "",
    "project_id": args.project_id or "",
    "selected_input": args.selected_order_input or "",
    "selected_input_talkroom": str(selected_input.get("talkroom_id") or ""),
}
call_log = os.environ.get("GIG_COLLECTOR_CALL_LOG")
if call_log:
    with Path(call_log).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(call, sort_keys=True) + "\n")

route = "https://coconala.com/talkrooms/4201"
order = {
    "request_id": "req-4201",
    "contract_id": "talkroom:4201",
    "talkroom_id": "4201",
    "marketplace_url": route,
    "buyer": "fixture",
    "title": "forced paid target",
    "status": "paid",
    "price_jpy": 17000,
    "price_source": "structured_order_label",
    "talkroom_state": "取引中",
    "buyer_feedback_pending_artifact": True,
    "buyer_visible_artifact_observed": False,
    "formal_delivery_observed": False,
}
receipt = {
    "source": "selected_talkroom",
    "requested_route": route,
    "final_route": route,
    "login_redirect": False,
    "coverage_complete": True,
}
if args.mode == "orders-only":
    stage1_empty = os.environ.get("GIG_STAGE1_RESULT_MODE") == "empty"
    payload = {
        "source": "authenticated_coconala_hidden_default_context_dom",
        "read_only": True,
        "collector_mode": "orders-only",
        "observed_sources": ["orders"],
        "open_orders_list_observed": True,
        "orders": [] if stage1_empty else [order],
        "source_receipt": {**receipt, "source": "orders",
                           "requested_route": "https://coconala.com/mypage/received_orders/open",
                           "final_route": "https://coconala.com/mypage/received_orders/open"},
    }
elif args.mode == "selected-talkroom-only":
    result_mode = os.environ.get("GIG_TARGETED_RESULT_MODE", "valid")
    targeted = copy.deepcopy(order)
    if result_mode == "mismatch":
        targeted["request_id"] = "req-4202"
        targeted["contract_id"] = "talkroom:4202"
        targeted["talkroom_id"] = "4202"
        targeted["marketplace_url"] = "https://coconala.com/talkrooms/4202"
    elif result_mode == "empty":
        targeted = None
    elif result_mode == "nonactionable":
        targeted.update({
            "talkroom_state": "納品確認待ち",
            "formal_delivery_observed": True,
            "buyer_feedback_pending_artifact": False,
            "buyer_visible_artifact_observed": True,
        })
    elif result_mode in {"incomplete", "redirect", "wrong-route"}:
        if result_mode == "incomplete":
            receipt["coverage_complete"] = False
        elif result_mode == "redirect":
            receipt["login_redirect"] = True
        else:
            receipt["requested_route"] = "https://coconala.com/talkrooms/4202"
    if targeted is not None:
        targeted.update({"selection_stage": "targeted", "targeted_readback_required": False})
    payload = {
        "source": "authenticated_coconala_hidden_default_context_dom",
        "read_only": True,
        "collector_mode": "selected-talkroom-only",
        "observed_sources": ["selected_talkroom"],
        "talkroom_id": args.talkroom_id,
        "orders": [targeted] if targeted is not None else [],
        "source_receipt": receipt,
    }
else:
    raise SystemExit("unexpected collector mode")
Path(args.output).write_text(json.dumps(payload) + "\n", encoding="utf-8")
PY
chmod +x "$GIG_DIR/scripts/coconala_queue_snapshot.py"

# Actionable P0c reaches the real paid dispatcher. These bounded seams satisfy only
# read/transaction preconditions; the runner still returns 42 before any effect.
cat > "$GIG_DIR/scripts/project_context_compiler.py" <<'PY'
#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--project-root", required=True)
parser.add_argument("--queue-item", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--evidence-output", required=True)
parser.add_argument("--receipt-evidence-output", required=True)
args = parser.parse_args()
item = json.loads(Path(args.queue_item).read_text(encoding="utf-8"))
root = Path(args.project_root)
root.joinpath("context").mkdir(parents=True, exist_ok=True)
payload = {
    "version": 1,
    "combined_context": {"order": item, "buyer_feedback": {}, "our_commitments": []},
    "read_these_first": [],
}
Path(args.output).write_text(json.dumps(payload) + "\n", encoding="utf-8")
Path(args.evidence_output).write_text('{"status":"ok"}\n', encoding="utf-8")
Path(args.receipt_evidence_output).write_text('{"status":"ok","coverage_complete":true}\n', encoding="utf-8")
PY
chmod +x "$GIG_DIR/scripts/project_context_compiler.py"

cat > "$GIG_DIR/scripts/paid_work_contract_bootstrap.py" <<'PY'
#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--project-root", required=True)
args = parser.parse_args()
root = Path(args.project_root) / "delivery"
root.mkdir(parents=True, exist_ok=True)
contract = root / "validation-contract.json"
if not contract.exists():
    contract.write_text(json.dumps({"version": 1, "trusted_files": []}) + "\n", encoding="utf-8")
PY
chmod +x "$GIG_DIR/scripts/paid_work_contract_bootstrap.py"

cat > "$GIG_DIR/scripts/paid_work_transaction.py" <<'PY'
#!/usr/bin/env python3
import sys

if sys.argv[1:2] not in (["begin"], ["rollback"]):
    raise SystemExit(2)
PY
chmod +x "$GIG_DIR/scripts/paid_work_transaction.py"

cat > "$GIG_DIR/scripts/gig_context_packet.py" <<'PY'
#!/usr/bin/env python3
import json
print(json.dumps({"version": 1, "test_only": True}))
PY
chmod +x "$GIG_DIR/scripts/gig_context_packet.py"

run_p0c_forced() {
  local label="$1" target="$2"
  local stage_log="$TMP/p0c-$label-stage.log"
  local admission_log="$TMP/p0c-$label-admission.log"
  local runner_log="$TMP/p0c-$label-runner.log"
  local evidence="$TMP/p0c-$label-evidence"
  : > "$stage_log"; : > "$admission_log"; : > "$runner_log"
  set +e
  HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_P0C_TEST_FIXTURES=1 \
    GIG_QUEUE_FIXTURE="$TMP/paid-snapshot.json" \
    GIG_FORCED_PAID_TARGETED_FIXTURE="$target" GIG_LOCK_DIR="$TMP/p0c-$label-lock.d" \
    GIG_EVIDENCE_DIR="$evidence" GIG_STAGE_CALL_LOG="$stage_log" \
    GIG_P0C_ACTIONABLE=1 \
    GIG_STEP_CALL_LOG="$runner_log" GIG_CONTEXT_LEASE_LOG="$CONTEXT_LEASE_LOG" \
    GIG_PREP_CALL_LOG="$admission_log" GIG_TEST_CDP_ALIVE=1 \
    GIG_HERMES_FORCED_STEP=PAID_WORK GIG_HERMES_OWNED_STEPS=PAID_WORK \
    GIG_INSTANT_REPORTS_ENABLED=0 timeout 20 bash "$GIG_DIR/gig_pass.sh" \
    >"$TMP/p0c-$label-out" 2>"$TMP/p0c-$label-err"
  P0C_RUN_RC=$?
  set -e
  P0C_STAGE_LOG="$stage_log" P0C_ADMISSION_LOG="$admission_log" \
    P0C_RUNNER_LOG="$runner_log" P0C_EVIDENCE="$evidence"
}

run_p0c_forced valid "$TMP/targeted-snapshot.json"
check "P0c valid Stage 1 preliminary runs once" 1 "$(grep -c '^preliminary$' "$P0C_STAGE_LOG" 2>/dev/null || true)"
check "P0c valid Stage 2 strict build runs once" 1 "$(grep -c '^build$' "$P0C_STAGE_LOG" 2>/dev/null || true)"
check "P0c valid observer runs once" 1 "$(prep_count paid_observe "$P0C_ADMISSION_LOG")"
check "P0c valid admission runs once" 1 "$(prep_count paid_admission "$P0C_ADMISSION_LOG")"
check "P0c valid admission ledger commit runs once after target" 1 "$(prep_count paid_admission_record "$P0C_ADMISSION_LOG")"
check "P0c valid paid executor runs exactly once" 1 "$(grep -c '^gig-PAID_WORK$' "$P0C_RUNNER_LOG" 2>/dev/null || true)"
check "P0c valid target has only selected source and one order" yes "$(python3 - "$P0C_EVIDENCE/selected-talkroom-snapshot.json" <<'PY'
import json, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))
print("yes" if value.get("observed_sources") == ["selected_talkroom"] and len(value.get("orders", [])) == 1 else "no")
PY
)"
check "P0c valid selected input is owner-only 0600" yes "$(python3 - "$P0C_EVIDENCE/selected-order-input.json" <<'PY'
import os
import stat
import sys
from pathlib import Path
path = Path(sys.argv[1])
print("yes" if stat.S_IMODE(path.stat().st_mode) == 0o600 and path.stat().st_uid == os.getuid() else "no")
PY
)"

cat > "$TMP/targeted-mismatch.json" <<'JSON'
{"source":"authenticated_coconala_hidden_default_context_dom","read_only":true,
 "collector_mode":"selected-talkroom-only","observed_sources":["selected_talkroom"],
 "orders":[{"contract_id":"talkroom:4202","talkroom_id":"4202","status":"paid",
             "selection_stage":"targeted","targeted_readback_required":false}]}
JSON
run_p0c_forced mismatch "$TMP/targeted-mismatch.json"
check "P0c mismatch observes once and keeps one admission" 1 "$(prep_count paid_observe "$P0C_ADMISSION_LOG")"
check "P0c mismatch admission runs once" 1 "$(prep_count paid_admission "$P0C_ADMISSION_LOG")"
check "P0c mismatch does not fallback to another room" 0 "$(grep -c '^build$' "$P0C_STAGE_LOG" 2>/dev/null || true)"
check "P0c mismatch does not call paid executor" 0 "$(wc -l < "$P0C_RUNNER_LOG" | tr -d ' ')"

cat > "$TMP/targeted-empty.json" <<'JSON'
{"source":"authenticated_coconala_hidden_default_context_dom","read_only":true,
 "collector_mode":"selected-talkroom-only","observed_sources":["selected_talkroom"],
 "orders":[]}
JSON
run_p0c_forced empty "$TMP/targeted-empty.json"
check "P0c empty observes once and keeps one admission" 1 "$(prep_count paid_observe "$P0C_ADMISSION_LOG")"
check "P0c empty admission runs once" 1 "$(prep_count paid_admission "$P0C_ADMISSION_LOG")"
check "P0c empty does not fallback to another room" 0 "$(grep -c '^build$' "$P0C_STAGE_LOG" 2>/dev/null || true)"
check "P0c empty does not call paid executor" 0 "$(wc -l < "$P0C_RUNNER_LOG" | tr -d ' ')"

run_p0c_collector() {
  local label="$1" target_mode="${2:-valid}" admission_mode="${3:-valid}" stage1_mode="${4:-valid}" actionable="${5:-1}" strict_empty="${6:-0}"
  local stage_log="$TMP/p0c-collector-$label-stage.log"
  local admission_log="$TMP/p0c-collector-$label-admission.log"
  local collector_log="$TMP/p0c-collector-$label-calls.jsonl"
  local runner_log="$TMP/p0c-collector-$label-runner.log"
  local runner_meta="$TMP/p0c-collector-$label-runner-meta.jsonl"
  local evidence="$TMP/p0c-collector-$label-evidence"
  local truth="$TMP/p0c-collector-$label-truth.json"
  : > "$stage_log"; : > "$admission_log"; : > "$collector_log"; : > "$runner_log"; : > "$runner_meta"
  set +e
  HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 \
    GIG_TARGETED_RESULT_MODE="$target_mode" GIG_ADMISSION_RESULT="$admission_mode" \
    GIG_STAGE1_RESULT_MODE="$stage1_mode" GIG_HERMES_TRUTH_PATH="$truth" \
    GIG_P0C_ACTIONABLE="$actionable" GIG_P0C_RUNNER_METADATA_LOG="$TMP/p0c-collector-$label-runner-meta.jsonl" \
    GIG_P0C_TARGETED_QUEUE_EMPTY="$strict_empty" \
    GIG_LOCK_DIR="$TMP/p0c-collector-$label-lock.d" GIG_EVIDENCE_DIR="$evidence" \
    GIG_STAGE_CALL_LOG="$stage_log" GIG_COLLECTOR_CALL_LOG="$collector_log" \
    GIG_STEP_CALL_LOG="$runner_log" GIG_P0C_RUNNER_METADATA_LOG="$runner_meta" \
    GIG_CONTEXT_LEASE_LOG="$CONTEXT_LEASE_LOG" \
    GIG_PREP_CALL_LOG="$admission_log" GIG_TEST_CDP_ALIVE=1 \
    GIG_HERMES_FORCED_STEP=PAID_WORK GIG_HERMES_OWNED_STEPS=PAID_WORK \
    GIG_INSTANT_REPORTS_ENABLED=0 timeout 20 bash "$GIG_DIR/gig_pass.sh" \
    >"$TMP/p0c-collector-$label-out" 2>"$TMP/p0c-collector-$label-err"
  P0C_RUN_RC=$?
  set -e
  P0C_STAGE_LOG="$stage_log" P0C_ADMISSION_LOG="$admission_log" \
    P0C_COLLECTOR_LOG="$collector_log" P0C_RUNNER_LOG="$runner_log" P0C_RUNNER_META="$runner_meta" \
    P0C_EVIDENCE="$evidence" P0C_PROJECT_ROOT="$HOME_DIR/gig/projects/req-4201" \
    P0C_TRUTH="$truth"
}

collector_call_contract() {
  python3 - "$1" <<'PY'
import json
import sys
from pathlib import Path

rows = [json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines() if line]
ok = len(rows) == 2 and rows[0] == {
    "mode": "orders-only", "talkroom_id": "", "project_id": "",
    "selected_input": "", "selected_input_talkroom": "",
} and rows[1]["mode"] == "selected-talkroom-only" \
    and rows[1]["talkroom_id"] == "4201" \
    and rows[1]["project_id"] == "req-4201" \
    and rows[1]["selected_input"].endswith("/selected-order-input.json") \
    and rows[1]["selected_input_talkroom"] == "4201"
print("yes" if ok else "no")
PY
}

verified_noop_truth_contract() {
  python3 - "$1" <<'PY'
import json
import sys

value = json.load(open(sys.argv[1], encoding="utf-8"))
closure = value.get("lane_closure") or {}
reason = value.get("no_action_reason")
ok = (
    value.get("status") == "success"
    and value.get("outcome") == "verified"
    and value.get("coverage_complete") is True
    and value.get("collector_complete") is True
    and value.get("blocked") is False
    and value.get("incomplete") is False
    and value.get("unclosed") is False
    and closure.get("closed") is True
    and closure.get("action_kind") == "verified_noop"
    and value.get("external_effect_expected") is False
    and value.get("official_readback_count") == 0
    and value.get("send_verified") is False
    and isinstance(reason, str)
    and bool(reason.strip())
)
print("yes" if ok else "no")
PY
}

run_p0c_collector collector-valid
check "P0c collector Stage 1 and Stage 2 calls are exact" yes "$(collector_call_contract "$P0C_COLLECTOR_LOG")"
check "P0c collector orders-only runs once" 1 "$(grep -c '"mode": "orders-only"' "$P0C_COLLECTOR_LOG" 2>/dev/null || true)"
check "P0c collector selected-talkroom-only runs once" 1 "$(grep -c '"mode": "selected-talkroom-only"' "$P0C_COLLECTOR_LOG" 2>/dev/null || true)"
check "P0c collector valid strict build runs once" 1 "$(grep -c '^build$' "$P0C_STAGE_LOG" 2>/dev/null || true)"
check "P0c collector targeted ledger selection runs once" 1 "$(grep -c 'queue_selected' "$P0C_PROJECT_ROOT/events.jsonl" 2>/dev/null || true)"
check "P0c collector valid paid executor runs exactly once" 1 "$(grep -c '^gig-PAID_WORK$' "$P0C_RUNNER_LOG" 2>/dev/null || true)"

run_p0c_collector collector-actionable valid valid valid 1
check "P0c actionable Stage 1 preliminary runs once" 1 "$(grep -c '^preliminary$' "$P0C_STAGE_LOG" 2>/dev/null || true)"
check "P0c actionable Stage 2 strict build runs once" 1 "$(grep -c '^build$' "$P0C_STAGE_LOG" 2>/dev/null || true)"
check "P0c actionable paid executor runs exactly once" 1 "$(grep -c '^gig-PAID_WORK$' "$P0C_RUNNER_LOG" 2>/dev/null || true)"
check "P0c actionable no-effect runner returns expected nonzero" yes "$([ "$P0C_RUN_RC" -ne 0 ] && echo yes || echo no)"
check "P0c actionable does not run other lane executors" 0 "$(grep -Ec '^(gig-B0|gig-B1|gig-B2|gig-PROFILE|gig-LEARN|gig-reply|gig-storefront)$' "$P0C_RUNNER_LOG" 2>/dev/null || true)"
check "P0c actionable executor keeps admitted project identity" yes "$(python3 - "$P0C_RUNNER_META" "$P0C_PROJECT_ROOT" <<'PY'
import json
import sys
from pathlib import Path

rows = [json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines() if line]
print("yes" if rows == [{"label": "gig-PAID_WORK", "workdir": sys.argv[2]}] else "no")
PY
)"

targeted_nonactionable_events_before=$(grep -c 'queue_selected' "$HOME_DIR/gig/projects/req-4201/events.jsonl" 2>/dev/null || true)
run_p0c_collector collector-targeted-nonactionable nonactionable valid valid 1 1
targeted_nonactionable_events_after=$(grep -c 'queue_selected' "$HOME_DIR/gig/projects/req-4201/events.jsonl" 2>/dev/null || true)
check "P0c targeted nonactionable Stage 1 preliminary runs once" 1 "$(grep -c '^preliminary$' "$P0C_STAGE_LOG" 2>/dev/null || true)"
check "P0c targeted nonactionable Stage 2 strict build runs once" 1 "$(grep -c '^build$' "$P0C_STAGE_LOG" 2>/dev/null || true)"
check "P0c targeted nonactionable exits healthy verified no-op" 0 "$P0C_RUN_RC"
check "P0c targeted nonactionable writes exact verified-noop truth" yes "$(verified_noop_truth_contract "$P0C_TRUTH")"
check "P0c targeted nonactionable reason is typed" targeted_order_nonactionable "$(python3 - "$P0C_TRUTH" <<'PY'
import json
import sys
print(json.load(open(sys.argv[1], encoding="utf-8")).get("no_action_reason", ""))
PY
)"
check "P0c targeted nonactionable does not commit admission ledger" 0 "$(prep_count paid_admission_record "$P0C_ADMISSION_LOG")"
check "P0c targeted nonactionable does not commit targeted project selection" 0 "$((targeted_nonactionable_events_after - targeted_nonactionable_events_before))"
check "P0c targeted nonactionable does not call paid executor" 0 "$(wc -l < "$P0C_RUNNER_LOG" | tr -d ' ')"

for admission_mode in failure multiple unknown; do
  run_p0c_collector "admission-$admission_mode" valid "$admission_mode"
  check "P0c admission $admission_mode observes once" 1 "$(prep_count paid_observe "$P0C_ADMISSION_LOG")"
  check "P0c admission $admission_mode runs once" 1 "$(prep_count paid_admission "$P0C_ADMISSION_LOG")"
  check "P0c admission $admission_mode Stage 1 runs once" 1 "$(grep -c '^preliminary$' "$P0C_STAGE_LOG" 2>/dev/null || true)"
  check "P0c admission $admission_mode does not enter Stage 2" 0 "$(grep -c '"mode": "selected-talkroom-only"' "$P0C_COLLECTOR_LOG" 2>/dev/null || true)"
  check "P0c admission $admission_mode does not strict-build" 0 "$(grep -c '^build$' "$P0C_STAGE_LOG" 2>/dev/null || true)"
  check "P0c admission $admission_mode does not call paid executor" 0 "$(wc -l < "$P0C_RUNNER_LOG" | tr -d ' ')"
done

for target_mode in incomplete redirect wrong-route; do
  run_p0c_collector "target-$target_mode" "$target_mode"
  check "P0c target $target_mode Stage 1 runs once" 1 "$(grep -c '^preliminary$' "$P0C_STAGE_LOG" 2>/dev/null || true)"
  check "P0c target $target_mode selected readback runs once" 1 "$(grep -c '"mode": "selected-talkroom-only"' "$P0C_COLLECTOR_LOG" 2>/dev/null || true)"
  check "P0c target $target_mode rejects strict build" 0 "$(grep -c '^build$' "$P0C_STAGE_LOG" 2>/dev/null || true)"
  check "P0c target $target_mode does not call paid executor" 0 "$(wc -l < "$P0C_RUNNER_LOG" | tr -d ' ')"
done

for empty_case in stage-empty all-skipped; do
  if [ "$empty_case" = "stage-empty" ]; then
    run_p0c_collector "$empty_case" valid valid empty
  else
    run_p0c_collector "$empty_case" valid all-skipped valid
  fi
  check "P0c $empty_case exits healthy verified no-op" 0 "$P0C_RUN_RC"
  check "P0c $empty_case writes exact verified-noop truth" yes "$(verified_noop_truth_contract "$P0C_TRUTH")"
  check "P0c $empty_case admission plans once" 1 "$(prep_count paid_admission "$P0C_ADMISSION_LOG")"
  check "P0c $empty_case does not enter Stage 2" 0 "$(grep -c '"mode": "selected-talkroom-only"' "$P0C_COLLECTOR_LOG" 2>/dev/null || true)"
  check "P0c $empty_case does not strict-build" 0 "$(grep -c '^build$' "$P0C_STAGE_LOG" 2>/dev/null || true)"
  check "P0c $empty_case does not commit admission ledger" 0 "$(prep_count paid_admission_record "$P0C_ADMISSION_LOG")"
  check "P0c $empty_case does not call paid executor" 0 "$(wc -l < "$P0C_RUNNER_LOG" | tr -d ' ')"
done

run_p0c_fixture_rejected() {
  local label="$1" fixture_kind="$2"
  local collector_log="$TMP/p0c-fixture-$label-collector.jsonl"
  local runner_log="$TMP/p0c-fixture-$label-runner.log"
  local evidence="$TMP/p0c-fixture-$label-evidence"
  : > "$collector_log"; : > "$runner_log"
  set +e
  if [ "$fixture_kind" = "queue" ]; then
    HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/paid-snapshot.json" \
      GIG_LOCK_DIR="$TMP/p0c-fixture-$label-lock.d" GIG_EVIDENCE_DIR="$evidence" \
      GIG_COLLECTOR_CALL_LOG="$collector_log" GIG_STEP_CALL_LOG="$runner_log" \
      GIG_CONTEXT_LEASE_LOG="$CONTEXT_LEASE_LOG" GIG_TEST_CDP_ALIVE=1 \
      GIG_HERMES_FORCED_STEP=PAID_WORK GIG_HERMES_OWNED_STEPS=PAID_WORK \
      GIG_INSTANT_REPORTS_ENABLED=0 timeout 20 bash "$GIG_DIR/gig_pass.sh" \
      >"$TMP/p0c-fixture-$label-out" 2>"$TMP/p0c-fixture-$label-err"
  else
    HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_FORCED_PAID_TARGETED_FIXTURE="$TMP/targeted-snapshot.json" \
      GIG_LOCK_DIR="$TMP/p0c-fixture-$label-lock.d" GIG_EVIDENCE_DIR="$evidence" \
      GIG_COLLECTOR_CALL_LOG="$collector_log" GIG_STEP_CALL_LOG="$runner_log" \
      GIG_CONTEXT_LEASE_LOG="$CONTEXT_LEASE_LOG" GIG_TEST_CDP_ALIVE=1 \
      GIG_HERMES_FORCED_STEP=PAID_WORK GIG_HERMES_OWNED_STEPS=PAID_WORK \
      GIG_INSTANT_REPORTS_ENABLED=0 timeout 20 bash "$GIG_DIR/gig_pass.sh" \
      >"$TMP/p0c-fixture-$label-out" 2>"$TMP/p0c-fixture-$label-err"
  fi
  P0C_RUN_RC=$?
  set -e
  P0C_COLLECTOR_LOG="$collector_log" P0C_RUNNER_LOG="$runner_log"
}

for fixture_kind in queue targeted; do
  run_p0c_fixture_rejected "${fixture_kind}-rejected" "$fixture_kind"
  check "P0c $fixture_kind fixture without test guard rejects" yes "$([ "$P0C_RUN_RC" -ne 0 ] && echo yes || echo no)"
  check "P0c $fixture_kind fixture without test guard does not call executor" 0 "$(wc -l < "$P0C_RUNNER_LOG" | tr -d ' ')"
done

echo
if [ "$fails" -gt 0 ]; then
  echo "$fails failed"
  echo "--- stderr ---"; tail -30 "$TMP/err"
  exit 1
fi
echo "PASS: one pass drives every due lane and isolates their failures"
