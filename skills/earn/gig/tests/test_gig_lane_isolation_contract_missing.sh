#!/usr/bin/env bash
# A13-1 (2026-08-01, SSOT section 0.1.3 blocker #1) failure injection: a paid
# order whose validation contract is MISSING on an ESTABLISHED project makes
# the PAID_WORK lane fail. Before this fix, `run_paid_work || exit 1` killed
# the whole pass and SCAN/APPLY/REPLY never ran (measured live: zero lane
# executions after 07-31 16:00 JST). Now the paid failure is isolated to its
# lane: B0/B1/B2 still get their turn, the failure row is durable, and the
# pass still ends nonzero with no success heartbeat -- isolation, not amnesty.
set -euo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d /tmp/gig-lane-isolation.XXXXXX)
trap 'rm -rf "$TMP"' EXIT
HOME_DIR="$TMP/home"
G="$HOME_DIR/life-manager/skills/earn/gig"
B="$HOME_DIR/anicca/skills/browser/scripts"
mkdir -p "$HOME_DIR/gig" "$G/scripts" "$G/schemas" "$G/config/connectors" \
  "$HOME_DIR/life-manager/skills/agent-runner" "$HOME_DIR/life-manager/lib" "$B"
for file in gig_pass.sh passprep.py strategy.default.json; do cp "$SKILL_DIR/$file" "$G/$file"; done
for file in delivery_queue.py delivery_cadence.py delivery_project.py project_ledger.py \
    delivery_identity.py paid_work_evidence.py artifact_judge.py ask_buyer.py buyer_voice.py paid_work_transaction.py \
    paid_work_contract_bootstrap.py paid_work_validation_contract.py paid_queue_evidence.py \
    reply_queue.py connector_outbox.py reconcile_paid_delivery.py paid_progress_ledger.py \
    paid_progress_finalize_gate.py cdp_lock.sh run_with_cdp_lock.sh \
    coconala_paid_progress_browser.py sync_gig_revenue_events.py gig_context_packet.py \
    b1_conversation_gate.py b0_objective.py b0_result_gate.py b2_queue_gate.py \
    b2_result_gate.py application_report.py normalize_applied.py lane_health.py \
    lane_state_machine.py lane_action_runtime.py lane_productivity.py listing_ledger.py \
    b2_wall_clock.py b2_objective.py b2_search_objective.py category_bandit.py \
    coconala_applied_readback.py experiment_evaluator.py lane_lessons.py; do
  cp "$SKILL_DIR/scripts/$file" "$G/scripts/$file"
done
printf '%s\n' '#!/usr/bin/env bash' 'exit 0' > "$G/scripts/gig_selfimprove_verify.sh"
chmod +x "$G/scripts/gig_selfimprove_verify.sh"
cp "$SKILL_DIR/../agent-runner/context_packet.py" "$HOME_DIR/life-manager/skills/agent-runner/context_packet.py"
cp "$SKILL_DIR/../../lib/unit_economics_events.py" "$HOME_DIR/life-manager/lib/unit_economics_events.py"
cp "$SKILL_DIR/config/connectors/coconala.json" "$G/config/connectors/coconala.json"
chmod +x "$G/scripts/run_with_cdp_lock.sh"
for schema in gig_step_result gig_b0_result gig_reflect_result gig_b1_result gig_b2_result artifact_judgement; do
  cp "$SKILL_DIR/schemas/$schema.schema.json" "$G/schemas/$schema.schema.json"
done
# Browser-lease stubs so B1/B2 can acquire and release their step contexts.
cat > "$B/cdp_context_lease.py" <<'PY'
raise SystemExit(0)
PY
: > "$G/scripts/cdp_nav_snapshot.py"

# ESTABLISHED project: a prior delivery exists in artifacts/ but the contract
# is GONE. The bootstrap must refuse to invent one (that is a real anomaly),
# so the paid lane fails -- the injected fault.
mkdir -p "$HOME_DIR/gig/projects/4201/artifacts" "$HOME_DIR/gig/projects/4201/delivery" \
  "$HOME_DIR/gig/projects/4201/requirements" "$HOME_DIR/gig/projects/4201/source"
