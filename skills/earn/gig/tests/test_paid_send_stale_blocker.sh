#!/usr/bin/env bash
set -euo pipefail

# Regression contract for the live 2026-08-10 shape: the deterministic browser
# has verified a buyer-visible send, but TOP_JSON still carries the blocker that
# was collected before that send.  The evidence gate is the only authority that
# may clear it; observe-only and model-only outcomes must leave it in place.
SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
PASS="$SKILL_DIR/gig_pass.sh"
TMP=$(mktemp -d /tmp/gig-paid-send-stale-blocker.XXXXXX)
trap 'rm -rf "$TMP"' EXIT

extract() {
  sed -n "/^$1() {/,/^}$/p" "$PASS"
}

HOME_DIR="$TMP/home"
G="$TMP/gig-work"
mkdir -p "$HOME_DIR/gig" "$HOME_DIR/anicca/skills/browser" "$G/scripts"
printf '%s\n' 'browser fixture' > "$HOME_DIR/anicca/skills/browser/SKILL.md"

# Keep the test at the shipped function boundary.  The browser and validators
# below are inert fixtures; no Coconala/browser action is possible here.
HARNESS="$TMP/harness.sh"
{
  printf 'set -uo pipefail\n'
  cat <<'STUBS'
log() { :; }
require_cdp_health() { return 0; }
claim_model_call() { return 0; }
record_failure() { LAST_FAILURE_REASON="$1"; printf 'record_failure:%s\n' "$1" >&2; }
STEP_EXECUTED=()
LAST_FAILURE_REASON=""
STUBS
  extract assess_paid_queue
} > "$HARNESS"

cat > "$G/scripts/run_with_cdp_lock.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
shift 2
test "${1:-}" = --
shift
exec "$@"
SH
chmod +x "$G/scripts/run_with_cdp_lock.sh"

cat > "$G/scripts/domain_skills.py" <<'PY'
print("")
PY

cat > "$G/scripts/step_result_status.py" <<'PY'
import os
print("blocked" if os.environ.get("CASE") == "model_self_report" else "ok")
PY

cat > "$G/scripts/paid_queue_evidence.py" <<'PY'
import os
import sys

# A valid observe-only manifest is accepted, while the two non-authoritative
# cases intentionally fail the deterministic validator.
raise SystemExit(0 if os.environ.get("CASE") in {"verified_send", "observe_only"} else 1)
PY

cat > "$G/scripts/gig_context_packet.py" <<'PY'
print('{"kind":"gig_paid_delivery"}')
PY

cat > "$TMP/fake_progress_browser.py" <<'PY'
import argparse
import json
import os
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--evidence-dir", type=Path, required=True)
args, _ = parser.parse_known_args()
args.evidence_dir.mkdir(parents=True, exist_ok=True)
sent = os.environ.get("CASE") == "verified_send"
live = args.evidence_dir / "live-dom.json"
live.write_text(json.dumps({"sent": sent}) + "\n", encoding="utf-8")
(args.evidence_dir / "paid-queue-evidence.json").write_text(
    json.dumps({"sent": sent, "live_dom_path": str(live)}) + "\n",
    encoding="utf-8",
)
PY

cat > "$TMP/fake_model_runner.py" <<'PY'
import argparse
import json
import os
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--evidence-dir", type=Path, required=True)
args, _ = parser.parse_known_args()
args.evidence_dir.mkdir(parents=True, exist_ok=True)
if os.environ.get("CASE") == "observe_only":
    live = args.evidence_dir / "live-dom.json"
    live.write_text(json.dumps({"sent": False}) + "\n", encoding="utf-8")
    (args.evidence_dir / "paid-queue-evidence.json").write_text(
        json.dumps({"sent": False, "live_dom_path": str(live)}) + "\n",
        encoding="utf-8",
    )
(args.evidence_dir / "summary.json").write_text(
    json.dumps({"status": "success"}) + "\n", encoding="utf-8"
)
PY

