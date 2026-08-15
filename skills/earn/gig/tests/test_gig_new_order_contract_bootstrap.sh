#!/usr/bin/env bash
# A22 (2026-08-01, SSOT section 0.1.3 blocker #1): a NEW order arrives with an
# empty delivery/ directory. Before this fix, paid_work_transaction.py begin
# raised acceptance_contract_missing_or_invalid because the contract only ever
# existed AFTER the builder ran -- a chicken-and-egg deadlock that killed every
# pass (observed live on order 90000004). Now code bootstraps a generic
# contract BEFORE begin pins it, so a new order proceeds without the error.
set -euo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d /tmp/gig-new-order-bootstrap.XXXXXX)
trap 'rm -rf "$TMP"' EXIT
HOME_DIR="$TMP/home"
G="$HOME_DIR/life-manager/skills/earn/gig"
mkdir -p "$HOME_DIR/gig" "$G/scripts" "$G/schemas" "$G/config/connectors" "$HOME_DIR/life-manager/skills/agent-runner"
cp "$SKILL_DIR/gig_pass.sh" "$G/gig_pass.sh"
cp "$SKILL_DIR/passprep.py" "$G/passprep.py"
cp "$SKILL_DIR/strategy.default.json" "$G/strategy.default.json"
cp "$SKILL_DIR/scripts/delivery_queue.py" "$G/scripts/delivery_queue.py"
cp "$SKILL_DIR/scripts/delivery_cadence.py" "$G/scripts/delivery_cadence.py"
cp "$SKILL_DIR/scripts/delivery_project.py" "$G/scripts/delivery_project.py"
cp "$SKILL_DIR/scripts/project_ledger.py" "$G/scripts/project_ledger.py"
cp "$SKILL_DIR/scripts/delivery_identity.py" "$G/scripts/delivery_identity.py"
cp "$SKILL_DIR/scripts/paid_progress_finalize_gate.py" "$G/scripts/paid_progress_finalize_gate.py"
# paid_work_evidence reads ask_buyer (which reads buyer_voice) to decide whether the
# builder declared itself blocked. Without them the gate reports "undeterminable" and
# refuses every delivery, which is the correct fail-closed behaviour and the wrong
# fixture.
for _blocked_gate in paid_work_evidence.py artifact_judge.py ask_buyer.py buyer_voice.py; do
  cp "$SKILL_DIR/scripts/$_blocked_gate" "$G/scripts/$_blocked_gate"
done
cp "$SKILL_DIR/scripts/paid_work_transaction.py" "$G/scripts/paid_work_transaction.py"
cp "$SKILL_DIR/scripts/paid_work_contract_bootstrap.py" "$G/scripts/paid_work_contract_bootstrap.py"
cp "$SKILL_DIR/scripts/paid_work_validation_contract.py" "$G/scripts/paid_work_validation_contract.py"
cp "$SKILL_DIR/scripts/paid_queue_evidence.py" "$G/scripts/paid_queue_evidence.py"
cp "$SKILL_DIR/scripts/gig_context_packet.py" "$G/scripts/gig_context_packet.py"
cp "$SKILL_DIR/../agent-runner/context_packet.py" "$HOME_DIR/life-manager/skills/agent-runner/context_packet.py"
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

# NEW ORDER: the project skeleton exists but delivery/ is EMPTY -- no
# validation-contract.json, no validator, nothing delivered yet. This is the
# exact live state of ~/gig/projects/90000004 on 2026-08-01.
mkdir -p "$HOME_DIR/gig/projects/generic-request-42/requirements" \
  "$HOME_DIR/gig/projects/generic-request-42/source" \
  "$HOME_DIR/gig/projects/generic-request-42/work" \
  "$HOME_DIR/gig/projects/generic-request-42/artifacts" \
  "$HOME_DIR/gig/projects/generic-request-42/acceptance" \
  "$HOME_DIR/gig/projects/generic-request-42/delivery" \
  "$HOME_DIR/gig/projects/generic-request-42/evidence"

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
    "title": "generic new order",
    "price_jpy": 2500,
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
cat > "$HOME_DIR/life-manager/skills/agent-runner/agent_runner.py" <<'PY'
#!/usr/bin/env python3
import hashlib, json, os
from pathlib import Path
args = __import__('sys').argv[1:]
label = args[args.index("--task-label") + 1].removeprefix("gig-")
evidence = Path(args[args.index("--evidence-dir") + 1]); evidence.mkdir(parents=True, exist_ok=True)
workdir = Path(args[args.index("--workdir") + 1])
Path(os.environ["GIG_TEST_RUNNER_LOG"]).open("a", encoding="utf-8").write(label + "\n")
if label == "PAID_WORK":
    for name in ("requirements", "source", "work", "artifacts", "acceptance", "delivery", "evidence"):
        (workdir / name).mkdir(parents=True, exist_ok=True)
    req = workdir / "requirements" / "latest-feedback.json"; req.write_text('{"feedback":"initial order"}\n')
    # The bootstrap contract enforces >=1024 bytes and an allowlisted suffix.
    artifact = workdir / "artifacts" / "delivery-v1.zip"; artifact.write_bytes(b"x" * 4096)
    acceptance = workdir / "acceptance" / "v1.json"; acceptance.write_text('{"status":"PASS","acceptance_delta":["初回納品物を作成"]}\n')
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    row = {"status":"ok", "project_root":str(workdir), "requirements_path":str(req), "artifact_path":str(artifact),
           "artifact_version":"v1", "acceptance_evidence_path":str(acceptance), "acceptance_status":"PASS",
           "acceptance_delta":["初回納品物を作成"], "package_sha256":digest}
    (workdir / "delivery" / "paid-work-result.json").write_text(json.dumps(row)+"\n")
