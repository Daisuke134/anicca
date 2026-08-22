#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/runtime-paths.sh"
export CLOAK_LEASE_HOLDER_PID=$$

JOB_SEARCH_DISK_GUARD="${JOB_SEARCH_DISK_GUARD:-$HOME/gig/releases/life-manager/current/skills/earn/gig/scripts/gig_disk_guard.py}"
if [[ ! -f "$JOB_SEARCH_DISK_GUARD" || -L "$JOB_SEARCH_DISK_GUARD" || ! -r "$JOB_SEARCH_DISK_GUARD" ]]; then
  print -u2 "job-search daily: disk guard is missing or unsafe"
  exit 75
fi
unset GIG_IGNORE_DISK_PRESSURE_BLOCK \
  GIG_IGNORE_DISK_WRITERS_STOP \
  DISK_CONTROL_STATE_DIR \
  OPENCLAW_STATE_DIR \
  LIFE_MANAGER_HOST_STATE_DIR
GIG_DISK_HEADROOM_KIB=524288
GIG_HOST_STATE_DIR="$HOME/.openclaw/state"
GIG_STATE_DIR="$HOME/.local/state/life-manager/job-search-daily"
export GIG_DISK_HEADROOM_KIB GIG_HOST_STATE_DIR GIG_STATE_DIR
if ! /usr/bin/python3 -I "$JOB_SEARCH_DISK_GUARD" /usr/bin/true; then
  print -u2 "job-search daily: disk guard blocked model wake"
  exit 75
fi

RUN_ID="daily-$(date +%Y%m%d-%H%M%S)"
EVIDENCE="$JOB_SEARCH_STATE_ROOT/evidence/$RUN_ID"
TELEGRAM_OUTBOX="$JOB_SEARCH_STATE_ROOT/telegram-outbox.sqlite3"
BROWSER_STATE="$JOB_SEARCH_STATE_ROOT/browser-agent"
BROWSER_SCRATCH="$EVIDENCE/scratch"

mkdir -p "$EVIDENCE" "$JOB_SEARCH_STATE_ROOT/logs" "$BROWSER_STATE" "$BROWSER_SCRATCH"
chmod 700 \
  "$JOB_SEARCH_STATE_ROOT" \
  "$JOB_SEARCH_STATE_ROOT/evidence" \
  "$EVIDENCE" \
  "$BROWSER_STATE" \
  "$BROWSER_SCRATCH" \
  "$JOB_SEARCH_STATE_ROOT/logs"
export PYTHONPATH="$JOB_SEARCH_APP_ROOT"
export JOB_SEARCH_BROWSER_OWNER_EVIDENCE="$EVIDENCE/browser-owner.json"
export JOB_SEARCH_BROWSER_STATE_ROOT="$BROWSER_STATE"
export JOB_SEARCH_BROWSER_SCRATCH="$BROWSER_SCRATCH"
"$JOB_SEARCH_PYTHON" -m job_search_loop.application_reporting deliver \
  --ledger "$JOB_SEARCH_STATE_ROOT/ledger.sqlite3" \
  --outbox "$TELEGRAM_OUTBOX" \
  --media-root "$JOB_SEARCH_TELEGRAM_MEDIA" \
  --output "$EVIDENCE/resume-deliver-before.json"
JAPAN_DAY=$(TZ=Asia/Tokyo /bin/date +%F)
refresh_summary() {
  "$JOB_SEARCH_PYTHON" -m job_search_loop.summary \
    --ledger "$JOB_SEARCH_STATE_ROOT/ledger.sqlite3" \
    --output "$JOB_SEARCH_STATE_ROOT/summary.v1.json" \
    --day "$JAPAN_DAY" \
    --model-route "${AGENT_RUNNER_PROVIDER:-unconfigured}"
}
"$JOB_SEARCH_PYTHON" -m job_search_loop.browser_owner \
  --endpoint "http://127.0.0.1:9222" \
  --output "$JOB_SEARCH_BROWSER_OWNER_EVIDENCE"
CANDIDATE_MEMORY="$JOB_SEARCH_STATE_ROOT/candidate-memory.v1.json"
"$JOB_SEARCH_PYTHON" -m job_search_loop.browser_agent.candidate_memory \
  --profile "$JOB_SEARCH_PROFILE" \
  --resume "${XDG_DATA_HOME:-$HOME/.local/share}/anicca/job-search/materials/master/Daisuke_Narita_AI_Resume.pdf" \
  --resume "${XDG_DATA_HOME:-$HOME/.local/share}/anicca/job-search/materials/business/Daisuke_Narita_AI_Business_Resume.pdf" \
  --resume "${XDG_DATA_HOME:-$HOME/.local/share}/anicca/job-search/materials/japan/Daisuke_Narita_Japan_AI_Resume.pdf" \
  --output "$CANDIDATE_MEMORY" >"$EVIDENCE/candidate-memory-receipt.json"
