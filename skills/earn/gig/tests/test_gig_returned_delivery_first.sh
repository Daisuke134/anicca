#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d /tmp/gig-returned-delivery-first.XXXXXX)
trap 'rm -rf "$TMP"' EXIT
HOME_DIR="$TMP/home"
G="$HOME_DIR/profitable-claude/skills/gig-work"
mkdir -p "$HOME_DIR/gig" "$G/scripts" "$G/schemas" "$G/config/connectors" "$HOME_DIR/profitable-claude/skills/agent-runner"
cp "$SKILL_DIR/gig_pass.sh" "$G/gig_pass.sh"
cp "$SKILL_DIR/passprep.py" "$G/passprep.py"
cp "$SKILL_DIR/strategy.default.json" "$G/strategy.default.json"
cp "$SKILL_DIR/scripts/delivery_queue.py" "$G/scripts/delivery_queue.py"
cp "$SKILL_DIR/scripts/delivery_cadence.py" "$G/scripts/delivery_cadence.py"
cp "$SKILL_DIR/scripts/delivery_project.py" "$G/scripts/delivery_project.py"
cp "$SKILL_DIR/scripts/project_ledger.py" "$G/scripts/project_ledger.py"
cp "$SKILL_DIR/scripts/delivery_identity.py" "$G/scripts/delivery_identity.py"
cp "$SKILL_DIR/scripts/paid_progress_finalize_gate.py" "$G/scripts/paid_progress_finalize_gate.py"
cp "$SKILL_DIR/scripts/paid_work_evidence.py" "$G/scripts/paid_work_evidence.py"
cp "$SKILL_DIR/scripts/paid_work_transaction.py" "$G/scripts/paid_work_transaction.py"
cp "$SKILL_DIR/scripts/paid_work_validation_contract.py" "$G/scripts/paid_work_validation_contract.py"
cp "$SKILL_DIR/scripts/paid_queue_evidence.py" "$G/scripts/paid_queue_evidence.py"
cp "$SKILL_DIR/scripts/gig_context_packet.py" "$G/scripts/gig_context_packet.py"
cp "$SKILL_DIR/../agent-runner/context_packet.py" "$HOME_DIR/profitable-claude/skills/agent-runner/context_packet.py"
cp "$SKILL_DIR/scripts/reply_queue.py" "$G/scripts/reply_queue.py"
cp "$SKILL_DIR/scripts/connector_outbox.py" "$G/scripts/connector_outbox.py"
cp "$SKILL_DIR/config/connectors/coconala.json" "$G/config/connectors/coconala.json"
cp "$SKILL_DIR/scripts/reconcile_paid_delivery.py" "$G/scripts/reconcile_paid_delivery.py"
cp "$SKILL_DIR/scripts/paid_progress_ledger.py" "$G/scripts/paid_progress_ledger.py"
cp "$SKILL_DIR/scripts/cdp_lock.sh" "$G/scripts/cdp_lock.sh"
cp "$SKILL_DIR/scripts/run_with_cdp_lock.sh" "$G/scripts/run_with_cdp_lock.sh"
chmod +x "$G/scripts/run_with_cdp_lock.sh"
cp "$SKILL_DIR/schemas/gig_step_result.schema.json" "$G/schemas/gig_step_result.schema.json"
cp "$SKILL_DIR/schemas/gig_reflect_result.schema.json" "$G/schemas/gig_reflect_result.schema.json"
mkdir -p "$HOME_DIR/gig/projects/generic-request-42/source" "$HOME_DIR/gig/projects/generic-request-42/delivery"
cat > "$HOME_DIR/gig/projects/generic-request-42/source/validate_fixture.py" <<'PY'
import json, sys
from pathlib import Path
artifact = Path(sys.argv[1])
assert artifact.is_file() and artifact.stat().st_size >= 8
print(json.dumps({"status": "PASS"}))
PY
cat > "$HOME_DIR/gig/projects/generic-request-42/delivery/validation-contract.json" <<'JSON'
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
cat > "$TMP/snapshot.json" <<'JSON'
{
  "source": "authenticated_coconala_default_context_dom",
  "read_only": true,
  "captured_at": "2026-07-22T06:00:00+00:00",
  "orders": [{
    "contract_id": "direct-offer:generic-42",
    "request_id": "generic-request-42",
    "talkroom_id": "4201",
    "buyer": "buyer",
    "title": "generic returned delivery",
    "price_jpy": 17000,
    "price_source": "structured_order_label",
    "delivery_date": "2026-08-01",
    "status": "unknown",
    "talkroom_state": "取引中",
    "buyer_feedback_pending_artifact": true,
    "buyer_reply_after_artifact_observed": false,
    "buyer_visible_artifact_observed": false,
    "formal_delivery_observed": false
  }],
  "quotes": [],
  "inquiries": []
}
JSON
cat > "$HOME_DIR/profitable-claude/skills/agent-runner/agent_runner.py" <<'PY'
#!/usr/bin/env python3
import hashlib, json, os
from pathlib import Path
args = __import__('sys').argv[1:]
label = args[args.index("--task-label") + 1].removeprefix("gig-")
evidence = Path(args[args.index("--evidence-dir") + 1]); evidence.mkdir(parents=True, exist_ok=True)
workdir = Path(args[args.index("--workdir") + 1])
prompt = Path(args[args.index("--prompt-file") + 1]).read_text(encoding="utf-8")
Path(os.environ["GIG_TEST_RUNNER_LOG"]).open("a", encoding="utf-8").write(label + "\n")
if label == "PAID_WORK":
    for name in ("requirements", "source", "work", "artifacts", "acceptance", "delivery", "evidence"):
        (workdir / name).mkdir(parents=True, exist_ok=True)
    req = workdir / "requirements" / "latest-feedback.json"; req.write_text('{"feedback":"revision"}\n')
    artifact = workdir / "artifacts" / "delivery-v3.zip"; artifact.write_bytes(b"returned v3")
    acceptance = workdir / "acceptance" / "v3.json"; acceptance.write_text('{"status":"PASS","acceptance_delta":["revision"]}\n')
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    row = {"status":"ok", "project_root":str(workdir), "requirements_path":str(req), "artifact_path":str(artifact),
           "artifact_version":"v3", "acceptance_evidence_path":str(acceptance), "acceptance_status":"PASS",
           "acceptance_delta":["revision"], "package_sha256":digest}
    (workdir / "delivery" / "paid-work-result.json").write_text(json.dumps(row)+"\n")
