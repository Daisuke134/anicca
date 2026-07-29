#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
PASS="$SKILL_DIR/gig_pass.sh"
TMP=$(mktemp -d /tmp/gig-delivery-first.XXXXXX)
trap 'rm -rf "$TMP"' EXIT
HOME_DIR="$TMP/home"
mkdir -p "$HOME_DIR/gig" "$HOME_DIR/anicca/skills/browser/scripts" \
  "$HOME_DIR/profitable-claude/skills/gig-work/scripts" \
  "$HOME_DIR/profitable-claude/skills/gig-work/config/connectors" \
  "$HOME_DIR/profitable-claude/skills/agent-runner"
cp "$PASS" "$HOME_DIR/profitable-claude/skills/gig-work/gig_pass.sh"
cp "$SKILL_DIR/scripts/delivery_queue.py" "$HOME_DIR/profitable-claude/skills/gig-work/scripts/delivery_queue.py"
cp "$SKILL_DIR/scripts/delivery_cadence.py" "$HOME_DIR/profitable-claude/skills/gig-work/scripts/delivery_cadence.py"
cp "$SKILL_DIR/scripts/delivery_project.py" "$HOME_DIR/profitable-claude/skills/gig-work/scripts/delivery_project.py"
cp "$SKILL_DIR/scripts/project_ledger.py" "$HOME_DIR/profitable-claude/skills/gig-work/scripts/project_ledger.py"
cp "$SKILL_DIR/scripts/delivery_identity.py" "$HOME_DIR/profitable-claude/skills/gig-work/scripts/delivery_identity.py"
cp "$SKILL_DIR/scripts/paid_progress_finalize_gate.py" "$HOME_DIR/profitable-claude/skills/gig-work/scripts/paid_progress_finalize_gate.py"
cp "$SKILL_DIR/scripts/paid_queue_evidence.py" "$HOME_DIR/profitable-claude/skills/gig-work/scripts/paid_queue_evidence.py"
cp "$SKILL_DIR/scripts/gig_context_packet.py" "$HOME_DIR/profitable-claude/skills/gig-work/scripts/gig_context_packet.py"
cp "$SKILL_DIR/../agent-runner/context_packet.py" "$HOME_DIR/profitable-claude/skills/agent-runner/context_packet.py"
cp "$SKILL_DIR/scripts/reply_queue.py" "$HOME_DIR/profitable-claude/skills/gig-work/scripts/reply_queue.py"
cp "$SKILL_DIR/scripts/connector_outbox.py" "$HOME_DIR/profitable-claude/skills/gig-work/scripts/connector_outbox.py"
cp "$SKILL_DIR/config/connectors/coconala.json" "$HOME_DIR/profitable-claude/skills/gig-work/config/connectors/coconala.json"
cp "$SKILL_DIR/scripts/reconcile_paid_delivery.py" "$HOME_DIR/profitable-claude/skills/gig-work/scripts/reconcile_paid_delivery.py"
cp "$SKILL_DIR/scripts/cdp_lock.sh" "$HOME_DIR/profitable-claude/skills/gig-work/scripts/cdp_lock.sh"
cp "$SKILL_DIR/scripts/run_with_cdp_lock.sh" "$HOME_DIR/profitable-claude/skills/gig-work/scripts/run_with_cdp_lock.sh"
chmod +x "$HOME_DIR/profitable-claude/skills/gig-work/scripts/run_with_cdp_lock.sh"
cp "$SKILL_DIR/tests/fixtures/live_queue.json" "$TMP/snapshot.json"
python3 - "$TMP/snapshot.json" <<'PY'
import json, sys
path = sys.argv[1]
snapshot = json.load(open(path, encoding="utf-8"))
snapshot["orders"][0]["buyer_feedback_pending_artifact"] = False
snapshot["orders"][0]["buyer_reply_after_artifact_observed"] = False
json.dump(snapshot, open(path, "w", encoding="utf-8"))
PY
cat > "$HOME_DIR/profitable-claude/skills/agent-runner/agent_runner.py" <<'PY'
#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
args=sys.argv[1:]
task_class=args[args.index("--task-class")+1]
evidence=args[args.index("--evidence-dir")+1]
os.makedirs(evidence,exist_ok=True)
if args[args.index("--task-label")+1] == "gig-paid-queue-assess":
    prompt=Path(args[args.index("--prompt-file")+1]).read_text()
    assert '"kind":"gig_paid_delivery"' in prompt
    assert '"max_bytes":8192' in prompt
    expected=json.loads((Path(evidence).parent/"paid-queue-expected.json").read_text())
    tid=str(expected["talkroom_id"]); url=f"https://coconala.com/talkrooms/{tid}"
    shot=Path(evidence)/"post.png"; shot.write_bytes(b"png")
    live=Path(evidence)/"post.json"; digest="a"*64
    live.write_text(json.dumps({"url":url,"sent":True,"formal_delivery_checkbox":False,"latest_seller_attachment":{"filename":"delivery-v3.zip","size_bytes":1,"message":f"v3 {digest}"}})+"\n")
    (Path(evidence)/"paid-queue-evidence.json").write_text(json.dumps({"sent":True,"formal_delivery_checkbox":False,"captured_at":"2026-07-22T08:00:00Z","talkroom_id":tid,"artifact_basename":"delivery-v3.zip","artifact_version":"v3","package_sha256":digest,"acceptance_delta":["revision"],"screenshot_path":str(shot),"live_dom_path":str(live)})+"\n")
