#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d /tmp/gig-step-cooldown.XXXXXX)
trap 'if [ "${KEEP_TMP:-0}" = 1 ]; then echo "KEEP_TMP=$TMP"; else rm -rf "$TMP"; fi' EXIT
HOME_DIR="$TMP/home"
GIG_DIR="$HOME_DIR/life-manager/skills/earn/gig"
mkdir -p "$GIG_DIR/scripts" "$GIG_DIR/schemas" "$GIG_DIR/config/connectors" "$HOME_DIR/life-manager/runtime/agent-runner" "$HOME_DIR/gig"
cp "$SKILL_DIR/gig_pass.sh" "$GIG_DIR/gig_pass.sh"
cp "$SKILL_DIR/scripts/gig_paths.sh" "$GIG_DIR/scripts/gig_paths.sh"
cp "$SKILL_DIR/passprep.py" "$GIG_DIR/passprep.py"
cp "$SKILL_DIR/strategy.default.json" "$GIG_DIR/strategy.default.json"
cp "$SKILL_DIR/scripts/delivery_queue.py" "$GIG_DIR/scripts/delivery_queue.py"
cp "$SKILL_DIR/scripts/delivery_cadence.py" "$GIG_DIR/scripts/delivery_cadence.py"
cp "$SKILL_DIR/scripts/delivery_identity.py" "$GIG_DIR/scripts/delivery_identity.py"
cp "$SKILL_DIR/scripts/reply_queue.py" "$GIG_DIR/scripts/reply_queue.py"
cp "$SKILL_DIR/scripts/connector_outbox.py" "$GIG_DIR/scripts/connector_outbox.py"
cp "$SKILL_DIR/config/connectors/coconala.json" "$GIG_DIR/config/connectors/coconala.json"
cp "$SKILL_DIR/scripts/b2_queue_gate.py" "$GIG_DIR/scripts/b2_queue_gate.py"
cp "$SKILL_DIR/scripts/b2_result_gate.py" "$GIG_DIR/scripts/b2_result_gate.py"
cp "$SKILL_DIR/scripts/b2_wall_clock.py" "$GIG_DIR/scripts/b2_wall_clock.py"
cp "$SKILL_DIR/scripts/b2_search_objective.py" "$GIG_DIR/scripts/b2_search_objective.py"
cp "$SKILL_DIR/scripts/application_report.py" "$GIG_DIR/scripts/application_report.py"
cp "$SKILL_DIR/scripts/normalize_applied.py" "$GIG_DIR/scripts/normalize_applied.py"
cp "$SKILL_DIR/scripts/b1_conversation_gate.py" "$GIG_DIR/scripts/b1_conversation_gate.py"
cp "$SKILL_DIR/scripts/b0_result_gate.py" "$GIG_DIR/scripts/b0_result_gate.py"
cp "$SKILL_DIR/schemas/gig_step_result.schema.json" "$GIG_DIR/schemas/gig_step_result.schema.json"
cp "$SKILL_DIR/schemas/gig_b0_result.schema.json" "$GIG_DIR/schemas/gig_b0_result.schema.json"
cp "$SKILL_DIR/schemas/gig_b1_result.schema.json" "$GIG_DIR/schemas/gig_b1_result.schema.json"
cp "$SKILL_DIR/schemas/gig_b2_result.schema.json" "$GIG_DIR/schemas/gig_b2_result.schema.json"
printf '%s\n' '{"captured_at":"2026-07-21T00:00:00Z","inbox":{"url":"https://coconala.com/message?fromMyPage=true","not_found":false},"orders":[],"quotes":[],"inquiries":[]}' > "$TMP/empty-snapshot.json"
cat > "$GIG_DIR/scripts/gig_selfimprove_verify.sh" <<'SH'
#!/usr/bin/env bash
exit 0
SH
cat > "$GIG_DIR/scripts/cdp_nav_snapshot.py" <<'PY'
#!/usr/bin/env python3
raise SystemExit(0)
PY
cat > "$GIG_DIR/scripts/experiment_evaluator.py" <<'PY'
#!/usr/bin/env python3
raise SystemExit(0)
PY
chmod +x "$GIG_DIR/scripts/gig_selfimprove_verify.sh"
cat > "$HOME_DIR/life-manager/runtime/agent-runner/agent_runner.py" <<'PY'
#!/usr/bin/env python3
import hashlib, json, os, sys
from pathlib import Path

args = sys.argv[1:]
label = args[args.index("--task-label") + 1].removeprefix("gig-")
evidence = Path(args[args.index("--evidence-dir") + 1])
evidence.mkdir(parents=True, exist_ok=True)
Path(os.environ["GIG_TEST_RUNNER_LOG"]).open("a", encoding="utf-8").write(label + "\n")
fail_label = os.environ.get("GIG_TEST_FAIL_LABEL")
fail_once = os.environ.get("GIG_TEST_FAIL_ONCE_FILE")
if label == fail_label and fail_once and not Path(fail_once).exists():
    Path(fail_once).touch()
    raise SystemExit(42)