elif label == "REFLECT":
    current_pass = json.loads(os.environ["GIG_REFLECT_CONTEXT_JSON"])
    result = evidence / "attempt-01.result.json"
    result.write_text(json.dumps({"status":"ok","summary":"new order first artifact built",
        "evidence":["bootstrap contract evidence"],"current_pass":current_pass})+"\n")
    (evidence / "summary.json").write_text(json.dumps({"status":"success","task_label":"gig-REFLECT",
        "result_path":str(result)})+"\n")
    raise SystemExit(0)
(evidence / "summary.json").write_text(json.dumps({"status": "success", "task_label": "gig-" + label}) + "\n", encoding="utf-8")
raise SystemExit(0)
PY
chmod +x "$HOME_DIR/life-manager/skills/agent-runner/agent_runner.py"
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
printf '%s\n' '{"status":"PASS","errors":[]}'
SH
chmod +x "$TMP/fake-validation-docker"
export GIG_PAID_VALIDATOR_DOCKER="$TMP/fake-validation-docker"

set +e
HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/snapshot.json" \
  GIG_TODAY=2026-07-22 GIG_LOCK_DIR="$TMP/lock.d" GIG_EVIDENCE_DIR="$TMP/evidence" \
  GIG_TEST_CDP_ALIVE=1 GIG_TEST_RUNNER_LOG="$TMP/runner.log" GIG_PASS_ID="new-order-bootstrap" \
  GIG_PAID_PROGRESS_BROWSER="$TMP/fake-paid-progress" \
  bash "$G/gig_pass.sh" >"$TMP/out" 2>"$TMP/err"
rc=$?
set -e
if [ "$rc" -ne 0 ]; then
  tail -40 "$TMP/err" >&2
fi
test "$rc" -eq 0
# The builder model call actually ran for the new order.
grep -qx 'PAID_WORK' "$TMP/runner.log"
# The chicken-and-egg error is gone for a NEW order.
test ! -e "$HOME_DIR/gig/pass-failures.jsonl" || {
  ! grep -q 'acceptance_contract_missing_or_invalid' "$HOME_DIR/gig/pass-failures.jsonl"
  ! grep -q '"pass_id":"new-order-bootstrap".*paid_work_transaction_begin_failed' "$HOME_DIR/gig/pass-failures.jsonl"
  ! grep -q '"pass_id":"new-order-bootstrap".*paid_work_contract_bootstrap_failed' "$HOME_DIR/gig/pass-failures.jsonl"
}
# Code generated the contract and its pinned validator before begin.
test -s "$HOME_DIR/gig/projects/generic-request-42/delivery/validation-contract.json"
test -s "$HOME_DIR/gig/projects/generic-request-42/validation/validate_delivery_generic.py"
python3 - "$HOME_DIR/gig/projects/generic-request-42/delivery/validation-contract.json" <<'PY'
import json, sys
contract = json.load(open(sys.argv[1], encoding="utf-8"))
assert contract["version"] == 1, contract
assert contract["generated_by"] == "paid_work_contract_bootstrap.py", contract
kinds = {row["kind"] for row in contract["commands"]}
assert {"test", "domain"}.issubset(kinds), contract
PY
# The pass completed with a success heartbeat.
test -s "$HOME_DIR/gig/pass-report.jsonl"
test -s "$HOME_DIR/gig/.last-pass"
echo 'PASS: a new order with an empty delivery/ bootstraps its validation contract and paid work proceeds'