chmod +x "$TMP/fake_progress_browser.py" "$TMP/fake_model_runner.py"

# Load the production function after all fixture scripts exist.
. "$HARNESS"

run_case() {
  local name="$1" action="$2" blockers_json="$3"
  local root="$TMP/$name"
  mkdir -p "$root/evidence" "$root/project/delivery"
  printf '{}\n' > "$root/project/delivery/paid-work-result.json"

  export CASE="$name" HOME="$HOME_DIR" G EVIDENCE_DIR="$root/evidence"
  export TOP_PROJECT_ROOT="$root/project" PASS_START_EPOCH=1
  export TOP_ACTION="$action" TOP_CLASS=buyer_feedback_or_revision TOP_ID=5204226
  export TOP_TALKROOM_URL=https://coconala.com/talkrooms/5204226
  export RUNNER="$TMP/fake_model_runner.py" SCHEMA="$TMP/schema.json"
  export GIG_PAID_PROGRESS_BROWSER="$TMP/fake_progress_browser.py"
  export TOP_JSON
  TOP_JSON=$(python3 - "$action" "$blockers_json" <<'PY'
import json
import sys
print(json.dumps({
    "talkroom_id": "5204226",
    "queue_class": "buyer_feedback_or_revision",
    "delivery_action": sys.argv[1],
    "blockers": json.loads(sys.argv[2]),
}, separators=(",", ":")))
PY
  )
  TOP_BLOCKERS=$(python3 - "$blockers_json" <<'PY'
import json
import sys
print(",".join(json.loads(sys.argv[1])))
PY
  )

  local rc=0
  assess_paid_queue >"$root/stdout" 2>"$root/stderr" || rc=$?
  printf 'rc=%s\nTOP_BLOCKERS=%s\nTOP_JSON=%s\n' "$rc" "$TOP_BLOCKERS" "$TOP_JSON"
}

FORMAL='["formal_delivery_not_confirmed"]'
FORMAL_AND_OTHER='["formal_delivery_not_confirmed","other_blocker"]'

# Verified send: only the deterministic evidence gate may clear the stale
# blocker, and an unrelated blocker survives for the next gate.
RESULT=$(run_case verified_send progress "$FORMAL_AND_OTHER")
printf '%s\n' "$RESULT" | grep -qx 'rc=0'
printf '%s\n' "$RESULT" | grep -qx 'TOP_BLOCKERS=other_blocker'
VERIFIED_JSON=$(printf '%s\n' "$RESULT" | sed -n 's/^TOP_JSON=//p')
python3 - "$VERIFIED_JSON" <<'PY'
import json
import sys
assert json.loads(sys.argv[1])["blockers"] == ["other_blocker"]
PY

# Observe-only: a valid sent=false manifest is not permission to mutate the
# queue's formal-delivery blocker.
RESULT=$(run_case observe_only none "$FORMAL")
printf '%s\n' "$RESULT" | grep -qx 'rc=0'
printf '%s\n' "$RESULT" | grep -qx 'TOP_BLOCKERS=formal_delivery_not_confirmed'

# Unverified evidence and a model self-report both fail closed and retain the
# stale blocker; neither can authorize a second buyer-visible action.
RESULT=$(run_case unverified progress "$FORMAL")
printf '%s\n' "$RESULT" | grep -qx 'rc=1'
printf '%s\n' "$RESULT" | grep -qx 'TOP_BLOCKERS=formal_delivery_not_confirmed'
RESULT=$(run_case model_self_report none "$FORMAL")
printf '%s\n' "$RESULT" | grep -qx 'rc=1'
printf '%s\n' "$RESULT" | grep -qx 'TOP_BLOCKERS=formal_delivery_not_confirmed'

echo 'PASS: verified send clears only formal_delivery_not_confirmed; all non-authoritative outcomes retain it'
