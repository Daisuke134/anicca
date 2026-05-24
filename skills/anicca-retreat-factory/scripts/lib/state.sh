#!/usr/bin/env bash
set -euo pipefail

STATE_FILE="${STATE_FILE:-$HOME/.openclaw/skills/anicca-retreat-factory/data/state.json}"

state_init() {
  if [ ! -f "$STATE_FILE" ]; then
    echo '{"phase":0,"phase_name":"location_discover","outreach_log":[],"last_run_at":null}' > "$STATE_FILE"
  fi
  if ! jq -e '.outreach_log' "$STATE_FILE" >/dev/null 2>&1; then
    local tmp; tmp=$(mktemp)
    jq '. + {"outreach_log": (.outreach_log // []), "phase": (.phase // 0)}' "$STATE_FILE" > "$tmp" && mv "$tmp" "$STATE_FILE"
  fi
}

state_already_sent() {
  local cid="$1"
  state_init
  jq -e --arg id "$cid" '.outreach_log | map(select(.candidate_id == $id)) | length > 0' "$STATE_FILE" >/dev/null 2>&1
}

state_record_send() {
  local cid="$1" mid="$2" method="${3:-gmail}" recipient="${4:-}"
  state_init
  local tmp; tmp=$(mktemp)
  jq --arg id "$cid" --arg mid "$mid" --arg m "$method" --arg r "$recipient" --arg ts "$(date -Iseconds)" \
    '.outreach_log += [{candidate_id: $id, message_id: $mid, method: $m, recipient: $r, sent_at: $ts}] | .last_run_at = $ts' \
    "$STATE_FILE" > "$tmp" && mv "$tmp" "$STATE_FILE"
}

state_summary() {
  state_init
  jq -r '
    "=== state.json summary ===\n" +
    "phase: \(.phase) (\(.phase_name // "n/a"))\n" +
    "last_run_at: \(.last_run_at // "never")\n" +
    "outreach_log entries: \(.outreach_log | length)\n" +
    "  by method: " + ((.outreach_log | group_by(.method) | map("\(.[0].method)=\(length)") | join(", ")) // "none")
  ' "$STATE_FILE"
}
