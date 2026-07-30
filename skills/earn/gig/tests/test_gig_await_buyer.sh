#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d /tmp/gig-await-buyer.XXXXXX)
trap 'if [ "${KEEP_TMP:-0}" = 1 ]; then echo "KEEP_TMP=$TMP"; else rm -rf "$TMP"; fi' EXIT
HOME_DIR="$TMP/home"
G="$HOME_DIR/life-manager/skills/earn/gig"
mkdir -p "$HOME_DIR/gig/projects/17943244" "$G/scripts" "$G/schemas" "$G/config/connectors" \
  "$HOME_DIR/life-manager/runtime/agent-runner" "$HOME_DIR/loops/gig/state"
cp "$SKILL_DIR/gig_pass.sh" "$G/gig_pass.sh"
cp "$SKILL_DIR/scripts/gig_paths.sh" "$G/scripts/gig_paths.sh"
cp "$SKILL_DIR/scripts/gig_paths.py" "$G/scripts/gig_paths.py"
cp "$SKILL_DIR/scripts/delivery_queue.py" "$G/scripts/delivery_queue.py"
cp "$SKILL_DIR/scripts/delivery_cadence.py" "$G/scripts/delivery_cadence.py"
cp "$SKILL_DIR/scripts/delivery_project.py" "$G/scripts/delivery_project.py"
cp "$SKILL_DIR/scripts/project_ledger.py" "$G/scripts/project_ledger.py"
cp "$SKILL_DIR/scripts/delivery_identity.py" "$G/scripts/delivery_identity.py"
cp "$SKILL_DIR/scripts/b2_queue_gate.py" "$G/scripts/b2_queue_gate.py"
cp "$SKILL_DIR/scripts/b2_result_gate.py" "$G/scripts/b2_result_gate.py"
cp "$SKILL_DIR/scripts/application_report.py" "$G/scripts/application_report.py"
cp "$SKILL_DIR/scripts/coconala_applied_readback.py" "$G/scripts/coconala_applied_readback.py"
cp "$SKILL_DIR/scripts/normalize_applied.py" "$G/scripts/normalize_applied.py"
cp "$SKILL_DIR/scripts/b1_conversation_gate.py" "$G/scripts/b1_conversation_gate.py"
cp "$SKILL_DIR/scripts/b0_objective.py" "$G/scripts/b0_objective.py"
cp "$SKILL_DIR/scripts/b0_result_gate.py" "$G/scripts/b0_result_gate.py"
cp "$SKILL_DIR/scripts/lane_health.py" "$G/scripts/lane_health.py"
cp "$SKILL_DIR/scripts/lane_state_machine.py" "$G/scripts/lane_state_machine.py"
cp "$SKILL_DIR/scripts/lane_action_runtime.py" "$G/scripts/lane_action_runtime.py"
cp "$SKILL_DIR/scripts/lane_productivity.py" "$G/scripts/lane_productivity.py"
cp "$SKILL_DIR/scripts/listing_ledger.py" "$G/scripts/listing_ledger.py"
cp "$SKILL_DIR/scripts/paid_work_evidence.py" "$G/scripts/paid_work_evidence.py"
cp "$SKILL_DIR/scripts/paid_work_transaction.py" "$G/scripts/paid_work_transaction.py"
cp "$SKILL_DIR/scripts/paid_work_validation_contract.py" "$G/scripts/paid_work_validation_contract.py"
cp "$SKILL_DIR/scripts/paid_queue_evidence.py" "$G/scripts/paid_queue_evidence.py"
cp "$SKILL_DIR/scripts/gig_context_packet.py" "$G/scripts/gig_context_packet.py"
cp "$SKILL_DIR/scripts/b2_wall_clock.py" "$G/scripts/b2_wall_clock.py"
cp "$SKILL_DIR/scripts/b2_search_objective.py" "$G/scripts/b2_search_objective.py"
cp "$SKILL_DIR/../../../runtime/agent-runner/context_packet.py" "$HOME_DIR/life-manager/runtime/agent-runner/context_packet.py"
cp "$SKILL_DIR/scripts/reply_queue.py" "$G/scripts/reply_queue.py"
cp "$SKILL_DIR/scripts/connector_outbox.py" "$G/scripts/connector_outbox.py"
cp "$SKILL_DIR/config/connectors/coconala.json" "$G/config/connectors/coconala.json"
cp "$SKILL_DIR/scripts/reconcile_paid_delivery.py" "$G/scripts/reconcile_paid_delivery.py"
cp "$SKILL_DIR/scripts/cdp_lock.sh" "$G/scripts/cdp_lock.sh"
cp "$SKILL_DIR/scripts/run_with_cdp_lock.sh" "$G/scripts/run_with_cdp_lock.sh"
cp "$SKILL_DIR/schemas/gig_b1_result.schema.json" "$G/schemas/gig_b1_result.schema.json"
cp "$SKILL_DIR/schemas/gig_b2_result.schema.json" "$G/schemas/gig_b2_result.schema.json"
cp "$SKILL_DIR/schemas/gig_step_result.schema.json" "$G/schemas/gig_step_result.schema.json"
cp "$SKILL_DIR/schemas/gig_b0_result.schema.json" "$G/schemas/gig_b0_result.schema.json"
cp "$SKILL_DIR/schemas/gig_reflect_result.schema.json" "$G/schemas/gig_reflect_result.schema.json"
chmod +x "$G/scripts/run_with_cdp_lock.sh"

