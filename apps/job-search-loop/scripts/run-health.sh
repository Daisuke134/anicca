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

"$JOB_SEARCH_PYTHON" - "$EVIDENCE/receipt.json" <<'PY'
import json
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
receipt = {"status": "failed", "delivery": "suppressed"}
path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
os.chmod(path, 0o600)
PY
exit "$HEALTH_RC"