open(os.path.join(evidence,"summary.json"),"w").write(json.dumps({"status":"success","task_class":task_class})+"\n")
open(os.environ["GIG_TEST_RUNNER_LOG"],"a").write(task_class+"\n")
raise SystemExit(0)
PY
chmod +x "$HOME_DIR/profitable-claude/skills/agent-runner/agent_runner.py"

before=1234567890
touch -t 200902132331.30 "$HOME_DIR/gig/.last-pass"
before=$(stat -f %m "$HOME_DIR/gig/.last-pass")
set +e
HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/snapshot.json" \
  GIG_TODAY=2026-07-21 GIG_LOCK_DIR="$TMP/lock.d" GIG_TEST_CDP_ALIVE=1 GIG_TEST_RUNNER_LOG="$TMP/runner.log" \
  bash "$HOME_DIR/profitable-claude/skills/gig-work/gig_pass.sh" >"$TMP/out" 2>"$TMP/err"
rc=$?
set -e
test "$rc" -ne 0 || { echo 'missing delivery evidence returned success'; exit 1; }
test "$(stat -f %m "$HOME_DIR/gig/.last-pass")" = "$before" || { echo '.last-pass changed'; exit 1; }
test ! -d "$TMP/lock.d" || { echo 'lock leaked after failure'; exit 1; }
test -s "$HOME_DIR/gig/pass-failures.jsonl" || { echo 'failure ledger missing'; exit 1; }
grep -q '5138597' "$HOME_DIR/gig/pass-failures.jsonl"
grep -q 'paid_queue_delivery_failed' "$HOME_DIR/gig/pass-failures.jsonl"
test ! -e "$TMP/runner.log" || { echo 'missing paid evidence incorrectly invoked a model'; exit 1; }
grep -q 'STEP PAID_QUEUE_DELIVERY start (deterministic_browser=true model_tokens=0)' "$TMP/err"
! grep -q 'STEP PAID_QUEUE_DELIVERY done' "$TMP/err" || { echo 'missing paid evidence claimed delivery success'; exit 1; }
! grep -q 'STEP LEARN start\|STEP B0 start\|STEP PROFILE start\|STEP B2 start' "$TMP/err" || { echo 'lower priority step ran'; exit 1; }
test ! -e "$HOME_DIR/gig/pass-report.jsonl" || { echo 'success ledger written'; exit 1; }

echo 'PASS: paid delivery blocker preempts lower-priority work and fails honestly'
