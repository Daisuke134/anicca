#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
SOURCE_DIR="${GIG_SOURCE_DIR:-$SKILL_DIR}"
TMP=$(mktemp -d /tmp/gig-reflect-contract.XXXXXX)
trap 'if [ "${KEEP_TMP:-0}" = 1 ]; then echo "KEEP_TMP=$TMP"; else rm -rf "$TMP"; fi' EXIT
HOME_DIR="$TMP/home"
GIG_DIR="$HOME_DIR/life-manager/skills/earn/gig"
mkdir -p "$GIG_DIR/scripts" "$GIG_DIR/schemas" "$GIG_DIR/config/connectors" \
  "$HOME_DIR/life-manager/runtime/agent-runner" \
  "$HOME_DIR/life-manager/skills/browser/scripts" "$HOME_DIR/gig"
cp "$SOURCE_DIR/gig_pass.sh" "$GIG_DIR/gig_pass.sh"
cp "$SOURCE_DIR/scripts/gig_paths.sh" "$GIG_DIR/scripts/gig_paths.sh"
cp "$SOURCE_DIR/passprep.py" "$GIG_DIR/passprep.py"
cp "$SOURCE_DIR/strategy.default.json" "$GIG_DIR/strategy.default.json"
cp "$SOURCE_DIR/scripts/delivery_queue.py" "$GIG_DIR/scripts/delivery_queue.py"
cp "$SOURCE_DIR/scripts/delivery_cadence.py" "$GIG_DIR/scripts/delivery_cadence.py"
cp "$SOURCE_DIR/scripts/delivery_identity.py" "$GIG_DIR/scripts/delivery_identity.py"
cp "$SOURCE_DIR/scripts/reply_queue.py" "$GIG_DIR/scripts/reply_queue.py"
cp "$SOURCE_DIR/scripts/connector_outbox.py" "$GIG_DIR/scripts/connector_outbox.py"
cp "$SOURCE_DIR/config/connectors/coconala.json" "$GIG_DIR/config/connectors/coconala.json"
cp "$SOURCE_DIR/scripts/b2_queue_gate.py" "$GIG_DIR/scripts/b2_queue_gate.py"
cp "$SOURCE_DIR/scripts/b2_result_gate.py" "$GIG_DIR/scripts/b2_result_gate.py"
cp "$SOURCE_DIR/scripts/application_report.py" "$GIG_DIR/scripts/application_report.py"
cp "$SOURCE_DIR/scripts/normalize_applied.py" "$GIG_DIR/scripts/normalize_applied.py"
cp "$SOURCE_DIR/scripts/cdp_nav_snapshot.py" "$GIG_DIR/scripts/cdp_nav_snapshot.py"
cp "$SOURCE_DIR/scripts/b2_wall_clock.py" "$GIG_DIR/scripts/b2_wall_clock.py"
cp "$SOURCE_DIR/scripts/b2_search_objective.py" "$GIG_DIR/scripts/b2_search_objective.py"
cp "$SOURCE_DIR/scripts/b1_conversation_gate.py" "$GIG_DIR/scripts/b1_conversation_gate.py"
cp "$SOURCE_DIR/scripts/b0_result_gate.py" "$GIG_DIR/scripts/b0_result_gate.py"
cp "$SOURCE_DIR/schemas/gig_step_result.schema.json" "$GIG_DIR/schemas/gig_step_result.schema.json"
cp "$SOURCE_DIR/schemas/gig_b0_result.schema.json" "$GIG_DIR/schemas/gig_b0_result.schema.json"
cp "$SOURCE_DIR/schemas/gig_reflect_result.schema.json" "$GIG_DIR/schemas/gig_reflect_result.schema.json"
cp "$SOURCE_DIR/schemas/gig_b1_result.schema.json" "$GIG_DIR/schemas/gig_b1_result.schema.json"
cp "$SOURCE_DIR/schemas/gig_b2_result.schema.json" "$GIG_DIR/schemas/gig_b2_result.schema.json"
printf '%s\n' '{"captured_at":"2026-07-22T00:00:00Z","inbox":{"url":"https://coconala.com/message?fromMyPage=true","not_found":false},"orders":[],"quotes":[],"inquiries":[]}' > "$TMP/empty-snapshot.json"
cat > "$GIG_DIR/scripts/gig_selfimprove_verify.sh" <<'SH'
#!/usr/bin/env bash
exit 0
SH
cat > "$GIG_DIR/scripts/experiment_evaluator.py" <<'PY'
#!/usr/bin/env python3
raise SystemExit(0)
PY
chmod +x "$GIG_DIR/scripts/gig_selfimprove_verify.sh"
cat > "$HOME_DIR/life-manager/skills/browser/scripts/cdp_context_lease.py" <<'PY'
#!/usr/bin/env python3
raise SystemExit(0)
PY
cat > "$HOME_DIR/life-manager/runtime/agent-runner/agent_runner.py" <<'PY'
#!/usr/bin/env python3
import hashlib, json, os, subprocess, sys
from pathlib import Path

