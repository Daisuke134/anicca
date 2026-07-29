#!/usr/bin/env bash
# Thin wrapper for camofox API. Sources userId/sessionKey from env (defaults: anicca/default).
# Usage:
#   source $LIFE_MANAGER_REPO/skills/camofox-browser/scripts/cf.sh
#   TAB=$(cf_open_tab "https://example.com")
#   cf_snapshot "$TAB"
#   cf_click "$TAB" e2
#   cf_type "$TAB" e1 "hello"
#   cf_press "$TAB" Enter
#   cf_navigate "$TAB" "https://example.com/dashboard"

CF_HOST="${CF_HOST:-http://localhost:9377}"
CF_USER="${CF_USER:-anicca}"
CF_SESSION="${CF_SESSION:-default}"

cf_open_tab() {
  local url="$1"
  curl -sS -X POST "$CF_HOST/tabs" \
    -H 'Content-Type: application/json' \
    -d "$(jq -n --arg url "$url" --arg u "$CF_USER" --arg s "$CF_SESSION" \
      '{url:$url, userId:$u, sessionKey:$s}')" \
    | jq -r .tabId
}

cf_navigate() {
  local tab="$1" url="$2"
  curl -sS -X POST "$CF_HOST/tabs/$tab/navigate" \
    -H 'Content-Type: application/json' \
    -d "$(jq -n --arg url "$url" --arg u "$CF_USER" --arg s "$CF_SESSION" \
      '{url:$url, userId:$u, sessionKey:$s}')"
}

cf_snapshot() {
  local tab="$1"
  curl -sS "$CF_HOST/tabs/$tab/snapshot?userId=$CF_USER&sessionKey=$CF_SESSION"
}

cf_url() {
  cf_snapshot "$1" | jq -r .url
}

cf_text() {
  cf_snapshot "$1" | jq -r .snapshot
}

cf_click() {
  local tab="$1" ref="$2"
  curl -sS -X POST "$CF_HOST/tabs/$tab/click" \
    -H 'Content-Type: application/json' \
    -d "$(jq -n --arg ref "$ref" --arg u "$CF_USER" --arg s "$CF_SESSION" \
      '{ref:$ref, userId:$u, sessionKey:$s}')"
}

cf_type() {
  local tab="$1" ref="$2" text="$3"
  curl -sS -X POST "$CF_HOST/tabs/$tab/type" \
    -H 'Content-Type: application/json' \
    -d "$(jq -n --arg ref "$ref" --arg text "$text" --arg u "$CF_USER" --arg s "$CF_SESSION" \
      '{ref:$ref, text:$text, userId:$u, sessionKey:$s}')"
}

cf_press() {
  local tab="$1" key="$2"
  curl -sS -X POST "$CF_HOST/tabs/$tab/press" \
    -H 'Content-Type: application/json' \
    -d "$(jq -n --arg key "$key" --arg u "$CF_USER" --arg s "$CF_SESSION" \
      '{key:$key, userId:$u, sessionKey:$s}')"
}

cf_screenshot() {
  local tab="$1" out="${2:-/tmp/cf-screen.png}"
  curl -sS "$CF_HOST/tabs/$tab/screenshot?userId=$CF_USER&sessionKey=$CF_SESSION" -o "$out"
  echo "$out"
}

cf_close_tab() {
  local tab="$1"
  curl -sS -X DELETE "$CF_HOST/tabs/$tab?userId=$CF_USER&sessionKey=$CF_SESSION"
}

cf_list_tabs() {
  curl -sS "$CF_HOST/tabs?userId=$CF_USER&sessionKey=$CF_SESSION"
}

cf_upload() {
  local tab="$1" ref_or_sel="$2"
  shift 2
  local files_json
  files_json=$(printf '%s\n' "$@" | jq -R . | jq -s .)
  local field="ref"
  if [[ "$ref_or_sel" != e[0-9]* && "$ref_or_sel" != "" ]]; then
    field="selector"
  fi
  curl -sS -X POST "$CF_HOST/tabs/$tab/upload" \
    -H 'Content-Type: application/json' \
    -d "$(jq -n --arg key "$field" --arg val "$ref_or_sel" --argjson files "$files_json" --arg u "$CF_USER" --arg s "$CF_SESSION" \
      '{($key): $val, files: $files, userId: $u, sessionKey: $s}')"
}