cat > "$TMP/snapshot.json" <<'JSON'
{
  "captured_at": "2026-07-22T03:27:17+00:00",
  "inbox": {"url": "https://coconala.com/message?fromMyPage=true", "not_found": false},
  "orders": [{
    "contract_id": "direct-offer:6198868",
    "talkroom_id": "17943244",
    "buyer": "buyer",
    "title": "generic paid work",
    "price_jpy": 40000,
    "delivery_date": "2026-08-14",
    "status": "paid",
    "talkroom_state": "取引中",
    "buyer_visible_artifact_observed": true,
    "buyer_feedback_pending_artifact": false,
    "buyer_agreement_observed": false,
    "formal_delivery_observed": false
  }],
  "quotes": [],
  "inquiries": []
}
JSON
cat > "$HOME_DIR/gig/projects/17943244/state.json" <<'JSON'
{
  "request_id": "17943244",
  "adapter": "coconala",
  "buyer_visible": true,
  "formal_delivery": false,
  "next_action": "await_buyer_approval_for_publication"
}
JSON
touch "$HOME_DIR/gig/projects/17943244/events.jsonl"
mkdir -p "$HOME_DIR/gig/projects/17943244/source" "$HOME_DIR/gig/projects/17943244/delivery"
cat > "$HOME_DIR/gig/projects/17943244/source/validate_fixture.py" <<'PY'
import json, sys
from pathlib import Path
artifact = Path(sys.argv[1])
assert artifact.is_file() and artifact.stat().st_size >= 8
print(json.dumps({"status": "PASS"}))
PY
cat > "$HOME_DIR/gig/projects/17943244/delivery/validation-contract.json" <<'JSON'
{
  "version": 1,
  "artifact": {"type": "file", "min_size_bytes": 8, "allowed_suffixes": [".zip"]},
  "trusted_files": ["source/validate_fixture.py"],
  "commands": [
    {"id": "fixture-domain", "kind": "domain", "argv": ["python3", "source/validate_fixture.py", "{artifact_path}"], "timeout_seconds": 30, "expect_stdout_json": {"status": "PASS"}},
    {"id": "fixture-test", "kind": "test", "argv": ["python3", "source/validate_fixture.py", "{artifact_path}"], "timeout_seconds": 30, "expect_stdout_json": {"status": "PASS"}}
  ]
}
JSON
printf '%s\n' '{"requestId":"existing","status":"applied"}' > "$HOME_DIR/gig/applied.jsonl"
printf '%s\n' '{"pass_id":"existing","requestId":"existing","action":"applied"}' > "$HOME_DIR/loops/gig/state/task-request-map.jsonl"

