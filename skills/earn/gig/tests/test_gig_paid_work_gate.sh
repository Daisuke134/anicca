#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d /tmp/gig-paid-work-gate.XXXXXX)
trap 'rm -rf "$TMP"' EXIT
HOME_DIR="$TMP/home"
G="$HOME_DIR/profitable-claude/skills/gig-work"
mkdir -p "$HOME_DIR/gig" "$G/scripts" "$G/schemas" "$G/config/connectors" "$HOME_DIR/profitable-claude/skills/agent-runner" "$HOME_DIR/profitable-claude/lib"
for file in gig_pass.sh passprep.py strategy.default.json; do cp "$SKILL_DIR/$file" "$G/$file"; done
for file in delivery_queue.py delivery_cadence.py delivery_project.py project_ledger.py delivery_identity.py paid_work_evidence.py paid_work_transaction.py paid_work_validation_contract.py paid_queue_evidence.py reply_queue.py connector_outbox.py reconcile_paid_delivery.py paid_progress_ledger.py paid_progress_finalize_gate.py cdp_lock.sh run_with_cdp_lock.sh coconala_paid_progress_browser.py sync_gig_revenue_events.py gig_context_packet.py b1_conversation_gate.py b0_objective.py b0_result_gate.py b2_queue_gate.py b2_result_gate.py application_report.py normalize_applied.py lane_health.py lane_state_machine.py lane_action_runtime.py lane_productivity.py listing_ledger.py; do cp "$SKILL_DIR/scripts/$file" "$G/scripts/$file"; done
# The self-improvement verifier is a downstream integration owned by another test.
# This fixture isolates the paid gate and real lane selector; it must not fail merely
# because it does not build the full self-improvement evidence tree.
printf '%s\n' '#!/usr/bin/env bash' 'exit 0' > "$G/scripts/gig_selfimprove_verify.sh"
chmod +x "$G/scripts/gig_selfimprove_verify.sh"
cp "$SKILL_DIR/../agent-runner/context_packet.py" "$HOME_DIR/profitable-claude/skills/agent-runner/context_packet.py"
cp "$SKILL_DIR/../../lib/unit_economics_events.py" "$HOME_DIR/profitable-claude/lib/unit_economics_events.py"
cp "$SKILL_DIR/config/connectors/coconala.json" "$G/config/connectors/coconala.json"
chmod +x "$G/scripts/run_with_cdp_lock.sh"
cp "$SKILL_DIR/schemas/gig_step_result.schema.json" "$G/schemas/gig_step_result.schema.json"
cp "$SKILL_DIR/schemas/gig_b0_result.schema.json" "$G/schemas/gig_b0_result.schema.json"
cp "$SKILL_DIR/schemas/gig_reflect_result.schema.json" "$G/schemas/gig_reflect_result.schema.json"
cp "$SKILL_DIR/schemas/gig_b1_result.schema.json" "$G/schemas/gig_b1_result.schema.json"
cp "$SKILL_DIR/schemas/gig_b2_result.schema.json" "$G/schemas/gig_b2_result.schema.json"
cat > "$TMP/snapshot.json" <<'JSON'
{
  "source": "authenticated_coconala_default_context_dom",
  "captured_at": "2026-07-22T08:00:00+00:00",
  "inbox": {
    "url": "https://coconala.com/message?fromMyPage=true",
    "not_found": false,
    "observed": true
  },
  "orders": [{
    "contract_id": "direct-offer:generic-42", "talkroom_id": "4201",
    "buyer": "generic", "title": "generic returned work", "status": "paid",
    "price_jpy": 17000, "delivery_date": "2026-08-01", "talkroom_state": "取引中",
    "buyer_feedback_pending_artifact": true, "buyer_visible_artifact_observed": false,
    "formal_delivery_observed": false
  }],
  "quotes": [], "inquiries": []
}
JSON
cat > "$HOME_DIR/profitable-claude/skills/agent-runner/agent_runner.py" <<'PY'
#!/usr/bin/env python3
import hashlib, json, os, sys, time
from pathlib import Path
args = sys.argv[1:]
label = args[args.index("--task-label") + 1]
evidence = Path(args[args.index("--evidence-dir") + 1]); evidence.mkdir(parents=True, exist_ok=True)
prompt = Path(args[args.index("--prompt-file") + 1]).read_text(encoding="utf-8")
workdir = Path(args[args.index("--workdir") + 1])
mode = os.environ.get("GIG_TEST_PAID_MODE", "green")
Path(os.environ["GIG_TEST_RUNNER_LOG"]).open("a", encoding="utf-8").write(label + "\n")
if label == "gig-PAID_WORK":
    if os.environ.get("ANICCA_BUDGET_SCOPE_ID") != os.environ.get("GIG_PASS_ID"):
        raise SystemExit(46)
    if os.environ.get("ANICCA_PASS_TOKEN_BUDGET") != "1048576":
        raise SystemExit(48)
    if os.environ.get("ANICCA_LOOP_DAILY_TOKEN_BUDGET") != "8388608":
        raise SystemExit(49)
    if '"kind":"gig_paid_work"' not in prompt or '"max_bytes":8192' not in prompt:
        raise SystemExit(44)
    if "generic returned work" in prompt:
        raise SystemExit(45)
    if "permitted outside write" in prompt or "Exact delivery evidence path" in prompt:
        raise SystemExit(43)
    if mode == "no-root-prompt" and "Stable project root:" not in prompt:
        raise SystemExit(41)
    if mode == "text-only":
        raise SystemExit(0)
    if mode == "green-existing":
        raise SystemExit(41)
    if mode == "answer":
        (workdir / "delivery").mkdir(parents=True, exist_ok=True)
        (workdir / "requirements" / "live-buyer-reply.json").write_text(json.dumps({
            "observed_at":"2026-07-22T08:02:00+00:00",
            "feedback_sha256":"b" * 64
        }) + "\n")
        (workdir / "delivery" / "paid-answer.json").write_text(json.dumps({
            "version":1,
            "status":"answer",
            "message":"確認事項に回答します。次の作業へ進められる状態です。"
        }) + "\n")
        raise SystemExit(0)
    for name in ("requirements", "source", "work", "artifacts", "acceptance", "delivery", "evidence"):
        (workdir / name).mkdir(parents=True, exist_ok=True)
    req = workdir / "requirements" / "latest-feedback.json"; req.write_text('{"feedback":"revision"}\n')
    artifact = workdir / "artifacts" / "delivery-v3.zip"; artifact.write_bytes(b"v3 artifact")
    acceptance = workdir / "acceptance" / "v3.json"; acceptance.write_text('{"status":"PASS","acceptance_delta":["revision"]}\n')
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    row = {"status":"ok", "project_root":str(workdir), "requirements_path":str(req),
           "artifact_path":str(artifact), "artifact_version":"v3",
           "acceptance_evidence_path":str(acceptance), "acceptance_status":"PASS",
           "acceptance_delta":["revision"], "package_sha256":digest}
    if mode == "invalid":
        row["project_root"] = str(workdir.parent / "other")
    (workdir / "delivery" / "paid-work-result.json").write_text(json.dumps(row)+"\n")
    if mode == "runner-nonzero-after-exec":
        raise SystemExit(47)
    if mode == "stale-text-only":
        # Simulate a builder that exits successfully without updating the
        # previously valid suite for the current buyer-feedback pass.
        stale = 1
        for path in (req, artifact, acceptance, workdir / "delivery" / "paid-work-result.json"):
            os.utime(path, (stale, stale))
        raise SystemExit(0)
