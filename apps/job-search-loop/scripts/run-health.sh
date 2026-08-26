#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/runtime-paths.sh"

RUN_ID="health-$(date +%Y%m%d-%H%M%S)"
EVIDENCE="$JOB_SEARCH_STATE_ROOT/evidence/$RUN_ID"
mkdir -p "$EVIDENCE" "$JOB_SEARCH_STATE_ROOT/logs"
chmod 700 "$EVIDENCE" "$JOB_SEARCH_STATE_ROOT/logs"

KICK_REQUEST="$JOB_SEARCH_STATE_ROOT/development-kickstart.request"
if [[ -e "$KICK_REQUEST" || -L "$KICK_REQUEST" ]]; then
  export PYTHONPATH="$JOB_SEARCH_APP_ROOT"
  "$JOB_SEARCH_PYTHON" -m job_search_loop.development_trigger consume \
    --request "$KICK_REQUEST" \
    --release "$JOB_SEARCH_REPO_ROOT/RELEASE.json" \
    --output "$EVIDENCE/development-kickstart.json"
fi

set +e
zsh "$SCRIPT_DIR/healthcheck.sh" >"$EVIDENCE/healthcheck.out.log" 2>"$EVIDENCE/healthcheck.err.log"
HEALTH_RC=$?
set -e

if [[ "$HEALTH_RC" -eq 0 ]]; then
  "$JOB_SEARCH_PYTHON" - "$EVIDENCE/receipt.json" <<'PY'
import json
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
path.write_text(json.dumps({"status": "healthy"}) + "\n", encoding="utf-8")
os.chmod(path, 0o600)
PY
  exit 0
fi

MESSAGE=$'Codex::: [Job Hunter][ヘルスチェック]\n⚠️ Workday loopの実処理で問題を検出しました。\n\n次に自動で行うこと\nprivate evidenceから原因を確認し、安全に再開できる処理だけを続けます。'
set +e
export PYTHONPATH="$JOB_SEARCH_APP_ROOT${PYTHONPATH:+:$PYTHONPATH}"
REPORT=$("$JOB_SEARCH_PYTHON" - "$JOB_SEARCH_STATE_ROOT/telegram-outbox.sqlite3" "$RUN_ID" "$MESSAGE" <<'PY'
import json,sys
from pathlib import Path
from job_search_loop.telegram import send_once
value=send_once(database=Path(sys.argv[1]), event_key=f"job-search-health:{sys.argv[2]}", message=sys.argv[3])
print(json.dumps(value, sort_keys=True))
PY
)
REPORT_RC=$?
set -e

"$JOB_SEARCH_PYTHON" - "$EVIDENCE/receipt.json" "$REPORT" "$REPORT_RC" <<'PY'
import json
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
raw = sys.argv[2]
returncode = int(sys.argv[3])
receipt = {"status": "failed", "report_status": "failed", "report_rc": returncode}
if returncode == 0:
    try:
        value = json.loads(raw)
        message_id = value.get("message_id") if isinstance(value, dict) else None
        if message_id:
            receipt["report_status"] = "sent"
            receipt["message_id"] = str(message_id)
    except json.JSONDecodeError:
        pass
path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
os.chmod(path, 0o600)
PY
exit "$HEALTH_RC"
