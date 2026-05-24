#!/usr/bin/env bash
# lib/dais-alert.sh — Slack + Google Calendar 統合 alert helper
# Usage: source lib/dais-alert.sh
#
#   alert_human "<title>" "<iso_start>" "<iso_end>" "<location>" "<full instruction>"
#
# Effect:
#   - Slack #metrics に投稿
#   - GCal に予定追加 (24h前 + 2h前 reminder)
#   - state.json に { manual_action_required: true, due_at: <iso_start> } を log

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
: "${SLACK_CHANNEL:={{profile.channels.reportChannel}}}"
: "${GOG_ACCOUNT:={{profile.contact.personalEmail}}}"
: "${GOG_KEYRING_PASSWORD:=<password>}"
export GOG_ACCOUNT GOG_KEYRING_PASSWORD

alert_human() {
  local TITLE="$1"
  local ISO_START="$2"
  local ISO_END="$3"
  local LOCATION="$4"
  local INSTRUCTION="$5"

  local GCAL_ID=""
  if command -v gog &>/dev/null && [ -n "$ISO_START" ]; then
    local GCAL_RESULT
    GCAL_RESULT=$(gog calendar create primary \
      --summary "$TITLE" \
      --from "$ISO_START" \
      --to   "$ISO_END" \
      --location "$LOCATION" \
      --description "$INSTRUCTION" \
      --json 2>&1)
    GCAL_ID=$(echo "$GCAL_RESULT" | jq -r '.event.id // empty' 2>/dev/null)
  fi

  if command -v openclaw &>/dev/null; then
    local MSG="$TITLE
日時: $ISO_START → $ISO_END
場所: $LOCATION
─────
$INSTRUCTION"
    [ -n "$GCAL_ID" ] && MSG="$MSG
📅 Calendar: https://www.google.com/calendar/event?eid=$GCAL_ID"

    openclaw message send --channel slack --target "$SLACK_CHANNEL" \
      --message "$MSG" 2>/dev/null || true
  fi

  echo "$GCAL_ID"
}