elif label == "gig-paid-queue-assess":
    expected = json.loads((Path(os.environ["GIG_EVIDENCE_DIR"]) / "paid-queue-expected.json").read_text())
    tid = str(expected.get("talkroom_id")); url = f"https://coconala.com/talkrooms/{tid}"
    if mode == "browser-fail":
        raise SystemExit(42)
    if mode not in ("green", "green-existing"):
        raise SystemExit(0)
    (evidence / "agent-browser-list.json").write_text("[]\n")
    shot = evidence / "post.png"; shot.write_bytes(b"png")
    ev = expected.get("delivery_evidence", {})
    artifact = Path(ev["artifact_path"]); digest = ev["package_sha256"]
    live = evidence / "post.json"
    live.write_text(json.dumps({"url":url,"sent":True,"formal_delivery_checkbox":False,"latest_seller_attachment":{
        "filename":artifact.name,"size_bytes":artifact.stat().st_size,"message":f"{ev['artifact_version']} {digest}"}})+"\n")
    (evidence / "paid-queue-evidence.json").write_text(json.dumps({
        "sent":True,"formal_delivery_checkbox":False,"captured_at":"2026-07-22T08:01:00Z",
        "talkroom_id":tid,"artifact_basename":artifact.name,"artifact_version":ev["artifact_version"],
        "package_sha256":digest,"acceptance_delta":ev["acceptance_delta"],
        "screenshot_path":str(shot),"live_dom_path":str(live)})+"\n")
elif label == "gig-B0":
    context_path = Path(prompt.split("context_path=", 1)[1].split(" and context_sha256=", 1)[0])
    service_id = "9000001"
    url = f"https://coconala.com/services/{service_id}"
    shot = evidence / "listing.png"; shot.write_bytes(b"png")
    dom = evidence / "listing.json"
    dom.write_text(json.dumps({
        "url":url,"not_found":False,"observed":True,"title":"Fixture listing"
    })+"\n")
    result = evidence / "attempt-01.result.json"
    result.write_text(json.dumps({
        "status":"ok","summary":"published fixture listing","evidence":[str(dom)],
        "current_b0":{
            "context_path":str(context_path),
            "context_sha256":hashlib.sha256(context_path.read_bytes()).hexdigest(),
            "action":"published","service_id":service_id,"url":url,
            "title":"Fixture listing","screenshot_path":str(shot),
            "live_dom_path":str(dom),"reason":"fixture publication"
        }
    })+"\n")
    (evidence / "summary.json").write_text(json.dumps({
        "status":"success","task_label":label,"result_path":str(result)
    })+"\n")
    raise SystemExit(0)
elif label == "gig-B1":
    context_path = Path(prompt.split("context_path=", 1)[1].split(" and context_sha256=", 1)[0])
    context = json.loads(context_path.read_text(encoding="utf-8"))
    inbox_shot = evidence / "inbox.png"; inbox_shot.write_bytes(b"png")
    inbox_dom = evidence / "inbox.json"
    inbox_dom.write_text(json.dumps({
        "url":"https://coconala.com/message?fromMyPage=true",
        "not_found":False,"observed":True
    })+"\n")
    inspected = []
    for row in context.get("actionable_talkrooms", []):
        tid = str(row["talkroom_id"])
        shot = evidence / f"talkroom-{tid}.png"; shot.write_bytes(b"png")
        live = evidence / f"talkroom-{tid}.json"
        live.write_text(json.dumps({
            "url":row["url"],"not_found":False,"observed":True
        })+"\n")
        inspected.append({
            "talkroom_id":tid,"url":row["url"],"outcome":"observed_no_action",
            "screenshot_path":str(shot),"live_dom_path":str(live)
        })
    result = evidence / "attempt-01.result.json"
    result.write_text(json.dumps({
        "status":"ok","summary":"hourly reply lane inspected",
        "evidence":[str(inbox_dom)],
        "current_b1":{
            "context_path":str(context_path),
            "context_sha256":hashlib.sha256(context_path.read_bytes()).hexdigest(),
            "inbox_url":"https://coconala.com/message?fromMyPage=true",
            "inbox_status":"ok",
            "inbox_screenshot_path":str(inbox_shot),
            "inbox_live_dom_path":str(inbox_dom),
            "inspected_talkrooms":inspected
        }
    })+"\n")
    (evidence / "summary.json").write_text(json.dumps({
        "status":"success","task_label":label,"result_path":str(result)
    })+"\n")
    raise SystemExit(0)
