#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/runtime-paths.sh"

RUN_ID="daily-$(date +%Y%m%d-%H%M%S)"
EVIDENCE="$JOB_SEARCH_STATE_ROOT/evidence/$RUN_ID"
TELEGRAM_OUTBOX="$JOB_SEARCH_STATE_ROOT/telegram-outbox.sqlite3"

mkdir -p "$EVIDENCE" "$JOB_SEARCH_STATE_ROOT/logs"
chmod 700 \
  "$JOB_SEARCH_STATE_ROOT" \
  "$JOB_SEARCH_STATE_ROOT/evidence" \
  "$EVIDENCE" \
  "$JOB_SEARCH_STATE_ROOT/logs"
export PYTHONPATH="$JOB_SEARCH_APP_ROOT"
export JOB_SEARCH_BROWSER_OWNER_EVIDENCE="$EVIDENCE/browser-owner.json"
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
ASHBY_FAST_PATH_RESULT="$EVIDENCE/ashby-fast-path.json"
set +e
"$JOB_SEARCH_PYTHON" -m job_search_loop.ashby_fast_path \
  --endpoint "http://127.0.0.1:9222" \
  --ledger "$JOB_SEARCH_STATE_ROOT/ledger.sqlite3" \
  --profile "$JOB_SEARCH_PROFILE" \
  --materials-root "${XDG_DATA_HOME:-$HOME/.local/share}/anicca/job-search/materials" \
  --evidence-dir "$EVIDENCE/ashby-fast-path" \
  --output "$ASHBY_FAST_PATH_RESULT" \
  --japan-day "$JAPAN_DAY"
ASHBY_FAST_PATH_RC=$?
set -e
if [[ "$ASHBY_FAST_PATH_RC" -ne 0 ]]; then
  printf '%s\n' "Ashby fast path exited rc=$ASHBY_FAST_PATH_RC; browser-lane fallback continues" >&2
fi
export JOB_SEARCH_ASHBY_FAST_PATH_RESULT="$ASHBY_FAST_PATH_RESULT"
WORKDAY_FAST_PATH_RESULT="$EVIDENCE/workday-fast-path.json"
if [[ "${JOB_SEARCH_ENABLE_WORKDAY:-0}" == "1" ]]; then
  set +e
  "$JOB_SEARCH_PYTHON" -m job_search_loop.workday_fast_path \
    --endpoint "http://127.0.0.1:9222" \
    --ledger "$JOB_SEARCH_STATE_ROOT/ledger.sqlite3" \
    --profile "$JOB_SEARCH_PROFILE" \
    --materials-root "${XDG_DATA_HOME:-$HOME/.local/share}/anicca/job-search/materials" \
    --evidence-dir "$EVIDENCE/workday-fast-path" \
    --store-path "${XDG_CONFIG_HOME:-$HOME/.config}/anicca/job-search/workday-accounts.json" \
    --output "$WORKDAY_FAST_PATH_RESULT" \
    --japan-day "$JAPAN_DAY"
  WORKDAY_FAST_PATH_RC=$?
  set -e
  if [[ "$WORKDAY_FAST_PATH_RC" -ne 0 ]]; then
    printf '%s\n' "Workday fast path exited rc=$WORKDAY_FAST_PATH_RC; browser-lane fallback continues" >&2
  fi
else
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
            "status": "parked",
            "processed": [],
            "excluded": [],
            "owner": "ai.anicca.job-search-daily",
            "reason": "ashby_first_gate",
        },
        ensure_ascii=False,
    )
    + "\n",
    encoding="utf-8",
)
os.chmod(path, 0o600)
PY
fi
export JOB_SEARCH_WORKDAY_FAST_PATH_RESULT="$WORKDAY_FAST_PATH_RESULT"
FAST_PATH_REPORT="$EVIDENCE/fast-path-report.json"
set +e
"$JOB_SEARCH_PYTHON" - \
  "$ASHBY_FAST_PATH_RESULT" \
  "$WORKDAY_FAST_PATH_RESULT" \
  "$TELEGRAM_OUTBOX" \
  "$JAPAN_DAY" \
  "$FAST_PATH_REPORT" <<'PY'
import json
import sys
from pathlib import Path

from job_search_loop.telegram import send_daily_report

ashby_path, workday_path, outbox_path, japan_day, receipt_path = map(Path, sys.argv[1:])

def read(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "failed", "processed": [], "reason": "result_unreadable"}
    return value if isinstance(value, dict) else {"status": "failed", "processed": [], "reason": "result_invalid"}

ashby = read(ashby_path)
workday = read(workday_path)
processed = ashby.get("processed") if isinstance(ashby.get("processed"), list) else []
details = []
for row in processed:
    if not isinstance(row, dict):
        continue
    company = str(row.get("company") or "unknown employer")
    title = str(row.get("title") or "unknown role")
    status = str(row.get("status") or "unknown")
    blocker = str(row.get("blocker") or "")
    details.append(f"{company} — {title}: {status}" + (f" ({blocker})" if blocker else ""))
if not details:
    details.append(f"no row processed ({ashby.get('status', 'unknown')})")
workday_status = str(workday.get("status") or "unknown")
workday_reason = str(workday.get("reason") or "")
message = (
    "Codex::: "
    f"{japan_day} JST fast-path checkpoint. Ashby ran first: "
    + "; ".join(details)
    + f". Workday is {workday_status}"
    + (f" ({workday_reason})" if workday_reason else "")
    + ". This checkpoint is sent before the model fallback so a timeout cannot suppress Telegram reporting."
)
try:
    result = send_daily_report(database=outbox_path, japan_day=japan_day, message=message)
    receipt = {"status": "sent", **result}
except Exception as error:
    receipt = {"status": "failed", "error_type": type(error).__name__}
receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
receipt_path.chmod(0o600)
print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
PY
FAST_PATH_REPORT_RC=$?
set -e
if [[ "$FAST_PATH_REPORT_RC" -ne 0 ]]; then
  printf '%s\n' "fast-path Telegram report failed; browser/model lane continues" >&2
fi
MODEL_TIMEOUT_SECONDS="${JOB_SEARCH_BROWSER_TIMEOUT_SECONDS:-300}"
set +e
"$JOB_SEARCH_PYTHON" "$JOB_SEARCH_RUNNER" \
  --task-class browser-lane-agent \
  --timeout-seconds "$MODEL_TIMEOUT_SECONDS" \
  --prompt-file "$JOB_SEARCH_APP_ROOT/prompts/daily-pass.md" \
  --schema "$JOB_SEARCH_APP_ROOT/schemas/pass-result.v1.schema.json" \
  --evidence-dir "$EVIDENCE" \
  --task-label job-search-daily \
  --loop job-search \
  --workdir "$JOB_SEARCH_REPO_ROOT"
RUNNER_RC=$?
set -e
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