args = sys.argv[1:]
label = args[args.index("--task-label") + 1].removeprefix("gig-")
evidence = Path(args[args.index("--evidence-dir") + 1])
evidence.mkdir(parents=True, exist_ok=True)
prompt = Path(args[args.index("--prompt-file") + 1]).read_text(encoding="utf-8")
if label in {"LEARN", "B1", "B2", "REFLECT"}:
    assert "GIG_PASS_RUNBOOK.md" not in prompt, (label, prompt)
    for required in (
        f"Bounded step ownership for {label}",
        f"Allowed actions for {label}",
        f"Forbidden for {label}",
        "Do not run gig_single_instance.sh",
        "Do not run passprep.py",
        "Do not execute another Gig step",
        "Do not write pass-report.jsonl or .last-pass",
        "Do not perform top-level finalize or heartbeat",
        "Do not rewrite or truncate existing JSONL files",
        "append one compact JSON row",
    ):
        assert required in prompt, (label, required, prompt)
if label in {"B1", "B2"}:
    for required in (
        "authenticated CloakBrowser daily-driver",
        "/life-manager/skills/browser/SKILL.md",
        "step-owned context lease",
        "Parent code already acquired",
        "ANICCA_BROWSER_LEASE",
        "Do not run cdp_context_lease.py release",
        "Parent code releases this exact context only after this agent exits",
        'cdp_nav_snapshot.py observe --lease "$ANICCA_BROWSER_LEASE"',
        "Do not copy or transcribe the opaque page websocket",
        "NEVER run agent-browser tab new",
        "Do not use agent-browser for leased-target navigation",
        "do not create a browser profile",
        "marketplace",
    ):
        assert required in prompt, (label, required, prompt)
    assert "agent-browser SKILL.md" not in prompt, (label, prompt)
    assert f"-{label}" in prompt, (label, prompt)