elif label == "paid-queue-assess":
    expected = json.loads((Path(os.environ["GIG_EVIDENCE_DIR"]) / "paid-queue-expected.json").read_text())
    ev = expected.get("delivery_evidence", {}); tid = str(expected.get("talkroom_id")); url = f"https://coconala.com/talkrooms/{tid}"
    artifact = Path(ev["artifact_path"]); digest = ev["package_sha256"]
    shot = evidence / "post.png"; shot.write_bytes(b"png")
    live = evidence / "post.json"; live.write_text(json.dumps({"url":url,"sent":True,"formal_delivery_checkbox":False,"latest_seller_attachment":{
        "filename":artifact.name,"size_bytes":artifact.stat().st_size,"message":f"{ev['artifact_version']} {digest}"}})+"\n")
    (evidence / "paid-queue-evidence.json").write_text(json.dumps({"sent":True,"formal_delivery_checkbox":False,
        "captured_at":"2026-07-22T08:01:00Z","talkroom_id":tid,"artifact_basename":artifact.name,
        "artifact_version":ev["artifact_version"],"package_sha256":digest,"acceptance_delta":ev["acceptance_delta"],
        "screenshot_path":str(shot),"live_dom_path":str(live)})+"\n")
elif label == "REFLECT":
    current_pass = json.loads(os.environ["GIG_REFLECT_CONTEXT_JSON"])
    result = evidence / "attempt-01.result.json"
    result.write_text(json.dumps({"status":"ok","summary":"returned paid progress remains formal pending",
        "evidence":["queue-bound returned progress"],"current_pass":current_pass})+"\n")
    (evidence / "summary.json").write_text(json.dumps({"status":"success","task_label":"gig-REFLECT",
        "result_path":str(result)})+"\n")
    raise SystemExit(0)