elif label == "gig-B2":
    context_path = Path(prompt.split("context_path=", 1)[1].split(" and context_sha256=", 1)[0])
    context = json.loads(context_path.read_text(encoding="utf-8"))
    dom = evidence / "jobs.json"
    dom.write_text(json.dumps({
        "url":"https://coconala.com/job_matching/requests",
        "not_found":False,"observed":True,"eligible_count":0
    })+"\n")
    shot = evidence / "jobs.png"
    shot.write_bytes(b"fresh marketplace screenshot")
    search_sources = []
    for index, source_id in enumerate(context["required_search_source_ids"]):
        source_url = "https://coconala.com/job_matching/requests" if source_id == "single:new" else f"https://coconala.com/requests?source={index}"
        source_shot = evidence / f"search-{index}.png"; source_shot.write_bytes(b"png")
        source_dom = evidence / f"search-{index}.json"
        source_dom.write_text(json.dumps({"url":source_url,"not_found":False,"observed":True})+"\n")
        search_sources.append({"source_id":source_id,"url":source_url,
            "screenshot_path":str(source_shot),"live_dom_path":str(source_dom),
            "inspected_count":1,"has_next":False,"exhausted":True})
    inspected = [{
        "request_id":"5179838",
        "url":"https://coconala.com/requests/5179838",
        "applicants":29,
        "contracted":0,
        "budget_max_jpy":100000,
        "outcome":"ineligible",
        "reason":"applicants exceed frozen threshold"
    }]
    if mode == "b2-invalid":
        inspected[0]["outcome"] = "eligible"
    result = evidence / "attempt-01.result.json"
    result.write_text(json.dumps({
        "status":"ok","summary":"no eligible new jobs",
        "evidence":[str(dom)],
        "eligible_count":1 if mode == "b2-invalid" else 0,
        "applications":[],
        "current_b2":{
            "context_path":str(context_path),
            "context_sha256":hashlib.sha256(context_path.read_bytes()).hexdigest(),
            "marketplace_url":"https://coconala.com/job_matching/requests",
            "marketplace_screenshot_path":str(shot),
            "marketplace_live_dom_path":str(dom),
            "inspected_requests":inspected,
            "search_sources":search_sources
        }
    })+"\n")
    (evidence / "summary.json").write_text(json.dumps({
        "status":"success","task_label":label,"result_path":str(result)
    })+"\n")
    raise SystemExit(0)
elif label == "gig-REFLECT":
    current_pass = json.loads(os.environ["GIG_REFLECT_CONTEXT_JSON"])
    result = evidence / "attempt-01.result.json"
    result.write_text(json.dumps({"status":"ok","summary":"validated progress remains formal pending",
        "evidence":["queue-bound progress evidence"],"current_pass":current_pass})+"\n")
    (evidence / "summary.json").write_text(json.dumps({"status":"success","task_label":label,
        "result_path":str(result)})+"\n")
    raise SystemExit(0)
(evidence / "summary.json").write_text(json.dumps({"status":"success","task_label":label})+"\n")
raise SystemExit(0)
PY
chmod +x "$HOME_DIR/profitable-claude/skills/agent-runner/agent_runner.py"
cat > "$TMP/fake-paid-progress" <<'PY'
#!/usr/bin/env python3
import argparse, json, os, sys
import hashlib
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--queue-item", required=True, type=Path)
parser.add_argument("--manifest", type=Path)
parser.add_argument("--answer-file", type=Path)
parser.add_argument("--evidence-dir", required=True, type=Path)
parser.add_argument("--default-tab-helper", required=True, type=Path)
args = parser.parse_args()
Path(os.environ["GIG_TEST_BROWSER_LOG"]).open("a", encoding="utf-8").write("deterministic-paid-progress\n")
mode = os.environ.get("GIG_TEST_PAID_MODE", "green")
if mode == "browser-fail":
    raise SystemExit(42)
if mode not in ("green", "green-existing", "answer"):
    raise SystemExit(43)
expected = json.loads(args.queue_item.read_text(encoding="utf-8"))
manifest = (
    json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.manifest else expected["delivery_evidence"]
)
tid = str(expected["talkroom_id"])
url = f"https://coconala.com/talkrooms/{tid}"
args.evidence_dir.mkdir(parents=True, exist_ok=True)
shot = args.evidence_dir / "post.png"; shot.write_bytes(b"png")
if args.answer_file:
    answer = json.loads(args.answer_file.read_text(encoding="utf-8"))
    message = answer["message"]
    live = args.evidence_dir / "post.json"
    live.write_text(json.dumps({
        "url":url,"sent":True,"mode":"answer","send_performed":True,
        "formal_delivery_control_checked":False,
        "latest_seller_message":message,
    })+"\n")
    (args.evidence_dir / "paid-queue-evidence.json").write_text(json.dumps({
        "sent":True,"mode":"answer","send_performed":True,"deduplicated":False,
        "formal_delivery_checkbox":False,"captured_at":"2026-07-22T08:01:00Z",
        "talkroom_id":tid,"message_sha256":hashlib.sha256(message.encode()).hexdigest(),
        "screenshot_path":str(shot),"live_dom_path":str(live),
    })+"\n")
    raise SystemExit(0)