if label == "B0":
    schema_path = Path(args[args.index("--schema") + 1])
    assert schema_path.name == "gig_b0_result.schema.json", schema_path
    assert "Do not write any ledger" in prompt
    context_path=evidence.parent/"b0-context.json"
    result_path=evidence/"attempt-01.result.json"
    result_path.write_text(json.dumps({
        "status":"ok","summary":"bounded B0 fixture","evidence":["fresh storefront check"],
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
    schema_path = Path(args[args.index("--schema") + 1])
    assert schema_path.name == "gig_b1_result.schema.json", schema_path
    assert "https://coconala.com/message?fromMyPage=true" in prompt
    assert "/mypage/messages" not in prompt
    assert "Inspect every actionable_talkrooms row exactly once" in prompt
    context_path=evidence.parent/"b1-context.json"; context=json.loads(context_path.read_text())
    inbox_shot=evidence/"inbox.png"; inbox_shot.write_bytes(b"png")
    inbox_dom=evidence/"inbox.json"; inbox_dom.write_text(json.dumps({"url":context["inbox_url"],"not_found":False,"observed":True})+"\n")
    result_path=evidence/"attempt-01.result.json"
    result_path.write_text(json.dumps({"status":"ok","summary":"bounded B1 fixture","evidence":["fresh inbox"],"current_b1":{"context_path":str(context_path),"context_sha256":hashlib.sha256(context_path.read_bytes()).hexdigest(),"inbox_url":context["inbox_url"],"inbox_status":"ok","inbox_screenshot_path":str(inbox_shot),"inbox_live_dom_path":str(inbox_dom),"inspected_talkrooms":[]}})+"\n")
    (evidence/"summary.json").write_text(json.dumps({"status":"success","task_label":"gig-B1","result_path":str(result_path)})+"\n")
elif label == "B2":
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
        "status":"ok","summary":"bounded B2 fixture","evidence":[str(market_dom)],
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
    schema_path = Path(args[args.index("--schema") + 1])
    assert schema_path.name == "gig_reflect_result.schema.json", schema_path
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert "current_pass" in schema["required"], schema
    current_pass_schema = schema["properties"]["current_pass"]
    assert set(current_pass_schema["required"]) == {
        "pass_id", "queue_path", "evidence_dir", "steps_executed", "steps_skipped_cooldown",
        "steps_skipped_policy",
    }, current_pass_schema
    assert current_pass_schema["additionalProperties"] is False, current_pass_schema
    assert "non-recursive" in prompt
    assert '"pass_id":"' + os.environ["GIG_REFLECT_PASS_ID"] + '"' in prompt
    assert '"queue_path":"' + os.environ["GIG_REFLECT_QUEUE_PATH"] + '"' in prompt
    assert '"steps_executed":["B0","PROFILE","B1","B2","LEARN"]' in prompt
    assert '"steps_skipped_cooldown":[]' in prompt
    assert '"steps_skipped_policy":[]' in prompt
    assert "structured current_pass" in prompt
    assert "Include evidence entries exactly" not in prompt
    assert "<absolute_path>: <description>" in prompt
    assert "ASCII colon immediately after the filename" in prompt
    assert "<path> は" in prompt and "invalid" in prompt
    ledger_paths = [
        Path.home() / "gig" / "pass-report.jsonl",
        Path.home() / "gig" / "reflections.jsonl",
        Path.home() / "gig" / ".last-pass",
    ]
    before_ledgers = [(path.exists(), path.read_bytes() if path.exists() else None) for path in ledger_paths]
    child = subprocess.run(["bash", os.environ["GIG_REFLECT_SCRIPT"]], text=True, capture_output=True)
    assert child.returncode == 97, (child.returncode, child.stderr)
    assert "before lock/browser" in child.stderr
    after_ledgers = [(path.exists(), path.read_bytes() if path.exists() else None) for path in ledger_paths]
    assert after_ledgers == before_ledgers, (before_ledgers, after_ledgers)
    Path(os.environ["GIG_TEST_RECURSION_LOG"]).write_text(child.stderr, encoding="utf-8")
    pass_id = os.environ["GIG_REFLECT_PASS_ID"]
    bad_mode = os.environ.get("GIG_REFLECT_BAD")
    if bad_mode in ("1", "wrong-pass"):
        pass_id = "wrong-pass"
    queue_path = os.environ["GIG_REFLECT_QUEUE_PATH"]
    evidence_dir = os.environ["GIG_REFLECT_EVIDENCE_DIR"]
    steps_executed = ["B0", "PROFILE", "B1", "B2", "LEARN"]
    if bad_mode == "wrong-queue":
        queue_path = str(Path(os.environ["GIG_REFLECT_EVIDENCE_DIR"]).parent / "not-current-queue.json")
    elif bad_mode == "wrong-evidence":
        evidence_dir = str(Path(os.environ["GIG_REFLECT_EVIDENCE_DIR"]).parent / "not-current-evidence")
    elif bad_mode == "wrong-steps":
        steps_executed = ["B0", "PROFILE"]
    local_evidence = evidence / "current-pass-evidence.json"
    local_evidence.write_text(json.dumps({"pass_id": pass_id}) + "\n", encoding="utf-8")
    reflection_evidence = [f"{local_evidence}: current-pass fixture evidence"]
    if bad_mode == "missing-local-evidence":
        reflection_evidence = [f"{evidence / 'missing-evidence.json'}: fabricated local evidence"]
    elif bad_mode == "escaped-local-evidence":
        escaped = evidence.parent.parent / "escaped-evidence.json"
        escaped.write_text('{"escaped":true}\n', encoding="utf-8")
        reflection_evidence = [f"{escaped}: evidence outside the current pass"]
    elif bad_mode == "stale-local-evidence":
        stale = evidence / "stale-evidence.json"
        stale.write_text('{"stale":true}\n', encoding="utf-8")
        os.utime(stale, (1, 1))
        reflection_evidence = [f"{stale}: stale local evidence"]
    result_path = evidence / "attempt-01.result.json"
    current_pass = {
        "pass_id": pass_id,
        "queue_path": queue_path,
        "evidence_dir": evidence_dir,
        "steps_executed": steps_executed,
        "steps_skipped_cooldown": [],
        "steps_skipped_policy": [],
    }
    result_path.write_text(json.dumps({
        "status": "ok", "summary": "deterministic reflection fixture",
        "current_pass": current_pass,
        "evidence": reflection_evidence,
    }) + "\n", encoding="utf-8")
    (evidence / "summary.json").write_text(json.dumps({
        "status": "success", "task_label": "gig-REFLECT", "result_path": str(result_path),
    }) + "\n", encoding="utf-8")
else:
    (evidence / "summary.json").write_text(json.dumps({"status": "success", "label": label}) + "\n", encoding="utf-8")
raise SystemExit(0)
PY
chmod +x "$HOME_DIR/life-manager/runtime/agent-runner/agent_runner.py"

run_pass() {
  local pass_id="$1" bad="$2"
  local evidence="$TMP/evidence-$pass_id" lock="$TMP/lock-$pass_id"
  if ! env HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/empty-snapshot.json" \
    GIG_TODAY=2026-07-22 GIG_LOCK_DIR="$lock" GIG_EVIDENCE_DIR="$evidence" \
    GIG_STEP_COOLDOWN_STATE_DIR="$TMP/cooldown-$pass_id" GIG_STEP_COOLDOWN_NOW=1000 \
    GIG_STEP_COOLDOWN_SECONDS=86400 GIG_PASS_ID="$pass_id" GIG_REFLECT_SCRIPT="$GIG_DIR/gig_pass.sh" \
    GIG_REFLECT_BAD="$bad" GIG_TEST_RECURSION_LOG="$TMP/recursive.log" \
    GIG_LEGACY_MAINTENANCE_ENABLED=1 GIG_MODEL_CALL_LIMIT=0 \
    bash "$GIG_DIR/gig_pass.sh" >"$TMP/out-$pass_id" 2>"$TMP/err-$pass_id"; then
    cat "$TMP/err-$pass_id" >&2
    return 1
  fi
}

printf '%s\n' 'legacy plaintext heartbeat' > "$HOME_DIR/gig/.last-pass"
run_pass reflect-e2e 0
test -f "$HOME_DIR/gig/.last-pass"
python3 - "$HOME_DIR/gig/pass-report.jsonl" "$HOME_DIR/gig/.last-pass" "$HOME_DIR/gig/reflections.jsonl" <<'PY'
import json, sys
report, heartbeat, ledger = sys.argv[1:]
report_bytes = open(report, "rb").read()
rows = [json.loads(line) for line in report_bytes.decode("utf-8").splitlines() if line.strip()]
assert rows and rows[-1]["status"] == "success", rows
row = rows[-1]
assert row["pass_id"] == "reflect-e2e"
assert row["steps"] == ["B0", "PROFILE", "B1", "B2", "LEARN", "REFLECT"], row
assert row["steps_executed"] == row["steps"] and row["steps_skipped_cooldown"] == [] and row["steps_skipped_policy"] == [], row
assert json.load(open(heartbeat, encoding="utf-8")) == row
assert open(heartbeat, "rb").read() == (report_bytes.splitlines()[-1] + b"\n")
reflection_rows = [json.loads(line) for line in open(ledger, encoding="utf-8") if line.strip()]
assert len(reflection_rows) == 1 and reflection_rows[0]["pass_id"] == row["pass_id"], reflection_rows
assert reflection_rows[0]["queue_path"].endswith("/delivery-queue.json"), reflection_rows
assert reflection_rows[0]["current_pass"]["pass_id"] == row["pass_id"], reflection_rows
assert reflection_rows[0]["current_pass"]["steps_skipped_policy"] == [], reflection_rows
PY
before_report=$(wc -l < "$HOME_DIR/gig/pass-report.jsonl")
before_reflections=$(wc -l < "$HOME_DIR/gig/reflections.jsonl")
before_heartbeat=$(python3 -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1])),sort_keys=True,separators=(",",":")))' "$HOME_DIR/gig/.last-pass")
set +e
run_pass reflect-bad 1
bad_rc=$?
set -e
test "$bad_rc" -ne 0
test "$(wc -l < "$HOME_DIR/gig/pass-report.jsonl")" -eq "$before_report"
test "$(wc -l < "$HOME_DIR/gig/reflections.jsonl")" -eq "$before_reflections"
test "$(python3 -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1])),sort_keys=True,separators=(",",":")))' "$HOME_DIR/gig/.last-pass")" = "$before_heartbeat"
grep -q 'reflect_validation_or_ledger_failed' "$HOME_DIR/gig/pass-failures.jsonl"
grep -q 'recursive gig_pass invocation refused before lock/browser' "$TMP/recursive.log"