if label == "B0":
    context_path=evidence.parent/"b0-context.json"
    result_path=evidence/"attempt-01.result.json"
    result_path.write_text(json.dumps({
        "status":"ok","summary":"B0 fixture noop","evidence":["fresh storefront check"],
        "current_b0":{
            "context_path":str(context_path),
            "context_sha256":hashlib.sha256(context_path.read_bytes()).hexdigest(),
            "action":"verified_noop","service_id":None,"url":None,"title":None,
            "screenshot_path":None,"live_dom_path":None,"reason":"fixture noop"
        }
    })+"\n")
    (evidence/"summary.json").write_text(json.dumps({
        "status":"success","task_label":"gig-B0","result_path":str(result_path)
    })+"\n")
elif label == "B1":
    context_path=evidence.parent/"b1-context.json"; context=json.loads(context_path.read_text())
    inbox_shot=evidence/"inbox.png"; inbox_shot.write_bytes(b"png")
    inbox_dom=evidence/"inbox.json"; inbox_dom.write_text(json.dumps({"url":context["inbox_url"],"not_found":False,"observed":True})+"\n")
    result_path=evidence/"attempt-01.result.json"
    result_path.write_text(json.dumps({"status":"ok","summary":"empty B1 fixture sweep","evidence":["fresh inbox"],"current_b1":{"context_path":str(context_path),"context_sha256":hashlib.sha256(context_path.read_bytes()).hexdigest(),"inbox_url":context["inbox_url"],"inbox_status":"ok","inbox_screenshot_path":str(inbox_shot),"inbox_live_dom_path":str(inbox_dom),"inspected_talkrooms":[]}})+"\n")
    (evidence/"summary.json").write_text(json.dumps({"status":"success","task_label":"gig-B1","result_path":str(result_path)})+"\n")
elif label == "B2":
    prompt = Path(args[args.index("--prompt-file") + 1]).read_text(encoding="utf-8")
    context_path = Path(prompt.split("context_path=", 1)[1].split(" and context_sha256=", 1)[0])
    context = json.loads(context_path.read_text())
    market_url = "https://coconala.com/requests?sort=new"
    market_shot = evidence / "requests.png"; market_shot.write_bytes(b"png")
    market_dom = evidence / "requests.json"
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
    result_path = evidence / "attempt-01.result.json"
    result_path.write_text(json.dumps({
        "status":"ok","summary":"empty B2 fixture sweep","evidence":[str(market_dom)],
        "eligible_count":0,"applications":[],
        "current_b2":{
            "context_path":str(context_path),
            "context_sha256":hashlib.sha256(context_path.read_bytes()).hexdigest(),
            "marketplace_url":market_url,
            "marketplace_screenshot_path":str(market_shot),
            "marketplace_live_dom_path":str(market_dom),
            "inspected_requests":[],
            "search_sources":search_sources
        }
    })+"\n")
    (evidence/"summary.json").write_text(json.dumps({
        "status":"success","task_label":"gig-B2","result_path":str(result_path)
    })+"\n")
elif label == "REFLECT":
    prompt = Path(args[args.index("--prompt-file") + 1]).read_text(encoding="utf-8")
    assert os.environ["GIG_REFLECT_PASS_ID"] in prompt
    current_pass = json.loads(os.environ["GIG_REFLECT_CONTEXT_JSON"])
    result_path = evidence / "attempt-01.result.json"
    result_path.write_text(json.dumps({
        "status": "ok", "summary": "cooldown fixture reflection",
        "current_pass": current_pass,
        "evidence": ["cooldown reflection evidence"],
    }) + "\n", encoding="utf-8")
    (evidence / "summary.json").write_text(json.dumps({
        "status": "success", "task_label": "gig-REFLECT", "result_path": str(result_path),
    }) + "\n", encoding="utf-8")
else:
    (evidence / "summary.json").write_text(json.dumps({"status": "success", "label": label}) + "\n", encoding="utf-8")
raise SystemExit(0)
PY
chmod +x "$HOME_DIR/life-manager/runtime/agent-runner/agent_runner.py"
mkdir -p "$HOME_DIR/life-manager/skills/browser/scripts"
cat > "$HOME_DIR/life-manager/skills/browser/scripts/cdp_context_lease.py" <<'PY'
#!/usr/bin/env python3
raise SystemExit(0)
PY
chmod +x "$HOME_DIR/life-manager/skills/browser/scripts/cdp_context_lease.py"

