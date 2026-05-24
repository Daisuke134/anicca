#!/usr/bin/env bash
set -euo pipefail

# Check Camp Fire JP project 951165 draft status via camofox-{{profile.lateness.stakeholders.channel}}.
# Recipe (exact tool): camofox REST API on :9377 (NOT playwright/selenium).
# Returns plain text status.

campfire_status() {
  : "${CAMPFIRE_PASSWORD:?required for re-login if session expired}"

  # 1. Open mypage projects 951165 (camofox session reuses cookie persistence per userId+sessionKey)
  local TAB_ID
  TAB_ID=$(curl -sS -X POST http://localhost:9377/tabs \
    -H 'Content-Type: application/json' \
    -d '{"url":"https://camp-fire.jp/mypage/projects/951165","userId":"anicca-retreat","sessionKey":"crowdfund"}' \
    | jq -r .tabId)

  if [ -z "$TAB_ID" ] || [ "$TAB_ID" = "null" ]; then
    echo "ERROR: camofox tab open failed"
    return 1
  fi
  sleep 5

  # 2. Snapshot — extract status indicators
  local snapshot
  snapshot=$(curl -sS "http://localhost:9377/tabs/$TAB_ID/snapshot?userId=anicca-retreat&sessionKey=crowdfund")

  local current_url
  current_url=$(echo "$snapshot" | jq -r '.url // ""')

  # If redirected to /login, session expired — re-login required
  if echo "$current_url" | grep -q "/login"; then
    echo "STATUS: session_expired"
    return 0
  fi

  # If on planning_information — survey not done
  if echo "$current_url" | grep -q "planning_information"; then
    echo "STATUS: survey_pending"
    return 0
  fi

  # Otherwise extract project state
  echo "STATUS: draft_active"
  echo "URL: $current_url"

  # Cleanup tab
  curl -sS -X DELETE "http://localhost:9377/tabs/$TAB_ID?userId=anicca-retreat&sessionKey=crowdfund" >/dev/null
}