for bad_mode in wrong-queue wrong-evidence wrong-steps; do
  before_report=$(wc -l < "$HOME_DIR/gig/pass-report.jsonl")
  before_reflections=$(wc -l < "$HOME_DIR/gig/reflections.jsonl")
  set +e
  run_pass "reflect-$bad_mode" "$bad_mode"
  bad_rc=$?
  set -e
  test "$bad_rc" -ne 0
  test "$(wc -l < "$HOME_DIR/gig/pass-report.jsonl")" -eq "$before_report"
  test "$(wc -l < "$HOME_DIR/gig/reflections.jsonl")" -eq "$before_reflections"
done

for bad_mode in missing-local-evidence escaped-local-evidence stale-local-evidence; do
  before_report=$(wc -l < "$HOME_DIR/gig/pass-report.jsonl")
  before_reflections=$(wc -l < "$HOME_DIR/gig/reflections.jsonl")
  set +e
  run_pass "reflect-$bad_mode" "$bad_mode"
  bad_rc=$?
  set -e
  test "$bad_rc" -ne 0
  test "$(wc -l < "$HOME_DIR/gig/pass-report.jsonl")" -eq "$before_report"
  test "$(wc -l < "$HOME_DIR/gig/reflections.jsonl")" -eq "$before_reflections"
  grep -q 'reflection evidence local path' "$TMP/err-reflect-$bad_mode"
