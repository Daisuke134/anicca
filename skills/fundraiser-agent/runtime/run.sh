#!/bin/bash
set -uo pipefail

REPO_ROOT="${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$REPO_ROOT" ] || { echo "fundraiser: repository unavailable" >&2; exit 2; }
STATE_ROOT="${FUNDRAISER_STATE_ROOT:-$HOME/.local/state/life-manager/fundraiser}"
LOCK_DIR="$STATE_ROOT/run.lock"
LOG="$STATE_ROOT/fundraiser.log"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
EVIDENCE_DIR="$STATE_ROOT/evidence/$RUN_ID"
RUN_AGENT="$REPO_ROOT/skills/earn/marketing-engine/run_agent.sh"
PROMPT="$REPO_ROOT/skills/fundraiser-agent/prompts/daily.md"
SCHEMA="$REPO_ROOT/skills/fundraiser-agent/runtime/pass-result.schema.json"
SENDER="$REPO_ROOT/skills/_shared/send-telegram.sh"

mkdir -p "$STATE_ROOT/evidence" "$EVIDENCE_DIR"
chmod 700 "$STATE_ROOT" "$STATE_ROOT/evidence" "$EVIDENCE_DIR"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "fundraiser: prior pass still owns the loop" >>"$LOG"
  exit 0
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT

export PATH="/opt/homebrew/bin:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export LIFE_MANAGER_REPO="$REPO_ROOT"
export FUNDRAISER_RUN_ID="$RUN_ID"
export FUNDRAISER_STATE_ROOT="$STATE_ROOT"
export FUNDRAISER_RECEIPTS="$STATE_ROOT/application-receipts.jsonl"
export FUNDRAISER_CURSOR="$STATE_ROOT/cursor.json"
export FUNDRAISER_CDP_ENDPOINT="http://127.0.0.1:9222"
export FUNDRAISER_X_CDP_ENDPOINT="http://127.0.0.1:9222"
export FUNDRAISER_TELEGRAM_SENDER="$SENDER"
export FUNDRAISER_CAPTCHA_MODE="existing-capsolver-only"
export AGENT_RUNNER_PROVIDER="codex"
export AGENT_RUNNER_MODEL="gpt-5.6-luna"

RUNTIME_PROMPT="$EVIDENCE_DIR/runtime-prompt.md"
{
  cat "$PROMPT"
  cat <<EOF

## Concrete local runtime

- This is real run \`$RUN_ID\`, owned by \`ai.anicca.fundraiser\`.
- Work in \`$REPO_ROOT\`; use the existing authenticated Chrome CDP endpoint \`http://127.0.0.1:9222\`.
- Search both the live Web and rendered authenticated X UI. X is discovery only; verify on the official program website before applying.
- Use existing browser helpers under \`skills/browser/\`; do not launch or kill a browser.
- Read private founder values only from \`~/.config/anicca/job-search/profile.json\` and \`~/.local/share/anicca/credentials.json\`; never print or report their values.
- Append one compact JSON object per terminal candidate to \`$STATE_ROOT/application-receipts.jsonl\`. Include run_id, receipt identity, official URL, status, UTC timestamp, and non-secret readback reference. Never append a submitted status without official completion UI or matching provider mail.
- Write the durable next discovery cursor atomically to \`$STATE_ROOT/cursor.json\`.
- Immediately after every candidate terminal, execute \`bash $SENDER "Codex::: Fundraiser: <program, truthful status, non-secret readback, running counts>"\` and require \`TELEGRAM_SENT=true\`.
- For a supported CAPTCHA, use only the already-installed CapSolver/tier-a-bypass route found locally. Never weaken, evade, or disable provider security. If unavailable, checkpoint that candidate and continue to the next one.
- Spend this pass applying, not editing product code. Continue after the first submission. Return status=failure when submitted=0.
EOF
} >"$RUNTIME_PROMPT"
chmod 600 "$RUNTIME_PROMPT"

echo "=== fundraiser $RUN_ID start ===" >>"$LOG"
set +e
cat "$RUNTIME_PROMPT" | "$RUN_AGENT" \
  --task-class application-intent-planner \
  --escalation-reason "Fundraiser skill requires the existing Luna application-intent route for autonomous application judgment" \
  --schema "$SCHEMA" \
  --evidence-dir "$EVIDENCE_DIR" \
  --task-label fundraiser-continuous \
  --loop fundraiser \
  --workdir "$REPO_ROOT" >>"$LOG" 2>&1
RC=$?
set -e

SUMMARY_STATUS="runner_failure"
COUNTS="submitted=0 unknown=0 checkpoints=0"
if [ "$RC" -eq 0 ] && [ -f "$EVIDENCE_DIR/summary.json" ]; then
  READBACK="$(python3 - "$EVIDENCE_DIR/summary.json" <<'PY'
import json, pathlib, sys
summary = json.loads(pathlib.Path(sys.argv[1]).read_text())
result = json.loads(pathlib.Path(summary["result_path"]).read_text())
print(result["status"])
print(f'submitted={result["submitted"]} unknown={result["submit_unknown"]} checkpoints={result["checkpoints"]}')
PY
)" || RC=1
  SUMMARY_STATUS="$(printf '%s\n' "$READBACK" | sed -n '1p')"
  COUNTS="$(printf '%s\n' "$READBACK" | sed -n '2p')"
fi

REPORT="Codex::: Fundraiser wake $RUN_ID finished: status=$SUMMARY_STATUS, $COUNTS. Evidence: $EVIDENCE_DIR"
"$SENDER" "$REPORT" >>"$LOG" 2>&1 || RC=1
echo "=== fundraiser $RUN_ID end rc=$RC status=$SUMMARY_STATUS $COUNTS ===" >>"$LOG"
exit "$RC"