printf 'x%.0s' $(seq 1 2048) > "$HOME_DIR/gig/projects/4201/artifacts/delivery-v2.zip"

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
cat > "$HOME_DIR/life-manager/skills/agent-runner/agent_runner.py" <<'PY'
#!/usr/bin/env python3
import hashlib, json, os, sys
from pathlib import Path
args = sys.argv[1:]
label = args[args.index("--task-label") + 1]
evidence = Path(args[args.index("--evidence-dir") + 1]); evidence.mkdir(parents=True, exist_ok=True)
prompt = Path(args[args.index("--prompt-file") + 1]).read_text(encoding="utf-8")
Path(os.environ["GIG_TEST_RUNNER_LOG"]).open("a", encoding="utf-8").write(label + "\n")
if label == "gig-PAID_WORK":
    # The injected fault fails BEFORE any model call; reaching here is a bug.
    raise SystemExit(99)
if label == "gig-B0":
    context_path = Path(prompt.split("context_path=", 1)[1].split(" and context_sha256=", 1)[0])
    service_id = "9000001"
    url = f"https://coconala.com/services/{service_id}"
    shot = evidence / "listing.png"; shot.write_bytes(b"png")
    dom = evidence / "listing.json"
    dom.write_text(json.dumps({"url":url,"not_found":False,"observed":True,"title":"Fixture listing"})+"\n")
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
    (evidence / "summary.json").write_text(json.dumps({"status":"success","task_label":label,"result_path":str(result)})+"\n")
    raise SystemExit(0)