cat > "$HOME_DIR/life-manager/runtime/agent-runner/agent_runner.py" <<'PY'
#!/usr/bin/env python3
import hashlib, json, os, sys
from pathlib import Path
args=sys.argv[1:]
task_label=args[args.index("--task-label")+1]
label=task_label.removeprefix("gig-")
open(os.environ["GIG_TEST_RUNNER_LOG"],"a").write(task_label+"\n")
if label == "PAID_WORK":
    root=Path(args[args.index("--workdir")+1])
    for name in ("requirements", "source", "work", "artifacts", "acceptance", "delivery", "evidence"):
        (root/name).mkdir(parents=True,exist_ok=True)
    req=root/"requirements/latest-feedback.json"; req.write_text('{"feedback":"revision"}\n')
    artifact=root/"artifacts/delivery-v3.zip"; artifact.write_bytes(b"await v3")
    acceptance=root/"acceptance/v3.json"; acceptance.write_text('{"status":"PASS","acceptance_delta":["revision"]}\n')
    digest=hashlib.sha256(artifact.read_bytes()).hexdigest()
    row={"status":"ok","project_root":str(root),"requirements_path":str(req),"artifact_path":str(artifact),"artifact_version":"v3","acceptance_evidence_path":str(acceptance),"acceptance_status":"PASS","acceptance_delta":["revision"],"package_sha256":digest}
    (root/"delivery/paid-work-result.json").write_text(json.dumps(row)+"\n")
elif label == "paid-queue-assess":
    evidence=Path(args[args.index("--evidence-dir")+1]); expected=json.loads((evidence.parent/"paid-queue-expected.json").read_text()); ev=expected["delivery_evidence"]
    tid=str(expected["talkroom_id"]); artifact=Path(ev["artifact_path"]); digest=ev["package_sha256"]
    shot=evidence/"post.png"; shot.write_bytes(b"png"); live=evidence/"post.json"
    live.write_text(json.dumps({"url":f"https://coconala.com/talkrooms/{tid}","sent":True,"formal_delivery_checkbox":False,"latest_seller_attachment":{"filename":artifact.name,"size_bytes":artifact.stat().st_size,"message":f"v3 {digest}"}})+"\n")
    (evidence/"paid-queue-evidence.json").write_text(json.dumps({"sent":True,"formal_delivery_checkbox":False,"captured_at":"now","talkroom_id":tid,"artifact_basename":artifact.name,"artifact_version":ev["artifact_version"],"package_sha256":digest,"acceptance_delta":ev["acceptance_delta"],"screenshot_path":str(shot),"live_dom_path":str(live)})+"\n")
elif label == "B0":
    evidence=Path(args[args.index("--evidence-dir")+1]); evidence.mkdir(parents=True,exist_ok=True)
    context_path=evidence.parent/"b0-context.json"
    result=evidence/"attempt-01.result.json"
    result.write_text(json.dumps({
        "status":"ok","summary":"B0 fixture noop","evidence":["fresh storefront check"],
        "current_b0":{
            "context_path":str(context_path),
            "context_sha256":hashlib.sha256(context_path.read_bytes()).hexdigest(),
            "action":"verified_noop","service_id":None,"url":None,"title":None,
            "screenshot_path":None,"live_dom_path":None,"reason":"fixture noop"
        }
    })+"\n")
    (evidence/"summary.json").write_text(json.dumps({
        "status":"success","task_label":"gig-B0","result_path":str(result)
    })+"\n")