artifact = Path(manifest["artifact_path"]); digest = manifest["package_sha256"]
live = args.evidence_dir / "post.json"
live.write_text(json.dumps({"url":url,"sent":True,"formal_delivery_checkbox":False,"latest_seller_attachment":{
    "filename":artifact.name,"size_bytes":artifact.stat().st_size,"message":f"{manifest['artifact_version']} {digest}"}})+"\n")
(args.evidence_dir / "paid-queue-evidence.json").write_text(json.dumps({
    "sent":True,"send_performed":True,"formal_delivery_checkbox":False,"captured_at":"2026-07-22T08:01:00Z",
    "talkroom_id":tid,"artifact_basename":artifact.name,"artifact_version":manifest["artifact_version"],
    "package_sha256":digest,"acceptance_delta":manifest["acceptance_delta"],
    "screenshot_path":str(shot),"live_dom_path":str(live)})+"\n")
PY
chmod +x "$TMP/fake-paid-progress"
cat > "$TMP/fake-validation-docker" <<'SH'
#!/usr/bin/env bash
printf '%s\n' '{"status":"PASS"}'
SH
chmod +x "$TMP/fake-validation-docker"
export GIG_PAID_VALIDATOR_DOCKER="$TMP/fake-validation-docker"

install_validation_contract() {
  local project_root="$1"
  mkdir -p "$project_root/source" "$project_root/delivery"
  cat > "$project_root/source/validate_fixture_artifact.py" <<'PY'
import json, sys
from pathlib import Path
artifact = Path(sys.argv[1])
assert artifact.is_file()
assert artifact.read_bytes() == b"v3 artifact"
print(json.dumps({"status": "PASS"}))
PY
  cat > "$project_root/delivery/validation-contract.json" <<'JSON'
{
  "version": 1,
  "artifact": {
    "type": "file",
    "min_size_bytes": 8,
    "allowed_suffixes": [".zip"]
  },
  "trusted_files": ["source/validate_fixture_artifact.py"],
  "commands": [
    {
      "id": "fixture-domain",
      "kind": "domain",
      "argv": ["python3", "source/validate_fixture_artifact.py", "{artifact_path}"],
      "timeout_seconds": 30,
      "expect_stdout_json": {"status": "PASS"}
    },
    {
      "id": "fixture-regression",
      "kind": "test",
      "argv": ["python3", "source/validate_fixture_artifact.py", "{artifact_path}"],
      "timeout_seconds": 30,
      "expect_stdout_json": {"status": "PASS"}
    }
  ]
}
JSON
}

install_validation_contract "$HOME_DIR/gig/projects/4201"
RECOVERY_HOME_DIR="$TMP/recovery-home"
mkdir -p "$RECOVERY_HOME_DIR/profitable-claude"
cp -R "$HOME_DIR/profitable-claude/." "$RECOVERY_HOME_DIR/profitable-claude/"
mkdir -p "$RECOVERY_HOME_DIR/gig" "$RECOVERY_HOME_DIR/loops/gig/state"
install_validation_contract "$RECOVERY_HOME_DIR/gig/projects/4201"
cp "$G/strategy.default.json" "$RECOVERY_HOME_DIR/gig/strategy.json"
printf '%s\n' '{"requestId":"recovery-existing","status":"applied"}' > "$RECOVERY_HOME_DIR/gig/applied.jsonl"
printf '%s\n' '{"pass_id":"recovery-existing","requestId":"recovery-existing","action":"applied"}' > "$RECOVERY_HOME_DIR/loops/gig/state/task-request-map.jsonl"
printf '%s\n' '{"service_id":"recovery-existing","status":"published"}' > "$RECOVERY_HOME_DIR/gig/shuppin.jsonl"
printf '%s\n' '{"requestId":"recovery-existing","outcome":"accepted"}' > "$RECOVERY_HOME_DIR/gig/shared-lessons.jsonl"
printf '%s\n' '{"status":"recovery-seed"}' > "$RECOVERY_HOME_DIR/gig/playbook.json"
printf '%s\n' '{"pass_id":"recovery-existing","applied":1}' > "$RECOVERY_HOME_DIR/gig/gig-funnel.jsonl"
printf '%s\n' '{"ts":1784707200,"requestId":"recovery-settled","status":"SETTLED","jpy":1,"evidence":"existing"}' > "$RECOVERY_HOME_DIR/gig/earnings.jsonl"
recovery_lower_paths=("$RECOVERY_HOME_DIR/gig/strategy.json" "$RECOVERY_HOME_DIR/gig/applied.jsonl" \
  "$RECOVERY_HOME_DIR/loops/gig/state/task-request-map.jsonl" "$RECOVERY_HOME_DIR/gig/shuppin.jsonl" \
  "$RECOVERY_HOME_DIR/gig/shared-lessons.jsonl" "$RECOVERY_HOME_DIR/gig/playbook.json" \
  "$RECOVERY_HOME_DIR/gig/gig-funnel.jsonl" "$RECOVERY_HOME_DIR/gig/earnings.jsonl")
recovery_lower_before=$(shasum -a 256 "${recovery_lower_paths[@]}")