if label == "gig-B1":
    context_path = Path(prompt.split("context_path=", 1)[1].split(" and context_sha256=", 1)[0])
    context = json.loads(context_path.read_text(encoding="utf-8"))
    inbox_shot = evidence / "inbox.png"; inbox_shot.write_bytes(b"png")
    inbox_dom = evidence / "inbox.json"
    inbox_dom.write_text(json.dumps({"url":"https://coconala.com/message?fromMyPage=true","not_found":False,"observed":True})+"\n")
    inspected = []
    for row in context.get("actionable_talkrooms", []):
        tid = str(row["talkroom_id"])
        shot = evidence / f"talkroom-{tid}.png"; shot.write_bytes(b"png")
        live = evidence / f"talkroom-{tid}.json"
        live.write_text(json.dumps({"url":row["url"],"not_found":False,"observed":True})+"\n")
        inspected.append({"talkroom_id":tid,"url":row["url"],"outcome":"observed_no_action",
            "screenshot_path":str(shot),"live_dom_path":str(live)})
    result = evidence / "attempt-01.result.json"
    result.write_text(json.dumps({
        "status":"ok","summary":"hourly reply lane inspected","evidence":[str(inbox_dom)],
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
    (evidence / "summary.json").write_text(json.dumps({"status":"success","task_label":label,"result_path":str(result)})+"\n")
    raise SystemExit(0)
if label == "gig-B2":
    context_path = Path(prompt.split("context_path=", 1)[1].split(" and context_sha256=", 1)[0])
    context = json.loads(context_path.read_text(encoding="utf-8"))
    dom = evidence / "jobs.json"
    dom.write_text(json.dumps({"url":"https://coconala.com/job_matching/requests","not_found":False,"observed":True,"eligible_count":0})+"\n")
    shot = evidence / "jobs.png"; shot.write_bytes(b"fresh marketplace screenshot")
    search_sources = []
    for index, source_id in enumerate(context["required_search_source_ids"]):
        source_url = "https://coconala.com/job_matching/requests" if source_id == "single:new" else f"https://coconala.com/requests?source={index}"
        source_shot = evidence / f"search-{index}.png"; source_shot.write_bytes(b"png")
        source_dom = evidence / f"search-{index}.json"
        source_dom.write_text(json.dumps({"url":source_url,"not_found":False,"observed":True})+"\n")
        search_sources.append({"source_id":source_id,"url":source_url,
            "screenshot_path":str(source_shot),"live_dom_path":str(source_dom),
            "inspected_count":1,"has_next":False,"exhausted":True})
    result = evidence / "attempt-01.result.json"
    result.write_text(json.dumps({
        "status":"ok","summary":"no eligible new jobs","evidence":[str(dom)],
        "eligible_count":0,"applications":[],
        "current_b2":{
            "context_path":str(context_path),
            "context_sha256":hashlib.sha256(context_path.read_bytes()).hexdigest(),
            "marketplace_url":"https://coconala.com/job_matching/requests",
            "marketplace_screenshot_path":str(shot),
            "marketplace_live_dom_path":str(dom),
            "inspected_requests":[],
            "search_sources":search_sources
        }
    })+"\n")
    (evidence / "summary.json").write_text(json.dumps({"status":"success","task_label":label,"result_path":str(result)})+"\n")
    raise SystemExit(0)
(evidence / "summary.json").write_text(json.dumps({"status":"success","task_label":label})+"\n")
raise SystemExit(0)
PY
chmod +x "$HOME_DIR/life-manager/skills/agent-runner/agent_runner.py"
cat > "$TMP/fake-validation-docker" <<'SH'
#!/usr/bin/env bash
printf '%s\n' '{"status":"PASS","errors":[]}'
SH
chmod +x "$TMP/fake-validation-docker"
export GIG_PAID_VALIDATOR_DOCKER="$TMP/fake-validation-docker"

set +e
HOME="$HOME_DIR" GIG_WORKER_LEASE_ACTIVE=1 GIG_QUEUE_FIXTURE="$TMP/snapshot.json" \
  GIG_TODAY=2026-07-22 GIG_LOCK_DIR="$TMP/lock.d" GIG_EVIDENCE_DIR="$TMP/evidence" \
  GIG_TEST_CDP_ALIVE=1 GIG_TEST_RUNNER_LOG="$TMP/runner.log" \
  GIG_PASS_ID="lane-isolation" \
  bash "$G/gig_pass.sh" >"$TMP/out" 2>"$TMP/err"
rc=$?
set -e

# 1. Isolation is not amnesty: the pass still ends nonzero.
test "$rc" -ne 0

# 2. The paid failure is durable with lane + reason on the status jsonl.
grep -q '"failed_step":"PAID_WORK"' "$HOME_DIR/gig/pass-failures.jsonl"
grep -q 'paid_work_contract_bootstrap_failed' "$HOME_DIR/gig/pass-failures.jsonl"

# 3. The paid lane was isolated, and the fault fired before any paid model call.
grep -q 'LANE PAID_WORK isolated' "$TMP/err"
! grep -q '^gig-PAID_WORK$' "$TMP/runner.log"

# 4. THE POINT: the sibling revenue lanes still got their turn in the SAME pass.
for lane in gig-B0 gig-B1 gig-B2; do
  grep -qx "$lane" "$TMP/runner.log" || {
    echo "RED: paid failure starved $lane: $(tr '\n' ',' < "$TMP/runner.log")" >&2
    exit 1
  }
done

# 5. The deferred verdict names the isolated lane and lists what executed.
grep -q 'pass failed (step=LANE' "$TMP/err"
grep -Eq 'pass failed \(step=LANE reason=[a-z_]+ lanes=.*PAID_WORK' "$TMP/err"

# 6. No success heartbeat for a pass with an isolated lane failure.
test ! -s "$HOME_DIR/gig/.last-pass"

# 7. The bootstrap refused to invent a contract for an established project.
test ! -e "$HOME_DIR/gig/projects/4201/delivery/validation-contract.json"

echo 'PASS: a missing contract fails only the paid lane; B0/B1/B2 still run and the pass ends nonzero'