elif label == "B2":
    open(os.environ["GIG_TEST_CONTEXT_LOG"], "a").write("acquire gig-B2\n")
    evidence=Path(args[args.index("--evidence-dir")+1]); evidence.mkdir(parents=True,exist_ok=True)
    prompt=Path(args[args.index("--prompt-file")+1]).read_text()
    context_path=Path(prompt.split("context_path=",1)[1].split(" and context_sha256=",1)[0])
    context=json.loads(context_path.read_text())
    market_shot=evidence/"requests.png"; market_shot.write_bytes(b"png")
    market_dom=evidence/"requests.json"
    market_url="https://coconala.com/requests?sort=new"
    market_dom.write_text(json.dumps({"url":market_url,"not_found":False,"observed":True})+"\n")
    search_sources=[]
    for index,source_id in enumerate(context["required_search_source_ids"]):
        source_url=market_url if source_id=="single:new" else f"https://coconala.com/requests?source={index}"
        source_shot=evidence/f"search-{index}.png"; source_shot.write_bytes(b"png")
        source_dom=evidence/f"search-{index}.json"
        source_dom.write_text(json.dumps({"url":source_url,"not_found":False,"observed":True})+"\n")
        search_sources.append({"source_id":source_id,"url":source_url,
            "screenshot_path":str(source_shot),"live_dom_path":str(source_dom),
            "inspected_count":1,"has_next":False,"exhausted":True})
    request_id="5179999"
    proof=Path.home()/"gig/evidence"/f"gig-fixture-B2-{request_id}-submitted.png"
    proof.parent.mkdir(parents=True,exist_ok=True); proof.write_bytes(b"submitted")
    result=evidence/"attempt-01.result.json"
    result.write_text(json.dumps({
        "status":"ok","summary":"one fixture application","evidence":[str(market_dom)],
        "eligible_count":1,
        "applications":[{
            "request_id":request_id,"bucket":"single","category":"fixture","title":"fixture",
            "price_jpy":8000,"deliver_date":"2026-07-23",
            "url":f"https://coconala.com/requests/{request_id}"
        }],
        "current_b2":{
            "context_path":str(context_path),
            "context_sha256":hashlib.sha256(context_path.read_bytes()).hexdigest(),
            "marketplace_url":market_url,
            "marketplace_screenshot_path":str(market_shot),
            "marketplace_live_dom_path":str(market_dom),
            "inspected_requests":[{
                "request_id":request_id,"bucket":"single",
                "url":f"https://coconala.com/requests/{request_id}",
                "applicants":1,"contracted":0,"budget_max_jpy":10000,
                "accepting_applications":True,
                "outcome":"eligible","reason":None
            }],
            "search_sources":search_sources
        }
    })+"\n")
    (evidence/"summary.json").write_text(json.dumps({
        "status":"success","task_label":"gig-B2","result_path":str(result)
    })+"\n")
    action_map=Path.home()/"loops/gig/state/task-request-map.jsonl"
    action_map.parent.mkdir(parents=True,exist_ok=True)
    with action_map.open("a") as handle:
        handle.write(json.dumps({"pass_id":"fixture","requestId":request_id,"action":"applied"})+"\n")
elif label == "B1":
    evidence=Path(args[args.index("--evidence-dir")+1]); evidence.mkdir(parents=True,exist_ok=True)
    context_path=evidence.parent/"b1-context.json"; context=json.loads(context_path.read_text())
    inbox_shot=evidence/"inbox.png"; inbox_shot.write_bytes(b"png")
    inbox_dom=evidence/"inbox.json"; inbox_dom.write_text(json.dumps({"url":context["inbox_url"],"not_found":False,"observed":True})+"\n")
    inspected=[]
    for row in context["actionable_talkrooms"]:
        tid=row["talkroom_id"]; shot=evidence/f"room-{tid}.png"; shot.write_bytes(b"png")
        dom=evidence/f"room-{tid}.json"; dom.write_text(json.dumps({"url":row["url"],"not_found":False,"observed":True})+"\n")
        inspected.append({"talkroom_id":tid,"url":row["url"],"outcome":"observed_no_action","screenshot_path":str(shot),"live_dom_path":str(dom)})
    result=evidence/"attempt-01.result.json"
    result.write_text(json.dumps({"status":"ok","summary":"B1 fixture sweep","evidence":["fresh deterministic sweep"],"current_b1":{"context_path":str(context_path),"context_sha256":hashlib.sha256(context_path.read_bytes()).hexdigest(),"inbox_url":context["inbox_url"],"inbox_status":"ok","inbox_screenshot_path":str(inbox_shot),"inbox_live_dom_path":str(inbox_dom),"inspected_talkrooms":inspected}})+"\n")
    (evidence/"summary.json").write_text(json.dumps({"status":"success","task_label":"gig-B1","result_path":str(result)})+"\n")
