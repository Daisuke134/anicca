#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d /tmp/gig-b1-context.XXXXXX)
trap 'rm -rf "$TMP"' EXIT
HOME_DIR="$TMP/home"
G="$HOME_DIR/life-manager/skills/earn/gig"
mkdir -p "$G/scripts" "$G/schemas" "$G/config/connectors" "$HOME_DIR/life-manager/runtime/agent-runner" "$HOME_DIR/gig"
for file in gig_pass.sh passprep.py strategy.default.json; do cp "$SKILL_DIR/$file" "$G/$file"; done
cp "$SKILL_DIR/scripts/gig_paths.sh" "$G/scripts/gig_paths.sh"
for file in delivery_queue.py delivery_cadence.py delivery_identity.py delivery_project.py project_ledger.py b0_result_gate.py b1_conversation_gate.py b2_queue_gate.py b2_result_gate.py reply_queue.py connector_outbox.py; do
  cp "$SKILL_DIR/scripts/$file" "$G/scripts/$file"
done
cp "$SKILL_DIR/config/connectors/coconala.json" "$G/config/connectors/coconala.json"
for file in gig_step_result.schema.json gig_b0_result.schema.json gig_b1_result.schema.json gig_reflect_result.schema.json; do
  cp "$SKILL_DIR/schemas/$file" "$G/schemas/$file"
done
cat > "$G/scripts/gig_selfimprove_verify.sh" <<'SH'
#!/usr/bin/env bash
exit 0
SH
chmod +x "$G/scripts/gig_selfimprove_verify.sh"
cat > "$HOME_DIR/life-manager/runtime/agent-runner/agent_runner.py" <<'PY'
#!/usr/bin/env python3
import hashlib, json, os, sys
from pathlib import Path
args=sys.argv[1:]
label=args[args.index("--task-label")+1].removeprefix("gig-")
evidence=Path(args[args.index("--evidence-dir")+1]); evidence.mkdir(parents=True,exist_ok=True)
Path(os.environ["RUNNER_LOG"]).open("a").write(label+"\n")
if label == "B0":
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
elif label == "B1":
    # Reproduces the production bug: a generic status=ok without inbox or
    # per-talkroom evidence must not make B1 successful.
    result=evidence/"attempt-01.result.json"
    result.write_text(json.dumps({"status":"ok","summary":"404 treated as okay","evidence":["status only"]})+"\n")
    (evidence/"summary.json").write_text(json.dumps({"status":"success","task_label":"gig-B1","result_path":str(result)})+"\n")
else:
    (evidence/"summary.json").write_text(json.dumps({"status":"success","task_label":"gig-"+label})+"\n")
raise SystemExit(0)
PY
chmod +x "$HOME_DIR/life-manager/runtime/agent-runner/agent_runner.py"
mkdir -p "$HOME_DIR/life-manager/skills/browser/scripts"
cat > "$HOME_DIR/life-manager/skills/browser/scripts/cdp_context_lease.py" <<'PY'
#!/usr/bin/env python3
raise SystemExit(0)
PY
chmod +x "$HOME_DIR/life-manager/skills/browser/scripts/cdp_context_lease.py"

cat > "$TMP/good.json" <<'JSON'
{"captured_at":"2026-07-22T00:00:00Z","inbox":{"url":"https://coconala.com/message?fromMyPage=true","not_found":false},"orders":[],"quotes":[],"inquiries":[{"talkroom_id":"42","talkroom_url":"https://coconala.com/talkrooms/42","reply_required":false}]}
JSON
set +e
HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/good.json" \
  GIG_TODAY=2026-07-22 GIG_LOCK_DIR="$TMP/good-lock" RUNNER_LOG="$TMP/runner.log" \
  GIG_LEGACY_MAINTENANCE_ENABLED=1 GIG_MODEL_CALL_LIMIT=0 \
  bash "$G/gig_pass.sh" >"$TMP/good.out" 2>"$TMP/good.err"
status_only_rc=$?
set -e
test "$status_only_rc" -ne 0 || { echo 'status-only B1 result passed'; exit 1; }
grep -q 'b1_conversation_evidence_failed' "$HOME_DIR/gig/pass-failures.jsonl" || {
  cat "$HOME_DIR/gig/pass-failures.jsonl"
  cat "$TMP/good.err"
  exit 1
}
! grep -q '^B2$\|^REFLECT$' "$TMP/runner.log" || { echo 'lower steps ran after invalid B1 result'; exit 1; }
test ! -e "$HOME_DIR/gig/.last-pass" || { echo 'invalid B1 result wrote heartbeat'; exit 1; }

cat > "$TMP/404.json" <<'JSON'
{"captured_at":"2026-07-22T00:00:00Z","inbox":{"url":"https://coconala.com/mypage/messages","not_found":true},"orders":[],"quotes":[],"inquiries":[]}
JSON
: > "$TMP/runner.log"
set +e
HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/404.json" \
  GIG_TODAY=2026-07-22 GIG_LOCK_DIR="$TMP/404-lock" RUNNER_LOG="$TMP/runner.log" \
  GIG_LEGACY_MAINTENANCE_ENABLED=1 GIG_MODEL_CALL_LIMIT=0 \
  bash "$G/gig_pass.sh" >"$TMP/404.out" 2>"$TMP/404.err"
bad_route_rc=$?
set -e
test "$bad_route_rc" -ne 0 || { echo '404 inbox input passed'; exit 1; }
test ! -s "$TMP/runner.log" || { echo 'agent ran before invalid inbox failed closed'; exit 1; }
grep -q 'b1_context_build_failed' "$HOME_DIR/gig/pass-failures.jsonl"

echo 'PASS: B1 fails closed on wrong inbox input and status-only agent results'
