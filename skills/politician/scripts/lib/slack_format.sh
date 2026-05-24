#!/usr/bin/env bash
# slack_format.sh — single-line summary formatter for cron delivery.
# Each mode script ends with: slack_post "<emoji> <title>" "key1=val1 key2=val2 …"

slack_post() {
  local title="$1" fields="${2:-}" mode="${MODE:-unknown}" dry="${POLITICIAN_DRY_RUN:-true}"
  local prefix="LIVE"
  [[ "$dry" == "true" ]] && prefix="DRY"
  printf '%s [%s | %s] %s' "$title" "$prefix" "$mode" "$fields"
  printf '\n'
}

slack_skip() {
  local reason="$1" mode="${MODE:-unknown}"
  printf '⏭️  politician/%s skipped — %s\n' "$mode" "$reason"
}