elif label == "REFLECT":
    evidence=Path(args[args.index("--evidence-dir")+1]); evidence.mkdir(parents=True,exist_ok=True)
    current_pass=json.loads(os.environ["GIG_REFLECT_CONTEXT_JSON"])
    result=evidence/"attempt-01.result.json"
    result.write_text(json.dumps({"status":"ok","summary":"await fixture reflection","current_pass":current_pass,"evidence":["await reflection evidence"]})+"\n")
    (evidence/"summary.json").write_text(json.dumps({"status":"success","task_label":"gig-REFLECT","result_path":str(result)})+"\n")
raise SystemExit(0)
PY
cat > "$G/passprep.py" <<'PY'
import json
print(json.dumps({
    "max_apply_per_pass":4,
    "apply_skip_thresholds":{
        "max_applicants":12,
        "min_contracted_to_skip":1,
        "min_budget_jpy":3000
    }
}))
PY
cat > "$G/gig_funnel.py" <<'PY'
raise SystemExit(0)
PY
cat > "$G/scripts/gig_selfimprove_verify.sh" <<'SH'
#!/usr/bin/env bash
exit 0
SH
cat > "$G/scripts/cdp_nav_snapshot.py" <<'PY'
#!/usr/bin/env python3
raise SystemExit(0)
PY
cat > "$G/scripts/experiment_evaluator.py" <<'PY'
#!/usr/bin/env python3
raise SystemExit(0)
PY
chmod +x "$HOME_DIR/life-manager/runtime/agent-runner/agent_runner.py" "$G/scripts/gig_selfimprove_verify.sh"
mkdir -p "$HOME_DIR/life-manager/skills/browser/scripts"
cat > "$HOME_DIR/life-manager/skills/browser/scripts/cdp_context_lease.py" <<'PY'
#!/usr/bin/env python3
raise SystemExit(0)
PY
chmod +x "$HOME_DIR/life-manager/skills/browser/scripts/cdp_context_lease.py"
cat > "$TMP/fake-validation-docker" <<'SH'
#!/usr/bin/env bash
printf '%s\n' '{"status":"PASS"}'
SH
chmod +x "$TMP/fake-validation-docker"
export GIG_PAID_VALIDATOR_DOCKER="$TMP/fake-validation-docker"
cat > "$TMP/fake-paid-progress" <<'PY'
#!/usr/bin/env python3
import os
open(os.environ["GIG_TEST_PROGRESS_LOG"], "a", encoding="utf-8").write("deterministic-paid-progress\n")
raise SystemExit(42)
PY
chmod +x "$TMP/fake-paid-progress"

applied_before=$(shasum -a 256 "$HOME_DIR/gig/applied.jsonl" | awk '{print $1}')
action_map_before=$(shasum -a 256 "$HOME_DIR/loops/gig/state/task-request-map.jsonl" | awk '{print $1}')
: > "$TMP/runner.log"
: > "$TMP/context.log"
printf '%s\n' '{"source":"code_owned_cdp_readback","url":"https://coconala.com/mypage/job_matching/applied/offers","observed":true,"not_found":false,"request_ids":["5179999"],"offers":[{"request_id":"5179999","offer_url":"https://coconala.com/mypage/offers/1","title":"fixture"}]}' > "$TMP/b2-readback.json"
HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/snapshot.json" \
  GIG_B2_READBACK_FIXTURE="$TMP/b2-readback.json" \
  GIG_TODAY=2026-07-22 GIG_LOCK_DIR="$TMP/lock.d" GIG_TEST_RUNNER_LOG="$TMP/runner.log" \
  GIG_TEST_CONTEXT_LOG="$TMP/context.log" \
  bash "$G/gig_pass.sh" >"$TMP/out" 2>"$TMP/err" || {
    echo 'await-buyer fixture pass failed' >&2
    cat "$TMP/err" >&2
    exit 1
  }