run_case() {
  local mode="$1" expected="$2" snapshot="${3:-$TMP/snapshot.json}"; : > "$TMP/runner.log"; : > "$TMP/browser.log"
  set +e
  HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$snapshot" \
    GIG_TODAY=2026-07-22 GIG_LOCK_DIR="$TMP/lock-$mode.d" GIG_EVIDENCE_DIR="$TMP/evidence-$mode" \
    GIG_TEST_CDP_ALIVE=1 GIG_TEST_PAID_MODE="$mode" GIG_TEST_RUNNER_LOG="$TMP/runner.log" \
    GIG_TEST_BROWSER_LOG="$TMP/browser.log" GIG_PAID_PROGRESS_BROWSER="$TMP/fake-paid-progress" \
    ANICCA_UNIT_ECONOMICS_LEDGER="$TMP/economics.jsonl" \
    GIG_PASS_ID="paid-$mode" \
    bash "$G/gig_pass.sh" >"$TMP/out-$mode" 2>"$TMP/err-$mode"
  local rc=$?; set -e
  if [ "$rc" -ne "$expected" ]; then
    tail -40 "$TMP/out-$mode" "$TMP/err-$mode"
  fi
  test "$rc" -eq "$expected"
}

# Invalid/text-only builder output fails closed before any browser send.
run_case invalid 1
test "$(cat "$TMP/runner.log")" = "gig-PAID_WORK"
grep -q 'paid_work_validation_failed' "$HOME_DIR/gig/pass-failures.jsonl"
run_case text-only 1
grep -q 'paid_work_validation_failed' "$HOME_DIR/gig/pass-failures.jsonl"
run_case runner-nonzero-after-exec 1
grep -q 'paid_work_builder_failed' "$HOME_DIR/gig/pass-failures.jsonl"
python3 - "$TMP/evidence-runner-nonzero-after-exec/paid-work-transaction.json" <<'PY'
import json, sys
row = json.load(open(sys.argv[1], encoding="utf-8"))
assert row["status"] == "rolled_back", row
assert row["failure_reason"] == "runner_nonzero", row
assert {item["kind"] for item in row["quarantined"]} == {"artifact", "acceptance", "requirements"}, row
PY

# A text-only success must not reuse a previously valid but stale vN suite.
run_case stale-text-only 1
grep -q 'paid_work_validation_failed' "$HOME_DIR/gig/pass-failures.jsonl"
test "$(cat "$TMP/runner.log")" = "gig-PAID_WORK"
! grep -q 'gig-paid-queue-assess' "$TMP/runner.log"

# A schema-valid B2 result is not a successful application check when it violates
# the frozen threshold and reports one eligible request but no application.
cat > "$TMP/clear-snapshot.json" <<'JSON'
{"captured_at":"2026-07-22T08:00:00+00:00","inbox":{"url":"https://coconala.com/message?fromMyPage=true","not_found":false,"observed":true},"orders":[],"quotes":[],"inquiries":[]}
JSON
B2_HOME_DIR="$TMP/b2-home"
mkdir -p "$B2_HOME_DIR"
cp -R "$HOME_DIR/." "$B2_HOME_DIR/"
: > "$TMP/b2-runner.log"
: > "$TMP/b2-browser.log"
set +e
HOME="$B2_HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/clear-snapshot.json" \
  GIG_TODAY=2026-07-22 GIG_LOCK_DIR="$TMP/b2-lock.d" GIG_EVIDENCE_DIR="$TMP/b2-evidence" \
  GIG_TEST_CDP_ALIVE=1 GIG_TEST_PAID_MODE=b2-invalid GIG_TEST_RUNNER_LOG="$TMP/b2-runner.log" \
  GIG_TEST_BROWSER_LOG="$TMP/b2-browser.log" GIG_PAID_PROGRESS_BROWSER="$TMP/fake-paid-progress" \
  ANICCA_UNIT_ECONOMICS_LEDGER="$TMP/b2-economics.jsonl" GIG_PASS_ID="paid-b2-invalid" \
  bash "$B2_HOME_DIR/profitable-claude/skills/gig-work/gig_pass.sh" \
  >"$TMP/b2-out" 2>"$TMP/b2-err"
b2_rc=$?
set -e
test "$b2_rc" -ne 0
grep -q 'b2_result_evidence_failed' "$B2_HOME_DIR/gig/pass-failures.jsonl"
test ! -f "$B2_HOME_DIR/gig/.last-pass"

# A queue-bound buyer-visible progress send is a successful bounded action, while
# formal completion remains pending. It runs first but must not terminate the
# hourly revenue sweep: B0/B1/B2 still consume the three remaining model-call
# slots and close listing/reply/application in this same pass.
mkdir -p "$HOME_DIR/loops/gig/state"
cp "$G/strategy.default.json" "$HOME_DIR/gig/strategy.json"
printf '%s\n' '{"requestId":"existing","status":"applied"}' > "$HOME_DIR/gig/applied.jsonl"
printf '%s\n' '{"pass_id":"existing","requestId":"existing","action":"applied"}' > "$HOME_DIR/loops/gig/state/task-request-map.jsonl"
printf '%s\n' '{"service_id":"existing","status":"published"}' > "$HOME_DIR/gig/shuppin.jsonl"
printf '%s\n' '{"requestId":"existing","outcome":"accepted"}' > "$HOME_DIR/gig/shared-lessons.jsonl"
printf '%s\n' '{"status":"seed"}' > "$HOME_DIR/gig/playbook.json"
printf '%s\n' '{"pass_id":"existing","applied":1}' > "$HOME_DIR/gig/gig-funnel.jsonl"
printf '%s\n' '{"ts":1784707200,"requestId":"settled-1","status":"SETTLED","jpy":1,"evidence":"existing"}' > "$HOME_DIR/gig/earnings.jsonl"
lower_paths=("$HOME_DIR/gig/strategy.json" "$HOME_DIR/gig/applied.jsonl" \
  "$HOME_DIR/loops/gig/state/task-request-map.jsonl" "$HOME_DIR/gig/shuppin.jsonl" \
  "$HOME_DIR/gig/shared-lessons.jsonl" "$HOME_DIR/gig/playbook.json" \
  "$HOME_DIR/gig/gig-funnel.jsonl" "$HOME_DIR/gig/earnings.jsonl")
