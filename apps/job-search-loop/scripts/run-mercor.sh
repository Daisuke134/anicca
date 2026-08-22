#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/runtime-paths.sh"

RUN_ID="mercor-$(date +%Y%m%d-%H%M%S)-$$"
MERCOR_STATE_ROOT="${JOB_SEARCH_STATE_ROOT}/mercor"
EVIDENCE="$JOB_SEARCH_STATE_ROOT/evidence/$RUN_ID"
LOCK="$MERCOR_STATE_ROOT/.pass.lock"
CDP_URL="${MERCOR_CDP_BASE_URL:-http://127.0.0.1:9334}"
MERCOR_PROFILE="${MERCOR_PROFILE:-$JOB_SEARCH_PROFILE}"
MERCOR_RESUME="${MERCOR_RESUME:-${XDG_DATA_HOME:-$HOME/.local/share}/anicca/job-search/materials/business/Daisuke_Narita_AI_Business_Resume.pdf}"

mkdir -p "$MERCOR_STATE_ROOT" "$JOB_SEARCH_STATE_ROOT/evidence" "$JOB_SEARCH_STATE_ROOT/logs" "$EVIDENCE"
chmod 700 "$JOB_SEARCH_STATE_ROOT" "$MERCOR_STATE_ROOT" "$JOB_SEARCH_STATE_ROOT/evidence" "$JOB_SEARCH_STATE_ROOT/logs"
chmod 700 "$EVIDENCE"
if ! mkdir "$LOCK" 2>/dev/null; then
  printf '%s\n' '{"status":"blocked","reason":"mercor_pass_already_running"}'
  exit 0
fi
trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT

export PYTHONPATH="$JOB_SEARCH_APP_ROOT"
chmod 644 "$JOB_SEARCH_APP_ROOT/prompts/mercor-pass.md" \
  "$JOB_SEARCH_APP_ROOT/schemas/mercor-pass-result.v1.schema.json"
PASS_PROMPT="$EVIDENCE/mercor-pass.md"
PASS_SCHEMA="$EVIDENCE/mercor-pass-result.v1.schema.json"
cp "$JOB_SEARCH_APP_ROOT/prompts/mercor-pass.md" "$PASS_PROMPT"
cp "$JOB_SEARCH_APP_ROOT/schemas/mercor-pass-result.v1.schema.json" "$PASS_SCHEMA"
chmod 600 "$PASS_PROMPT" "$PASS_SCHEMA"
"$JOB_SEARCH_PYTHON" -m job_search_loop.browser_owner \
  --endpoint "$CDP_URL" \
  --output "$EVIDENCE/browser-owner.json"

"$JOB_SEARCH_PYTHON" -m job_search_loop.mercor_pass \
  --state-root "$MERCOR_STATE_ROOT" \
  --profile "$MERCOR_PROFILE" \
  --resume "$MERCOR_RESUME" \
  --cdp-url "$CDP_URL" \
  --prompt "$PASS_PROMPT" \
  --schema "$PASS_SCHEMA" \
  --evidence-dir "$EVIDENCE/agent" \
  --workdir "$JOB_SEARCH_REPO_ROOT" \
  --run-id "$RUN_ID"

# Model-created artifacts are private even when the model omitted chmod.
find "$EVIDENCE" -type d -exec chmod 700 {} +
find "$EVIDENCE" -type f -exec chmod 600 {} +

# Read-only Earnings capture is part of every Mercor wake. It never clicks a
# payment control and fail-closes if the page exposes rows we cannot structure.
EARNINGS_EVIDENCE="$EVIDENCE/earnings"
EARNINGS_SNAPSHOT="$MERCOR_STATE_ROOT/earnings-readback.json"
mkdir -p "$EARNINGS_EVIDENCE"
chmod 700 "$EARNINGS_EVIDENCE"
set +e
"$JOB_SEARCH_PYTHON" -m job_search_loop.mercor_earnings_capture \
  --cdp "$CDP_URL" \
  --evidence-dir "$EARNINGS_EVIDENCE" \
  --output "$EARNINGS_SNAPSHOT"
CAPTURE_RC=$?
if [[ "$CAPTURE_RC" -eq 0 ]]; then
  "$JOB_SEARCH_PYTHON" -m job_search_loop.mercor_earnings_sync \
    --snapshot "$EARNINGS_SNAPSHOT" \
    --store "$MERCOR_STATE_ROOT/work-events.jsonl" \
    --outbox "$JOB_SEARCH_STATE_ROOT/telegram-outbox.sqlite3" \
    --output "$EVIDENCE/mercor-earnings-sync.json"
else
  printf '%s\n' '{"status":"blocked","synced_count":0,"events":[],"reason":"earnings_capture_failed"}' \
    >"$EVIDENCE/mercor-earnings-sync.json"
  chmod 600 "$EVIDENCE/mercor-earnings-sync.json"
fi
set -e

# Report every pass through the existing idempotent Telegram outbox. A missing
# Telegram credential must not erase or retry the browser pass; the report
# evidence records delivery_unknown and the next wake can reconcile it.
"$JOB_SEARCH_PYTHON" -m job_search_loop.mercor_reporting \
  --run-id "$RUN_ID" \
  --result "$EVIDENCE/agent/mercor-pass-summary.json" \
  --outbox "$JOB_SEARCH_STATE_ROOT/telegram-outbox.sqlite3" \
  --gate-store "$MERCOR_STATE_ROOT/human-gates.jsonl" \
  --output "$EVIDENCE/telegram-report.json"
