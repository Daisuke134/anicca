#!/usr/bin/env bash
# Emits a single-line JSON object to stdout describing the genesis body's vital signs.
# Read-only. No outbound network. Used by heartbeat.sh.
set -euo pipefail

HERMES_BIN="${HERMES_BIN:-/Users/operator/.local/bin/hermes}"
STATE_DIR="${STATE_DIR:-/Users/operator/.hermes/state}"
CONSTITUTION="${CONSTITUTION:-/Users/operator/anicca-oss/CONSTITUTION.md}"

ts="$(date -u +%FT%TZ)"
hermes_version="$("$HERMES_BIN" --version 2>/dev/null | head -1 | awk '{print $3}')"
constitution_sha="$(shasum -a 256 "$CONSTITUTION" | awk '{print $1}')"

mkdir -p "$STATE_DIR"
err_file="$STATE_DIR/.tmp-status-err.$$"
status_out="$("$HERMES_BIN" status 2>"$err_file" || true)"
status_err="$(head -c 500 "$err_file" 2>/dev/null || echo "")"
rm -f "$err_file"
model="$(echo "$status_out" | awk -F: '/^[[:space:]]*Model:/{sub(/^[[:space:]]+/,"",$2); sub(/^[[:space:]]+/,"",$2); print $2; exit}' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
provider="$(echo "$status_out" | awk -F: '/^[[:space:]]*Provider:/{sub(/^[[:space:]]+/,"",$2); sub(/^[[:space:]]+/,"",$2); print $2; exit}' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"

cron_count="$("$HERMES_BIN" cron list 2>/dev/null | grep -cE 'Name:[[:space:]]+anicca-' || true)"

last_ts="$(tail -n 1 "$STATE_DIR/heartbeat.jsonl" 2>/dev/null | /usr/bin/jq -r '.ts' 2>/dev/null || echo "")"

/usr/bin/jq -n \
  --arg ts "$ts" \
  --arg hermes_version "$hermes_version" \
  --arg constitution_sha "$constitution_sha" \
  --arg provider "$provider" \
  --arg model "$model" \
  --argjson cron_count "${cron_count:-0}" \
  --arg last_ts "$last_ts" \
  --arg status_err "$status_err" \
  '{ts:$ts, hermes_version:$hermes_version, constitution_sha:$constitution_sha,
    provider:$provider, model:$model, cron_count:$cron_count, last_ts:$last_ts,
    status_err:$status_err}'