chmod 600 "$EVIDENCE/candidate-memory-receipt.json"
export JOB_SEARCH_CANDIDATE_MEMORY="$CANDIDATE_MEMORY"
export JOB_SEARCH_ANSWER_MEMORY="$JOB_SEARCH_STATE_ROOT/answer-memory.v1.json"
export JOB_SEARCH_MACHINE_CREDENTIALS="${XDG_DATA_HOME:-$HOME/.local/share}/anicca/credentials.json"
WORKDAY_DISCOVERY_RESULT="$EVIDENCE/workday-discovery.json"
set +e
"$JOB_SEARCH_PYTHON" -m job_search_loop.workday_discovery \
  --ledger "$JOB_SEARCH_STATE_ROOT/ledger.sqlite3" \
  --output "$WORKDAY_DISCOVERY_RESULT"
WORKDAY_DISCOVERY_RC=$?
set -e
if [[ "$WORKDAY_DISCOVERY_RC" -ne 0 ]]; then
  printf '%s\n' "Workday discovery failed; existing eligible queue continues" >&2
fi
ASHBY_DISCOVERY_RESULT="$EVIDENCE/ashby-discovery.json"
ASHBY_COMBINED_RESULT="$EVIDENCE/ashby-fast-path-combined.json"
"$JOB_SEARCH_PYTHON" - \
  "$ASHBY_DISCOVERY_RESULT" \
  "$ASHBY_COMBINED_RESULT" <<'PY'
import json
import os
import sys
from pathlib import Path

