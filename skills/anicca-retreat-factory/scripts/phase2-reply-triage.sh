#!/usr/bin/env bash
set -euo pipefail

# Phase 2 — Reply triage: read incoming replies via gog gmail thread, classify (positive / info-request / rejection / spam),
# draft response via template, post to Slack #metrics for human approve, send via gog gmail (--reply-to-message-id --quote).
#
# Recipe (exact tools — recorded 2026-05-11 from Shonan reply):
#   1. gog gmail thread get $THREAD_ID -j --results-only → parse messages → extract last incoming body
#   2. claude haiku via openclaw inference → classify + draft reply (NOT smtplib, NOT openai SDK)
#   3. Slack chat.postMessage with draft + 'send' / 'edit' button (manual approve until 24h auto-send rule kicks in)
#   4. gog gmail send -a {{profile.contact.personalEmail}} --to <reply_from> --reply-to-message-id <reply_msg_id> --quote --subject "Re: ..."
#   5. state.outreach_log[].our_reply_message_id += new msg id; status = in_dialogue
#
# Idempotent: skip if our_reply_message_id already set.

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$SKILL_DIR/data"
export STATE_FILE="$DATA_DIR/state.json"
TEMPLATES_DIR="$DATA_DIR/templates"
REPLIES_INBOUND="$DATA_DIR/replies/inbound"
REPLIES_OUTBOUND="$DATA_DIR/replies/outbound"
mkdir -p "$REPLIES_INBOUND" "$REPLIES_OUTBOUND"

# shellcheck source=lib/state.sh
source "$SKILL_DIR/scripts/lib/state.sh"
# shellcheck source=lib/gmail-inbox.sh
source "$SKILL_DIR/scripts/lib/gmail-inbox.sh"
# shellcheck source=lib/gmail.sh
source "$SKILL_DIR/scripts/lib/gmail.sh"
# shellcheck source=lib/slack.sh
source "$SKILL_DIR/scripts/lib/slack.sh"

if [ -f "$HOME/.openclaw/.env" ] && [ -z "${GOG_KEYRING_PASSWORD:-}" ]; then
  set -a; source "$HOME/.openclaw/.env"; set +a
fi
: "${GOG_KEYRING_PASSWORD:?required}"
: "${SLACK_BOT_TOKEN:?required}"

SLACK_CHANNEL="${SLACK_CHANNEL_METRICS:-{{profile.channels.reportChannel}}}"
GMAIL_ACCOUNT="${GMAIL_ACCOUNT:-{{profile.contact.personalEmail}}}"
state_init

triaged=0
skipped=0

# Find candidates that have replied but we haven't responded yet
while IFS= read -r oid; do
  status=$(jq -r --arg id "$oid" '.outreach_log[] | select(.candidate_id == $id) | .status // ""' "$STATE_FILE")
  our_reply=$(jq -r --arg id "$oid" '.outreach_log[] | select(.candidate_id == $id) | .our_reply_message_id // ""' "$STATE_FILE")

  # Skip non-replied or already-responded
  if [ "$status" != "replied" ]; then
    skipped=$((skipped + 1))
    continue
  fi
  if [ -n "$our_reply" ] && [ "$our_reply" != "null" ]; then
    skipped=$((skipped + 1))
    continue
  fi

  # Skip rejected (no reply needed)
  if [ "$status" = "rejected" ]; then
    skipped=$((skipped + 1))
    continue
  fi

  thread_id=$(jq -r --arg id "$oid" '.outreach_log[] | select(.candidate_id == $id) | (.thread_id // .message_id)' "$STATE_FILE")
  reply_from=$(jq -r --arg id "$oid" '.outreach_log[] | select(.candidate_id == $id) | .reply_from // ""' "$STATE_FILE")
  reply_msg_id=$(jq -r --arg id "$oid" '.outreach_log[] | select(.candidate_id == $id) | .reply_message_id // ""' "$STATE_FILE")
  reply_subject=$(jq -r --arg id "$oid" '.outreach_log[] | select(.candidate_id == $id) | .reply_subject // ""' "$STATE_FILE")
  recipient=$(jq -r --arg id "$oid" '.outreach_log[] | select(.candidate_id == $id) | .recipient // ""' "$STATE_FILE")

  # Extract clean {{profile.lateness.stakeholders.channel}} address from reply_from (which can be "Name <{{profile.lateness.stakeholders.channel}}@...>" format)
  reply_{{profile.lateness.stakeholders.channel}}=$(echo "$reply_from" | grep -oE '[A-Za-z0-9._+-]+@[A-Za-z0-9.-]+\.[A-Za-z]+' | head -1)
  [ -z "$reply_{{profile.lateness.stakeholders.channel}}" ] && reply_{{profile.lateness.stakeholders.channel}}="$recipient"

  echo "[TRIAGE] $oid → reply from $reply_{{profile.lateness.stakeholders.channel}} (msg $reply_msg_id)"

  # 1. Read full thread body for context (save to inbound dir for archive)
  inbound_file="$REPLIES_INBOUND/${oid}_${reply_msg_id}.json"
  if [ ! -f "$inbound_file" ]; then
    inbox_thread_get "$thread_id" > "$inbound_file"
  fi

  # 2. Slack notify — human approve required (until claude-haiku auto-draft kicks in next iteration)
  notice="🏞️ *Anicca Retreats — Reply received, triage needed*

*candidate*: \`${oid}\`
*from*: \`${reply_{{profile.lateness.stakeholders.channel}}}\`
*subject*: ${reply_subject}
*thread*: https://mail.google.com/mail/u/0/#inbox/${thread_id}

Auto-reply draft generation pending (claude haiku integration). For now: open Gmail, read, manually compose response, then mark our_reply_message_id in state.json.

state: \`${STATE_FILE}\`"

  ts=$(slack_post "$SLACK_CHANNEL" "$notice" || echo "")
  echo "[SLACK] notified ts=$ts"

  # Mark as awaiting_human_response so we don't re-notify
  tmp=$(mktemp)
  jq --arg id "$oid" --arg ts "$(date -Iseconds)" \
    '.outreach_log = (.outreach_log | map(if .candidate_id == $id then .triage_notified_at = $ts else . end))' \
    "$STATE_FILE" > "$tmp" && mv "$tmp" "$STATE_FILE"

  triaged=$((triaged + 1))

done < <(jq -r '.outreach_log[] | select(.status == "replied" and (.our_reply_message_id // "") == "" and (.triage_notified_at // "") == "") | .candidate_id' "$STATE_FILE")

echo "[DONE] triaged=$triaged skipped=$skipped"