done

before_report=$(wc -l < "$HOME_DIR/gig/pass-report.jsonl")
before_reflections=$(wc -l < "$HOME_DIR/gig/reflections.jsonl")
concurrent_heartbeat='{"writer":"concurrent-test","status":"in-progress"}'
(
  sleep 0.05
  printf '%s\n' "$concurrent_heartbeat" > "$HOME_DIR/gig/.last-pass"
) &
writer_pid=$!
set +e
GIG_TEST_FINALIZE_PAUSE_AFTER_REPORT_MS=200 GIG_TEST_FAIL_HEARTBEAT_WRITE=1 run_pass reflect-finalize-fail 0
finalize_rc=$?
set -e
wait "$writer_pid"
test "$finalize_rc" -ne 0
test "$(wc -l < "$HOME_DIR/gig/pass-report.jsonl")" -eq "$before_report"
test "$(wc -l < "$HOME_DIR/gig/reflections.jsonl")" -eq "$before_reflections"
test "$(cat "$HOME_DIR/gig/.last-pass")" = "$concurrent_heartbeat"
grep -q 'success_report_or_heartbeat_write_failed' "$TMP/err-reflect-finalize-fail"

echo 'PASS: REFLECT structured binding, stale/entity gates, recursion isolation, legacy heartbeat replacement, and transactional rollback verified'
