#!/usr/bin/env bash
# daily-report entrypoint — fires once, writes ONE trace JSONL line.
# Wired to `hermes cron` schedule `0 6 * * *` (06:00 JST).
set -uo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PY="$SKILL_DIR/.venv/bin/python"
STATE_DIR="${STATE_DIR:-/Users/anicca/.hermes/state}"
mkdir -p "$STATE_DIR"
TRACE_LOG="$STATE_DIR/daily-report.jsonl"
COMPOSE_TRACE="$STATE_DIR/.tmp-daily-report-compose-trace.$$"
JQ="/usr/bin/jq"

# Load env (best-effort). A pre-exported ANICCA_REPORT_TO (e.g. from the E2E
# test scoping the send to the inbox only) MUST win over the .env default, so
# we preserve it across the source.
_PRESET_REPORT_TO="${ANICCA_REPORT_TO:-}"
set -a
. /Users/anicca/.hermes/.env 2>/dev/null || true
set +a
[ -n "$_PRESET_REPORT_TO" ] && export ANICCA_REPORT_TO="$_PRESET_REPORT_TO"

ts="$(date -u +%FT%TZ)"

# Compose (live LLM call) and capture trace from stderr
compose_out="$("$VENV_PY" "$SKILL_DIR/scripts/compose.py" --json 2> "$COMPOSE_TRACE")"
compose_rc=$?
compose_trace="$(cat "$COMPOSE_TRACE" 2>/dev/null || echo '{}')"
[ -z "$compose_trace" ] && compose_trace='{}'
rm -f "$COMPOSE_TRACE"

# Send
send_out="$(printf '%s' "$compose_out" | "$VENV_PY" "$SKILL_DIR/scripts/send.py")"
send_rc=$?
[ -z "$send_out" ] && send_out='{"ok":false,"error":"send.py produced no output"}'

# Merge into one JSONL line
"$JQ" -nc \
  --arg ts "$ts" \
  --argjson compose_rc "$compose_rc" \
  --argjson send_rc "$send_rc" \
  --argjson compose "$compose_trace" \
  --argjson send "$send_out" \
  '{ts:$ts, compose_rc:$compose_rc, send_rc:$send_rc, compose:$compose, send:$send}' \
  >> "$TRACE_LOG"

# Echo the send trace so `hermes cron run` sees it
printf '%s\n' "$send_out"