lower_before=$(shasum -a 256 "${lower_paths[@]}")
mkdir -p "$HOME_DIR/gig/projects/4201/requirements"
cat > "$HOME_DIR/gig/projects/4201/requirements/live-buyer-reply.json" <<'JSON'
{"observed_at":"2020-01-01T00:00:00+00:00","feedback_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}
JSON
python3 - "$TMP/snapshot.json" "$HOME_DIR/gig/projects/4201/requirements/live-buyer-reply.json" <<'PY'
import json, sys
path, requirements = sys.argv[1:]
snapshot = json.load(open(path, encoding="utf-8"))
order = snapshot["orders"][0]
order["buyer_feedback_sha256"] = "a" * 64
order["buyer_feedback_requirements_path"] = requirements
json.dump(snapshot, open(path, "w", encoding="utf-8"))
PY
run_case green 0
grep -q 'Stable project root:' "$TMP/evidence-green/PAID_WORK.prompt.txt"
grep -q 'Never create placeholder, fake, or synthetic' "$TMP/evidence-green/PAID_WORK.prompt.txt"
grep -q 'Do not write outside PROJECT_ROOT' "$TMP/evidence-green/PAID_WORK.prompt.txt"
grep -q 'existing build and test scripts' "$TMP/evidence-green/PAID_WORK.prompt.txt"
grep -q 'do not create or update the delivery manifest' "$TMP/evidence-green/PAID_WORK.prompt.txt"
grep -q 'Rewrite the packet-bound buyer-feedback requirements file during this pass' "$TMP/evidence-green/PAID_WORK.prompt.txt"
grep -q 'Create exactly one final next-version artifact' "$TMP/evidence-green/PAID_WORK.prompt.txt"
grep -q 'identical JSON array in both' "$TMP/evidence-green/PAID_WORK.prompt.txt"
grep -q 'nonempty strings, never objects' "$TMP/evidence-green/PAID_WORK.prompt.txt"
! grep -q 'permitted outside write\|Exact delivery evidence path\|Also write the same' "$TMP/evidence-green/PAID_WORK.prompt.txt"
! grep -q 'Live evidence directory\|live evidence' "$TMP/evidence-green/PAID_WORK.prompt.txt"
if grep -qF "$HOME_DIR/gig/delivery-evidence/4201.json" "$TMP/evidence-green/PAID_WORK.prompt.txt"; then
  echo 'RED: stable delivery evidence path leaked into PAID_WORK prompt'
  exit 1
fi
test ! -e "$TMP/evidence-green/PAID_QUEUE_DELIVERY.prompt.txt"
test "$(cat "$TMP/browser.log")" = "deterministic-paid-progress"
expected_runner_log="$(printf '%s\n' gig-PAID_WORK gig-B0 gig-B1 gig-B2)"
test "$(cat "$TMP/runner.log")" = "$expected_runner_log"
! grep -q '^gig-REFLECT$' "$TMP/runner.log"
! grep -q '^gig-paid-queue-assess$' "$TMP/runner.log"
! grep -q '"pass_id":"paid-green"' "$HOME_DIR/gig/pass-failures.jsonl"
# ...and the buyer-visible progress that really happened is still recorded, in the
# ledger that means exactly that. applied.jsonl is the apply lane's scratch pad: a
# paid-contract progress reply is not a 募集 application, and writing it there both
# broke the invariant above and fed application_ledger/category_bandit a false
# "engaged application". One fact, one ledger.
python3 - "$HOME_DIR/gig/paid-progress.jsonl" <<'PY'
import json, sys
rows = [json.loads(line) for line in open(sys.argv[1], encoding="utf-8") if line.strip()]
assert len(rows) == 1, rows
row = rows[0]
assert row["pass_id"] == "paid-green", row
assert row["status"] == "replied", row
assert row["action"] == "paid_progress", row
assert row["buyer_visible"] is True, row
assert str(row["requestId"]), row
assert row["artifact_version"] == "v3", row
assert row["package_sha256"], row
assert row["url"].endswith("/4201"), row
PY
test -s "$TMP/evidence-green/b1-context.json"
python3 - "$TMP/economics.jsonl" <<'PY'
import json, sys
rows = [json.loads(line) for line in open(sys.argv[1], encoding="utf-8") if line.strip()]
assert len(rows) == 1, rows
event = rows[0]
assert event["type"] == "ai.anicca.unit_economics.revenue.settled.v1", event
assert event["data"]["loop"] == "gig", event
assert event["data"]["currency"] == "JPY", event
assert event["data"]["amount_minor"] == 1, event
PY
python3 - "$TMP/evidence-green/paid-work-transaction.json" \
  "$HOME_DIR/gig/projects/4201/delivery/paid-work-result.json" \
  "$HOME_DIR/gig/delivery-evidence/4201.json" <<'PY'
import hashlib, json, sys
transaction = json.load(open(sys.argv[1], encoding="utf-8"))
assert transaction["status"] == "committed", transaction
manifest = open(sys.argv[2], "rb").read()
stable = open(sys.argv[3], "rb").read()
assert stable == manifest
assert transaction["after"]["stable_delivery_evidence"]["sha256"] == hashlib.sha256(stable).hexdigest()
PY
python3 - "$HOME_DIR/gig/projects/4201/state.json" "$TMP/evidence-green/delivery-queue.json" \
  "$HOME_DIR/gig/pass-report.jsonl" "$HOME_DIR/gig/.last-pass" \
  "$HOME_DIR/gig/lane-actions.sqlite3" <<'PY'
import json, sqlite3, sys
state = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert state["current_version"] == "v3", state
assert state["latest_buyer_visible_version"] == "v3", state
assert state["next_action"] == "await_buyer_feedback", state
assert state["buyer_visible"] is True, state
assert state.get("formal_delivery_complete") is not True, state
assert state.get("earned") is not True, state
queue = json.load(open(sys.argv[2], encoding="utf-8"))
assert queue["items"][0]["blockers"] == ["formal_delivery_not_confirmed"], queue
report_rows = [json.loads(line) for line in open(sys.argv[3], encoding="utf-8") if line.strip()]
report = report_rows[-1]
assert report["pass_id"] == "paid-green", report
assert report["status"] == "success", report
assert report["steps_executed"] == [
    "PAID_WORK", "PAID_QUEUE_DELIVERY", "B0", "B1", "B2"
], report
assert all(
    not row.startswith(("B0:", "B1:", "B2:"))
    for row in report["steps_skipped_policy"]
), report
heartbeat = json.load(open(sys.argv[4], encoding="utf-8"))
assert heartbeat == report, (heartbeat, report)
assert open(sys.argv[4], "rb").read() == (open(sys.argv[3], "rb").read().splitlines()[-1] + b"\n")
with sqlite3.connect(sys.argv[5]) as connection:
    rows = connection.execute(
        "SELECT lane,action_kind,state,side_effect_count,evidence_hash "
        "FROM lane_actions WHERE event_key LIKE ? ORDER BY lane",
        ("%:pass-paid-green",),
    ).fetchall()
assert rows == [
    ("application", "verified_noop", "verified_noop", 0, None),
    ("delivery", "progress", "verified", 1, rows[1][4]),
    ("listing", "publish", "verified", 1, rows[2][4]),
    ("reply", "verified_noop", "verified_noop", 0, None),
], rows
assert rows[1][4], rows
assert rows[2][4], rows
PY

# Answer mode already performs and verifies the browser send inside PAID_WORK.
# The outer paid-queue path must reuse that evidence, not open the talkroom and
# send/observe a second time. A second browser call used to overwrite the first
# send_performed=true manifest with a deduplicated observation.
python3 - "$TMP/snapshot.json" "$TMP/answer-snapshot.json" \
  "$HOME_DIR/gig/projects/4201/requirements/live-buyer-reply.json" <<'PY'
import json, sys
source, output, requirements = sys.argv[1:]
snapshot = json.load(open(source, encoding="utf-8"))
order = snapshot["orders"][0]
order["buyer_feedback_sha256"] = "b" * 64
order["buyer_feedback_requirements_path"] = requirements
json.dump(snapshot, open(output, "w", encoding="utf-8"))
PY
run_case answer 0 "$TMP/answer-snapshot.json"
test "$(cat "$TMP/browser.log")" = "deterministic-paid-progress"
test "$(grep -c '^gig-PAID_WORK$' "$TMP/runner.log")" -eq 1
python3 - "$HOME_DIR/gig/pass-report.jsonl" "$HOME_DIR/gig/paid-progress.jsonl" <<'PY'
import json, sys
reports = [json.loads(line) for line in open(sys.argv[1], encoding="utf-8") if line.strip()]
answer = [row for row in reports if row["pass_id"] == "paid-answer"][-1]
assert "PAID_WORK" in answer["steps_executed"], answer
assert "PAID_QUEUE_DELIVERY" in answer["steps_executed"], answer
progress = [json.loads(line) for line in open(sys.argv[2], encoding="utf-8") if line.strip()]
assert any(row["pass_id"] == "paid-answer" for row in progress), progress
PY
python3 - "$HOME_DIR/gig/projects/4201/state.json" <<'PY'
import json, sys
state = json.load(open(sys.argv[1], encoding="utf-8"))
assert state["handled_buyer_feedback_sha256"] == "b" * 64, state
assert state["material_event_outcome"] == "buyer_answer_sent", state
assert state["last_buyer_answer_sha256"], state
assert state["next_action"] == "await_buyer_feedback", state
PY

# The next unchanged poll observes the same buyer feedback. The live DOM can
# still say the artifact is absent (the buyer's exact issue was that the
# confirmation UI did not transition), but the verified text answer itself is
# already handled. It must never invoke the builder or browser again.
python3 - "$TMP/snapshot.json" "$TMP/unchanged-snapshot.json" <<'PY'
import json, sys
snapshot = json.load(open(sys.argv[1], encoding="utf-8"))
order = snapshot["orders"][0]
order["buyer_visible_artifact_observed"] = False
order["buyer_feedback_pending_artifact"] = True
order["buyer_reply_after_artifact_observed"] = True
order["buyer_feedback_sha256"] = "b" * 64
json.dump(snapshot, open(sys.argv[2], "w", encoding="utf-8"))
PY
run_case unchanged-artifact 0 "$TMP/unchanged-snapshot.json"
if grep -q '^gig-PAID_WORK$\|^gig-B0$\|^gig-B1$\|^gig-B2$' "$TMP/runner.log"; then
  echo "RED: unchanged artifact repeated paid/revenue work: $(tr '\n' ',' < "$TMP/runner.log")" >&2
  exit 1
fi
test ! -s "$TMP/browser.log"
python3 - "$HOME_DIR/gig/projects/4201/state.json" <<'PY'
import json, sys
state = json.load(open(sys.argv[1], encoding="utf-8"))
assert state["handled_buyer_feedback_sha256"] == "b" * 64, state
assert state["material_event_outcome"] == "buyer_answer_sent", state
assert state["next_action"] == "await_buyer_feedback", state
PY
run_recovery_case() {
  local mode="$1" expected="$2"; : > "$TMP/recovery-runner.log"; : > "$TMP/recovery-browser.log"
  set +e
  HOME="$RECOVERY_HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/recovery-snapshot.json" \
    GIG_TODAY=2026-07-22 GIG_LOCK_DIR="$TMP/recovery-lock.d" GIG_EVIDENCE_DIR="$TMP/recovery-evidence-$mode" \
    GIG_TEST_CDP_ALIVE=1 GIG_TEST_PAID_MODE="$mode" GIG_TEST_RUNNER_LOG="$TMP/recovery-runner.log" \
    GIG_TEST_BROWSER_LOG="$TMP/recovery-browser.log" GIG_PAID_PROGRESS_BROWSER="$TMP/fake-paid-progress" \
    ANICCA_UNIT_ECONOMICS_LEDGER="$TMP/recovery-economics.jsonl" \
    GIG_PASS_ID="paid-recovery-$mode" \
    bash "$RECOVERY_HOME_DIR/profitable-claude/skills/gig-work/gig_pass.sh" >"$TMP/recovery-out-$mode" 2>"$TMP/recovery-err-$mode"
  local rc=$?; set -e
  if [ "$rc" -ne "$expected" ]; then
    tail -40 "$TMP/recovery-out-$mode" "$TMP/recovery-err-$mode"
  fi
  test "$rc" -eq "$expected"
}

# If the browser helper fails after a green builder, the next pass reuses the
# durable artifact/hash/acceptance bundle and invokes only browser delivery.
mkdir -p "$RECOVERY_HOME_DIR/gig/projects/4201/requirements"
printf '%s\n' \
  '{"observed_at":"2020-01-01T00:00:00+00:00","feedback_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}' \
  > "$RECOVERY_HOME_DIR/gig/projects/4201/requirements/live-buyer-reply.json"
python3 - "$TMP/snapshot.json" "$TMP/recovery-snapshot.json" \
  "$RECOVERY_HOME_DIR/gig/projects/4201/requirements/live-buyer-reply.json" <<'PY'
import json, sys
source, output, requirements = sys.argv[1:]
snapshot = json.load(open(source, encoding="utf-8"))
snapshot["orders"][0]["buyer_feedback_requirements_path"] = requirements
json.dump(snapshot, open(output, "w", encoding="utf-8"))
PY
run_recovery_case browser-fail 1
grep -q '^gig-PAID_WORK$' "$TMP/recovery-runner.log"
! grep -q '^gig-paid-queue-assess$' "$TMP/recovery-runner.log"
if [ "$(cat "$TMP/recovery-browser.log")" != "deterministic-paid-progress" ]; then
  echo "RED: accepted artifact did not reach deterministic paid-progress recovery" >&2
  tail -40 "$TMP/recovery-out-browser-fail" >&2
  tail -40 "$TMP/recovery-err-browser-fail" >&2
  exit 1
fi
test "$(shasum -a 256 "${recovery_lower_paths[@]}")" = "$recovery_lower_before"
# Nothing reached the buyer, so nothing is claimed. A failed attempt leaves no row.
if [ -s "$RECOVERY_HOME_DIR/gig/paid-progress.jsonl" ]; then
  echo 'RED: a failed browser send recorded buyer-visible progress that never happened' >&2
  exit 1
fi
python3 - "$RECOVERY_HOME_DIR/gig/projects/4201/state.json" <<'PY'
import json, sys
state = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert state["buyer_visible"] is False, state
assert state["artifact_ready_pending_browser"] is True, state
assert state["next_action"] == "retry_buyer_visible_delivery", state
assert state["current_version"] == "v3", state
assert state["current_package_sha256"], state
json.dump({key: state[key] for key in (
    "current_version", "current_artifact_path", "current_package_sha256",
    "current_acceptance_evidence_path", "current_acceptance_delta",
)}, open(sys.argv[1] + ".binding", "w"), sort_keys=True)
PY
run_recovery_case green-existing 0
! grep -q '^gig-PAID_WORK$' "$TMP/recovery-runner.log"
for revenue_label in B0 B1 B2; do
  test "$(grep -c "^gig-${revenue_label}$" "$TMP/recovery-runner.log")" -eq 1
done
test "$(cat "$TMP/recovery-browser.log")" = "deterministic-paid-progress"
python3 - "$RECOVERY_HOME_DIR/gig/projects/4201/state.json" <<'PY'
import json, sys
state = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert state["buyer_visible"] is True, state
assert state["artifact_ready_pending_browser"] is False, state
assert state["next_action"] == "await_buyer_feedback", state
assert state["current_version"] == "v3", state
assert state["latest_buyer_visible_package_sha256"] == state["current_package_sha256"], state
binding = json.load(open(sys.argv[1] + ".binding", encoding="utf-8"))
for key in binding:
    assert state[key] == binding[key], (key, state, binding)
PY
# The recovered send did reach the buyer, so it is recorded -- and still not in any
# application ledger. Lower lanes now run after the recovered send, so their own
# legitimate state may advance; the paid-progress fact must still stay in its
# dedicated ledger. An external side effect is never rolled back by deleting its
# record; it is recorded where that record means what happened.
python3 - "$RECOVERY_HOME_DIR/gig/paid-progress.jsonl" <<'PY'
import json, sys
rows = [json.loads(line) for line in open(sys.argv[1], encoding="utf-8") if line.strip()]
assert len(rows) == 1, rows
row = rows[0]
assert row["pass_id"] == "paid-recovery-green-existing", row
assert row["action"] == "paid_progress", row
assert row["buyer_visible"] is True, row
assert row["artifact_version"] == "v3", row
PY

echo 'PASS: paid-work gate runs first without starving the hourly revenue lanes'