discovery_path, output_path = map(Path, sys.argv[1:])
discovery_path.write_text(
    json.dumps({"status": "parked", "reason": "workday_first_gate"}) + "\n",
    encoding="utf-8",
)
os.chmod(discovery_path, 0o600)
combined = {
    "status": "parked",
    "processed": [],
    "excluded": [],
    "reason": "workday_first_gate",
    "discovery": {"status": "parked", "discovered_count": 0},
    "owner": "ai.anicca.job-search-daily",
}
output_path.write_text(json.dumps(combined, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
os.chmod(output_path, 0o600)
PY
export JOB_SEARCH_ASHBY_FAST_PATH_RESULT="$ASHBY_COMBINED_RESULT"
export JOB_SEARCH_ASHBY_DISCOVERY_RESULT="$ASHBY_DISCOVERY_RESULT"
WORKDAY_FAST_PATH_RESULT="$EVIDENCE/workday-fast-path.json"
"$JOB_SEARCH_PYTHON" - "$WORKDAY_FAST_PATH_RESULT" <<'PY'
import json
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
path.write_text(
    json.dumps(
        {
            "status": "model_owned",
            "processed": [],
            "excluded": [],
            "owner": "ai.anicca.job-search-daily",
            "reason": "mandatory_browser_lane",
        },
        ensure_ascii=False,
    )
    + "\n",
    encoding="utf-8",
)
os.chmod(path, 0o600)
PY
export JOB_SEARCH_WORKDAY_FAST_PATH_RESULT="$WORKDAY_FAST_PATH_RESULT"
PREFLIGHT_REPORT="$EVIDENCE/pre-model-report.json"
JOB_SEARCH_REPORT_TEXT=$("$JOB_SEARCH_PYTHON" - \
  "$ASHBY_COMBINED_RESULT" \
  "$WORKDAY_FAST_PATH_RESULT" \
  "$JAPAN_DAY" \
  "$RUN_ID" <<'PY'
import json
import sys
from pathlib import Path

ashby_path, workday_path, japan_day, run_id = map(Path, sys.argv[1:])

def read(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "failed", "processed": [], "reason": "result_unreadable"}
    return value if isinstance(value, dict) else {"status": "failed", "processed": [], "reason": "result_invalid"}

ashby = read(ashby_path)
workday = read(workday_path)
ashby_discovery = ashby.get("discovery") if isinstance(ashby.get("discovery"), dict) else {}
ashby_discovery_status = str(ashby_discovery.get("status") or "unknown")
ashby_discovered_count = int(ashby_discovery.get("discovered_count") or 0)
workday_status = str(workday.get("status") or "unknown")
workday_reason = str(workday.get("reason") or "")
message = (
    "Codex::: "
    f"{japan_day} JST {run_id.name} pre-model checkpoint. "
    + "Workday-only model browser wake is starting"
    + f"; Workday is {workday_status}"
    + (f" ({workday_reason})" if workday_reason else "")
    + f". Ashby is {ashby_discovery_status} ({ashby_discovered_count} discovered; parked until Workday is proven repeatable)"
    + ". This checkpoint is sent before the mandatory model lane so a timeout cannot suppress Telegram reporting."
)
print(message)
PY
)
set +e
JOB_SEARCH_REPORT_RESPONSE=$(/opt/homebrew/bin/timeout 10 env PATH="/opt/homebrew/bin:/opt/homebrew/opt/node/bin:/usr/bin:/bin" \
  "$JOB_SEARCH_OPENCLAW" message send \
    --channel telegram \
    --target "${TELEGRAM_ALERT_CHAT_ID:-8547730585}" \
    -m "$JOB_SEARCH_REPORT_TEXT" \
    --json 2>/dev/null)
JOB_SEARCH_REPORT_RC=$?
set -e
"$JOB_SEARCH_PYTHON" - \
  "$PREFLIGHT_REPORT" \
  "$JOB_SEARCH_REPORT_RESPONSE" \
  "$JOB_SEARCH_REPORT_RC" <<'PY'
import json
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
raw = sys.argv[2]
returncode = int(sys.argv[3])
receipt = {"status": "failed", "error_type": f"openclaw_rc_{returncode}"}
if returncode == 0:
    try:
        value = json.loads(raw)
        payload = value.get("payload") if isinstance(value, dict) else {}
        message_id = value.get("messageId") or (payload or {}).get("messageId")
        if message_id:
            receipt = {"status": "sent", "message_id": str(message_id)}
        else:
            receipt = {"status": "failed", "error_type": "ack_missing_message_id"}
    except json.JSONDecodeError:
        receipt = {"status": "failed", "error_type": "invalid_openclaw_json"}
path.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
os.chmod(path, 0o600)
print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
PY
if [[ "$JOB_SEARCH_REPORT_RC" -ne 0 ]]; then
  printf '%s\n' "pre-model Telegram report failed; wake continues" >&2
fi
MODEL_TIMEOUT_SECONDS="${JOB_SEARCH_BROWSER_TIMEOUT_SECONDS:-1800}"
set +e
"$JOB_SEARCH_PYTHON" -m job_search_loop.browser_agent.orchestrator \
  --runner "$JOB_SEARCH_RUNNER" \
  --timeout-seconds "$MODEL_TIMEOUT_SECONDS" \
  --prompt "$JOB_SEARCH_APP_ROOT/prompts/daily-pass.md" \
  --schema "$JOB_SEARCH_APP_ROOT/schemas/pass-result.v1.schema.json" \
  --evidence-dir "$EVIDENCE" \
  --workdir "$JOB_SEARCH_REPO_ROOT" \
  --python "$JOB_SEARCH_PYTHON" \
  --active-provider workday
RUNNER_RC=$?
set -e
set +e
/opt/homebrew/bin/timeout 45 env \
  SESSION_VAULT_PORT=9222 \
  SESSION_VAULT_DIR="$JOB_SEARCH_SESSION_VAULT_DIR" \
  "$JOB_SEARCH_PYTHON" "$JOB_SEARCH_SESSION_VAULT_SCRIPT" dump \
  >"$EVIDENCE/session-vault-dump.json" 2>"$EVIDENCE/session-vault-dump.stderr.log"
VAULT_RC=$?
set -e
chmod 600 "$EVIDENCE/session-vault-dump.json" "$EVIDENCE/session-vault-dump.stderr.log"
if [[ "$VAULT_RC" -ne 0 ]]; then
  printf '%s\n' "job-search session vault snapshot failed; wake evidence preserved" >&2
fi
if [[ "$RUNNER_RC" -ne 0 ]]; then
  refresh_summary
  exit "$RUNNER_RC"
fi
"$JOB_SEARCH_PYTHON" -m job_search_loop.application_reporting deliver \
  --ledger "$JOB_SEARCH_STATE_ROOT/ledger.sqlite3" \
  --outbox "$TELEGRAM_OUTBOX" \
  --media-root "$JOB_SEARCH_TELEGRAM_MEDIA" \
  --output "$EVIDENCE/resume-deliver-after.json"
refresh_summary
