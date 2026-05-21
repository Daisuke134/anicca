#!/usr/bin/env bash
set -euo pipefail

OBSERVATION_FILE=${OBSERVER_DIR:-$HOME/.openclaw/observer}/observations/$(date +%Y-%m-%d).jsonl
COLLECT_URLS=${COLLECT_URLS:-false}
CURRENT_APP=${CURRENT_APP:-""}
TIMESTAMP=${TIMESTAMP:-"$(date -u +"%Y-%m-%dT%H:%M:%SZ")"}

sanitize_url_host() {
  local raw_url="$1"
  local scheme host

  scheme=$(echo "$raw_url" | grep -oE '^https?' || true)
  host=$(echo "$raw_url" | sed -E 's|^https?://([^/:@]+).*|\1|' || true)

  if [[ -n "$scheme" && -n "$host" ]]; then
    printf "%s://%s" "$scheme" "$host"
  fi
}

should_take_screenshot() {
  local current_ts="$1"
  local last_ts="$2"
  local interval="$3"

  if (( current_ts - last_ts >= interval )); then
    return 0
  fi
  return 1
}

log_browser_url() {
  local app="$1"
  local raw_url="$2"
  local sanitized

  [[ "$COLLECT_URLS" == "true" ]] || return 0

  sanitized=$(sanitize_url_host "$raw_url")
  [[ -n "$sanitized" ]] || return 0

  mkdir -p "$(dirname "$OBSERVATION_FILE")"
  jq -n \
    --arg ts "$TIMESTAMP" \
    --arg type "browser" \
    --arg app "$app" \
    --arg url "$sanitized" \
    '{timestamp: $ts, type: $type, data: {app: $app, url_host: $url}}' \
    >> "$OBSERVATION_FILE"
}

# Get frontmost (active) application name on macOS
get_frontmost_app() {
  osascript -e 'tell application "System Events" to get name of first application process whose frontmost is true' 2>/dev/null || true
}

# Return 0 if app is in excluded list, 1 otherwise
is_excluded_app() {
  local app_name="$1"
  local exclude_file="${OBSERVER_DIR:-$HOME/.openclaw/observer}/excluded_apps.txt"
  [[ -z "$app_name" ]] && return 0
  [[ -f "$exclude_file" ]] || return 1
  grep -qixF "$app_name" "$exclude_file" 2>/dev/null
}

log_frontmost_app() {
  local app
  app=$(get_frontmost_app)
  app=$(echo "$app" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  [[ -n "$app" ]] || return 0
  is_excluded_app "$app" && return 0

  mkdir -p "$(dirname "$OBSERVATION_FILE")"
  jq -n \
    --arg ts "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
    --arg type "app" \
    --arg app "$app" \
    '{timestamp: $ts, type: $type, data: {app: $app}}' \
    >> "$OBSERVATION_FILE"
}

if [[ "${1:-}" == "--self-test" ]]; then
  log_browser_url "Google Chrome" "https://github.com/user/repo?token=abc"
  log_frontmost_app
  exit 0
fi

log_frontmost_app
