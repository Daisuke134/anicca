#!/usr/bin/env bash
set -euo pipefail

OBSERVATION_FILE=${OBSERVER_DIR:-$HOME/.openclaw/observer}/observations/$(date +%Y-%m-%d).jsonl

extract_command_name() {
  local input="$1"
  local cmd

  cmd=$(echo "$input" | awk '{print $1}')
  if [[ -z "$cmd" ]]; then
    printf "[REDACTED]"
    return
  fi
  basename "$cmd"
}

log_shell_command() {
  local command_line="$1"
  local ts="${2:-$(date -u +"%Y-%m-%dT%H:%M:%SZ")}" 
  local file="$OBSERVATION_FILE"
  local command_name

  command_name=$(extract_command_name "$command_line")

  mkdir -p "$(dirname "$file")"
  jq -n \
    --arg ts "$ts" \
    --arg type "shell" \
    --arg cmd "$command_name" \
    '{timestamp: $ts, type: $type, command: $cmd}' >> "$file"
}

if [[ "${1:-}" == "--self-test" ]]; then
  log_shell_command "git status"
fi