run_pass() {
  local now="$1" state_dir="$2" evidence="$3" err="$4";
  if HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/empty-snapshot.json" \
    GIG_TODAY=2026-07-21 GIG_LOCK_DIR="$TMP/lock-$now" GIG_EVIDENCE_DIR="$evidence" \
    GIG_STEP_COOLDOWN_STATE_DIR="$state_dir" GIG_STEP_COOLDOWN_NOW="$now" \
    GIG_B0_COOLDOWN_SECONDS=3600 GIG_PROFILE_COOLDOWN_SECONDS=86400 \
    GIG_TEST_RUNNER_LOG="$TMP/runner.log" \
    GIG_LEGACY_MAINTENANCE_ENABLED=1 GIG_MODEL_CALL_LIMIT=0 \
    bash "$GIG_DIR/gig_pass.sh" >"$TMP/out-$now" 2>"$err"; then
    return 0
  else
    return $?
  fi
}

run_pass 1000 "$TMP/cooldown" "$TMP/evidence-1" "$TMP/err-1"
python3 - "$HOME_DIR/gig/pass-report.jsonl" <<'PY'
import json, sys
row = json.loads(open(sys.argv[1], encoding="utf-8").read().splitlines()[-1])
assert row["steps_executed"] == ["B0", "PROFILE", "B1", "B2", "LEARN", "REFLECT"], row
assert row["steps_skipped_cooldown"] == [], row
PY
grep -q '^B0$' "$TMP/runner.log"
grep -q '^PROFILE$' "$TMP/runner.log"

run_pass 1000 "$TMP/cooldown" "$TMP/evidence-2" "$TMP/err-2"
test "$(grep -c '^B0$' "$TMP/runner.log")" -eq 1
test "$(grep -c '^PROFILE$' "$TMP/runner.log")" -eq 1
grep -q 'STEP B0 skipped (cooldown' "$TMP/err-2"
grep -q 'STEP PROFILE skipped (cooldown' "$TMP/err-2"
python3 - "$HOME_DIR/gig/pass-report.jsonl" <<'PY'
import json, sys
row = json.loads(open(sys.argv[1], encoding="utf-8").read().splitlines()[-1])
assert row["steps_executed"] == ["B1", "B2", "LEARN", "REFLECT"], row
assert row["steps_skipped_cooldown"] == ["B0", "PROFILE"], row
assert "B0" not in row["steps_executed"] and "PROFILE" not in row["steps_executed"], row
PY

run_pass 4600 "$TMP/cooldown" "$TMP/evidence-hourly" "$TMP/err-hourly"
test "$(grep -c '^B0$' "$TMP/runner.log")" -eq 2
test "$(grep -c '^PROFILE$' "$TMP/runner.log")" -eq 1
grep -q 'STEP PROFILE skipped (cooldown' "$TMP/err-hourly"

# B0 is a wall-clock hourly lane, not "sleep for 3600 seconds after success".
# A controlled run late in one hour must not suppress the next :00 natural wake.
BUCKET_STATE="$TMP/cooldown-hour-bucket"
run_pass 3500 "$BUCKET_STATE" "$TMP/evidence-bucket-first" "$TMP/err-bucket-first"
run_pass 3599 "$BUCKET_STATE" "$TMP/evidence-bucket-same" "$TMP/err-bucket-same"
python3 - "$HOME_DIR/gig/pass-report.jsonl" <<'PY'
import json, sys
row = json.loads(open(sys.argv[1], encoding="utf-8").read().splitlines()[-1])
assert "B0" in row["steps_skipped_cooldown"], row
PY
run_pass 3600 "$BUCKET_STATE" "$TMP/evidence-bucket-next" "$TMP/err-bucket-next"
python3 - "$HOME_DIR/gig/pass-report.jsonl" <<'PY'
import json, sys
row = json.loads(open(sys.argv[1], encoding="utf-8").read().splitlines()[-1])
assert "B0" in row["steps_executed"], row
assert "B0" not in row["steps_skipped_cooldown"], row
PY

run_pass 87400 "$TMP/cooldown" "$TMP/evidence-3" "$TMP/err-3"
test "$(grep -c '^B0$' "$TMP/runner.log")" -eq 5
test "$(grep -c '^PROFILE$' "$TMP/runner.log")" -eq 3
test "$(tr -d '\n' < "$TMP/cooldown/.b0-cooldown")" = 87400
test "$(tr -d '\n' < "$TMP/cooldown/.profile-cooldown")" = 87400

FAIL_STATE="$TMP/cooldown-failure"
set +e
GIG_TEST_FAIL_LABEL=B0 GIG_TEST_FAIL_ONCE_FILE="$TMP/fail-once" \
  run_pass 2000 "$FAIL_STATE" "$TMP/evidence-fail" "$TMP/err-fail"
fail_rc=$?
set -e
test "$fail_rc" -ne 0
test ! -e "$FAIL_STATE/.b0-cooldown"
unset GIG_TEST_FAIL_LABEL GIG_TEST_FAIL_ONCE_FILE
run_pass 2000 "$FAIL_STATE" "$TMP/evidence-retry" "$TMP/err-retry"
test -e "$FAIL_STATE/.b0-cooldown"

echo 'PASS: B0 executes hourly, PROFILE daily, skip reporting is honest, failed steps remain retryable'