! grep -q '^gig-paid-queue-assess$' "$TMP/runner.log" || { echo 'duplicate progress worker ran'; exit 1; }
for revenue_label in B0 B1 B2; do
  test "$(grep -c "^gig-${revenue_label}$" "$TMP/runner.log")" -eq 1 || {
    echo "await-buyer starved hourly revenue lane $revenue_label: $(tr '\n' ',' < "$TMP/runner.log")"
    exit 1
  }
done
grep -q 'gig-B2' "$TMP/context.log" || { echo 'B2 browser context was not acquired after await-buyer poll'; exit 1; }
test "$(shasum -a 256 "$HOME_DIR/gig/applied.jsonl" | awk '{print $1}')" != "$applied_before" || { echo 'B2 did not append its verified fixture application'; exit 1; }
test "$(shasum -a 256 "$HOME_DIR/loops/gig/state/task-request-map.jsonl" | awk '{print $1}')" != "$action_map_before" || { echo 'B2 did not append its verified fixture action map'; exit 1; }
grep -q 'awaiting buyer; live state polled without mutation' "$TMP/err"
grep -q 'queue top class=other_paid_work id=17943244 ' "$TMP/err" || { echo 'queue log did not use stable talkroom identity'; exit 1; }
test -f "$HOME_DIR/gig/.last-pass" || { echo 'successful poll heartbeat missing'; exit 1; }
python3 - "$HOME_DIR/gig/projects/17943244/state.json" "$HOME_DIR/gig/pass-report.jsonl" \
  "$TMP/home/gig/.last-pass" "$TMP/home/gig/evidence" <<'PY'
import json,sys
state=json.load(open(sys.argv[1]))
assert state["next_action"] == "await_buyer_approval_for_publication"
assert state["source_contract_id"] == "direct-offer:6198868"
report=[json.loads(line) for line in open(sys.argv[2]) if line.strip()][-1]
assert report["steps_executed"] == ["B0", "PROFILE", "B1", "B2", "LEARN", "REFLECT"], report
assert all(not row.startswith(("B0:", "B1:", "B2:")) for row in report["steps_skipped_policy"]), report
assert json.load(open(sys.argv[3])) == report
PY

# With no unresolved paid/feedback/proposal queue item, B2 remains enabled.
printf '%s\n' '{"captured_at":"2026-07-22T03:27:17+00:00","inbox":{"url":"https://coconala.com/message?fromMyPage=true","not_found":false},"orders":[],"quotes":[],"inquiries":[]}' > "$TMP/clear-snapshot.json"
: > "$TMP/runner.log"
: > "$TMP/context.log"
applied_before_clear=$(shasum -a 256 "$HOME_DIR/gig/applied.jsonl" | awk '{print $1}')
action_map_before_clear=$(shasum -a 256 "$HOME_DIR/loops/gig/state/task-request-map.jsonl" | awk '{print $1}')
HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/clear-snapshot.json" \
  GIG_B2_READBACK_FIXTURE="$TMP/b2-readback.json" \
  GIG_TODAY=2026-07-22 GIG_LOCK_DIR="$TMP/clear-lock.d" GIG_TEST_RUNNER_LOG="$TMP/runner.log" \
  GIG_TEST_CONTEXT_LOG="$TMP/context.log" GIG_PASS_ID="queue-clear" \
  bash "$G/gig_pass.sh" >"$TMP/clear-out" 2>"$TMP/clear-err"
