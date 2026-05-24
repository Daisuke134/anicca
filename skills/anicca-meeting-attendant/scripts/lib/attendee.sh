#!/usr/bin/env bash
# lib/attendee.sh — attendee.dev REST API wrapper
# Doc: https://docs.attendee.dev
set -euo pipefail

ATTENDEE_BASE="${ATTENDEE_BASE:-https://app.attendee.dev}"
: "${ATTENDEE_API_KEY:?ATTENDEE_API_KEY required (~/.openclaw/.env)}"

# attendee_spawn <meeting_url> <bot_name>
# Returns bot id on stdout
attendee_spawn() {
  local meeting_url="${1:?meeting_url}"
  local bot_name="${2:-Anicca}"
  local payload
  payload=$(MEETING_URL="$meeting_url" BOT_NAME="$bot_name" python3 -c 'import json,os;print(json.dumps({"meeting_url":os.environ["MEETING_URL"],"bot_name":os.environ["BOT_NAME"]}))')
  curl -sS -X POST "$ATTENDEE_BASE/api/v1/bots" \
    -H "Authorization: Token $ATTENDEE_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$payload"
}

# attendee_get <bot_id>
attendee_get() {
  local bot_id="${1:?bot_id}"
  curl -sS "$ATTENDEE_BASE/api/v1/bots/$bot_id" \
    -H "Authorization: Token $ATTENDEE_API_KEY"
}

# attendee_speak <bot_id> <text>  — TTS via attendee, bot speaks in meeting
attendee_speak() {
  local bot_id="${1:?bot_id}"
  local text="${2:?text}"
  local payload
  payload=$(SPEAK="$text" python3 -c 'import json,os;print(json.dumps({"text":os.environ["SPEAK"]}))')
  curl -sS -X POST "$ATTENDEE_BASE/api/v1/bots/$bot_id/output_audio" \
    -H "Authorization: Token $ATTENDEE_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$payload"
}

# attendee_transcript <bot_id> — get full meeting transcript
attendee_transcript() {
  local bot_id="${1:?bot_id}"
  curl -sS "$ATTENDEE_BASE/api/v1/bots/$bot_id/transcript" \
    -H "Authorization: Token $ATTENDEE_API_KEY"
}

# attendee_leave <bot_id>
attendee_leave() {
  local bot_id="${1:?bot_id}"
  curl -sS -X POST "$ATTENDEE_BASE/api/v1/bots/$bot_id/leave" \
    -H "Authorization: Token $ATTENDEE_API_KEY"
}

# attendee_list
attendee_list() {
  curl -sS "$ATTENDEE_BASE/api/v1/bots" \
    -H "Authorization: Token $ATTENDEE_API_KEY"
}