(evidence / "summary.json").write_text(json.dumps({"status": "success", "task_label": "gig-" + label}) + "\n", encoding="utf-8")
raise SystemExit(0)
PY
chmod +x "$HOME_DIR/profitable-claude/skills/agent-runner/agent_runner.py"
cat > "$TMP/fake-paid-progress" <<'PY'
#!/usr/bin/env python3
import argparse, json
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument("--queue-item",type=Path,required=True); parser.add_argument("--manifest",type=Path,required=True)
parser.add_argument("--evidence-dir",type=Path,required=True); parser.add_argument("--default-tab-helper",type=Path,required=True)
args=parser.parse_args(); expected=json.loads(args.queue_item.read_text()); manifest=json.loads(args.manifest.read_text())
args.evidence_dir.mkdir(parents=True,exist_ok=True); artifact=Path(manifest["artifact_path"]); digest=manifest["package_sha256"]
tid=str(expected["talkroom_id"]); url=f"https://coconala.com/talkrooms/{tid}"
shot=args.evidence_dir/"post.png"; shot.write_bytes(b"png"); live=args.evidence_dir/"post.json"
live.write_text(json.dumps({"url":url,"sent":True,"formal_delivery_checkbox":False,"latest_seller_attachment":{"filename":artifact.name,"size_bytes":artifact.stat().st_size,"message":f"{manifest['artifact_version']} {digest}"}})+"\n")
(args.evidence_dir/"paid-queue-evidence.json").write_text(json.dumps({"sent":True,"formal_delivery_checkbox":False,"captured_at":"2026-07-22T08:01:00Z","talkroom_id":tid,"artifact_basename":artifact.name,"artifact_version":manifest["artifact_version"],"package_sha256":digest,"acceptance_delta":manifest["acceptance_delta"],"screenshot_path":str(shot),"live_dom_path":str(live)})+"\n")
PY
chmod +x "$TMP/fake-paid-progress"
cat > "$TMP/fake-validation-docker" <<'SH'
#!/usr/bin/env bash
printf '%s\n' '{"status":"PASS"}'
SH
chmod +x "$TMP/fake-validation-docker"
export GIG_PAID_VALIDATOR_DOCKER="$TMP/fake-validation-docker"

set +e
HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/snapshot.json" \
  GIG_TODAY=2026-07-22 GIG_LOCK_DIR="$TMP/lock.d" GIG_EVIDENCE_DIR="$TMP/evidence" \
  GIG_TEST_CDP_ALIVE=1 GIG_TEST_RUNNER_LOG="$TMP/runner.log" GIG_PASS_ID="returned-progress" \
  GIG_PAID_PROGRESS_BROWSER="$TMP/fake-paid-progress" \
  bash "$G/gig_pass.sh" >"$TMP/out" 2>"$TMP/err"
rc=$?
set -e
test "$rc" -eq 0
grep -qx 'PAID_WORK' "$TMP/runner.log"
! grep -qx 'REFLECT' "$TMP/runner.log"
! grep -qx 'paid-queue-assess' "$TMP/runner.log"
test "$(wc -l < "$TMP/runner.log" | tr -d ' ')" -eq 1
grep -q 'STEP PAID_QUEUE_DELIVERY start (deterministic_browser=true model_tokens=0)' "$TMP/err"
! grep -q 'STEP B1 start\|STEP B2 start\|STEP LEARN start' "$TMP/err"
test ! -e "$HOME_DIR/gig/pass-failures.jsonl" || ! grep -q '"pass_id":"returned-progress"' "$HOME_DIR/gig/pass-failures.jsonl"
test -s "$HOME_DIR/gig/pass-report.jsonl"
test -s "$HOME_DIR/gig/.last-pass"
echo 'PASS: returned delivery with unknown card status stays paid, enters delivery queue, and blocks lower-priority work'