! grep -q '^gig-B0$\|^gig-B1$\|^gig-B2$' "$TMP/runner.log" || { echo 'clear same-hour poll repeated a revenue lane'; exit 1; }
test ! -s "$TMP/context.log" || { echo 'clear no-event poll acquired a browser context'; exit 1; }
test "$(shasum -a 256 "$HOME_DIR/gig/applied.jsonl" | awk '{print $1}')" = "$applied_before_clear" || { echo 'clear no-event poll mutated applied ledger'; exit 1; }
test "$(shasum -a 256 "$HOME_DIR/loops/gig/state/task-request-map.jsonl" | awk '{print $1}')" = "$action_map_before_clear" || { echo 'clear no-event poll mutated action map'; exit 1; }

# Any later buyer-authored reply reopens the paid workflow, even when its text
# does not match a hand-maintained keyword list.
python3 - "$TMP/snapshot.json" <<'PY'
import json,sys
path=sys.argv[1]
snapshot=json.load(open(path))
snapshot["orders"][0]["buyer_reply_after_artifact_observed"] = True
open(path,"w").write(json.dumps(snapshot)+"\n")
PY
: > "$TMP/runner.log"
: > "$TMP/progress.log"
set +e
HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/snapshot.json" \
  GIG_B2_READBACK_FIXTURE="$TMP/b2-readback.json" \
  GIG_TODAY=2026-07-22 GIG_LOCK_DIR="$TMP/reply-lock.d" GIG_TEST_CDP_ALIVE=1 GIG_TEST_RUNNER_LOG="$TMP/runner.log" \
  GIG_TEST_CONTEXT_LOG="$TMP/context.log" GIG_TEST_PROGRESS_LOG="$TMP/progress.log" \
  GIG_PAID_PROGRESS_BROWSER="$TMP/fake-paid-progress" \
  GIG_PASS_ID="buyer-replied" bash "$G/gig_pass.sh" >"$TMP/reply-out" 2>"$TMP/reply-err"
reply_rc=$?
set -e
test "$reply_rc" -ne 0 || { echo 'buyer reply with incomplete formal gates should remain pending'; exit 1; }
test "$(cat "$TMP/progress.log")" = "deterministic-paid-progress" || { echo 'buyer reply did not reopen paid workflow'; exit 1; }
! grep -q '^gig-paid-queue-assess$' "$TMP/runner.log" || { echo 'buyer reply used the deprecated model-driven progress path'; exit 1; }

# An unreadable/invalid deterministic gate result is a pass failure, never an
# implicit permission to start B2.
cat > "$G/scripts/b2_queue_gate.py" <<'PY'
raise SystemExit(2)
PY
: > "$TMP/runner.log"
reports_before_invalid=$(wc -l < "$HOME_DIR/gig/pass-report.jsonl")
set +e
HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/clear-snapshot.json" \
  GIG_B2_READBACK_FIXTURE="$TMP/b2-readback.json" \
  GIG_TODAY=2026-07-22 GIG_LOCK_DIR="$TMP/invalid-lock.d" GIG_TEST_RUNNER_LOG="$TMP/runner.log" \
  GIG_TEST_CONTEXT_LOG="$TMP/context.log" GIG_PASS_ID="invalid-b2-gate" \
  GIG_LEGACY_MAINTENANCE_ENABLED=1 GIG_MODEL_CALL_LIMIT=0 \
  bash "$G/gig_pass.sh" >"$TMP/invalid-out" 2>"$TMP/invalid-err"
invalid_rc=$?
set -e
test "$invalid_rc" -ne 0 || { echo 'invalid B2 queue gate failed open'; exit 1; }
! grep -q '^gig-B2$' "$TMP/runner.log" || { echo 'B2 runner started after invalid gate result'; exit 1; }
grep -q 'b2_queue_gate_invalid' "$HOME_DIR/gig/pass-failures.jsonl" || { echo 'invalid B2 queue gate failure was not durable'; exit 1; }
test "$(wc -l < "$HOME_DIR/gig/pass-report.jsonl")" -eq "$reports_before_invalid" || { echo 'invalid B2 queue gate wrote a success report'; exit 1; }

echo 'PASS: awaiting-buyer contract is polled once and any newer buyer reply reopens work'
