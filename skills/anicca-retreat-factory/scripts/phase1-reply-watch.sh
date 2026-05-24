#!/usr/bin/env bash
set -euo pipefail

# Phase 1 — Watch Gmail INBOX for replies + bounces against state.outreach_log.
# Idempotent. Posts to Slack on every state change (no quiet skip on flips).
# Uses thread API to read the actual incoming message (not the SENT thread head).

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$SKILL_DIR/data"
export STATE_FILE="$DATA_DIR/state.json"

# shellcheck source=lib/state.sh
source "$SKILL_DIR/scripts/lib/state.sh"
# shellcheck source=lib/gmail-inbox.sh
source "$SKILL_DIR/scripts/lib/gmail-inbox.sh"
# shellcheck source=lib/slack.sh
source "$SKILL_DIR/scripts/lib/slack.sh"

if [ -f "$HOME/.openclaw/.env" ] && [ -z "${GOG_KEYRING_PASSWORD:-}" ]; then
  set -a; source "$HOME/.openclaw/.env"; set +a
fi
: "${GOG_KEYRING_PASSWORD:?required}"
: "${SLACK_BOT_TOKEN:?required}"

SLACK_CHANNEL="${SLACK_CHANNEL_METRICS:-{{profile.channels.reportChannel}}}"
state_init

new_replies=""
new_bounces=""

# For each outreach with status sent (or unset), classify its thread.
# message_id stored at send time IS the thread head for gog gmail send.
while IFS= read -r oid; do
  cur_status=$(jq -r --arg id "$oid" '.outreach_log[] | select(.candidate_id == $id) | .status // "sent"' "$STATE_FILE")
  [ "$cur_status" = "bounced" ] && continue
  [ "$cur_status" = "replied" ] && continue
  [ "$cur_status" = "rejected" ] && continue
  recipient=$(jq -r --arg id "$oid" '.outreach_log[] | select(.candidate_id == $id) | .recipient' "$STATE_FILE")
  thread_id=$(jq -r --arg id "$oid" '.outreach_log[] | select(.candidate_id == $id) | (.thread_id // .message_id)' "$STATE_FILE")
  [ -z "$thread_id" ] || [ "$thread_id" = "null" ] && continue

  classification=$(inbox_classify_thread "$thread_id")
  cls=$(echo "$classification" | awk -F'\t' '{print $1}')
  rmid=$(echo "$classification" | awk -F'\t' '{print $2}')
  rsubj=$(echo "$classification" | awk -F'\t' '{print $3}')
  rfrom=$(echo "$classification" | awk -F'\t' '{print $4}')
  ridate=$(echo "$classification" | awk -F'\t' '{print $5}')

  if [ "$cls" = "replied" ]; then
    tmp=$(mktemp)
    jq --arg id "$oid" --arg rmid "$rmid" --arg rsubj "$rsubj" --arg rfrom "$rfrom" --arg ridate "$ridate" --arg ts "$(date -Iseconds)" \
      '.outreach_log = (.outreach_log | map(if .candidate_id == $id then .status = "replied" | .reply_message_id = $rmid | .reply_subject = $rsubj | .reply_from = $rfrom | .reply_internal_date = $ridate | .reply_detected_at = $ts else . end))' \
      "$STATE_FILE" > "$tmp" && mv "$tmp" "$STATE_FILE"
    new_replies="${new_replies}
• ${oid} (${recipient}) — from \`${rfrom}\` — \`${rmid}\`"
  elif [ "$cls" = "bounced" ]; then
    tmp=$(mktemp)
    jq --arg id "$oid" --arg rmid "$rmid" --arg rsubj "$rsubj" --arg rfrom "$rfrom" --arg ridate "$ridate" --arg ts "$(date -Iseconds)" \
      '.outreach_log = (.outreach_log | map(if .candidate_id == $id then .status = "bounced" | .bounce_message_id = $rmid | .bounce_subject = $rsubj | .bounce_from = $rfrom | .bounce_internal_date = $ridate | .bounce_detected_at = $ts else . end))' \
      "$STATE_FILE" > "$tmp" && mv "$tmp" "$STATE_FILE"
    new_bounces="${new_bounces}
• ${oid} (${recipient}) — \`${rmid}\`"
  fi
done < <(jq -r '.outreach_log[].candidate_id' "$STATE_FILE")

if [ -n "$new_replies$new_bounces" ]; then
  total_replied=$(jq '[.outreach_log[] | select(.status == "replied")] | length' "$STATE_FILE")
  total_bounced=$(jq '[.outreach_log[] | select(.status == "bounced")] | length' "$STATE_FILE")
  total_pending=$(jq '[.outreach_log[] | select((.status // "sent") == "sent")] | length' "$STATE_FILE")
  total_rejected=$(jq '[.outreach_log[] | select(.status == "rejected")] | length' "$STATE_FILE")
  report="🏞️ *Anicca Retreats Phase 1 — reply watch* ($(date '+%Y-%m-%d %H:%M JST'))

*new replies*: ${new_replies:-(none)}
*new bounces*: ${new_bounces:-(none)}

*totals*: replied=${total_replied} | bounced=${total_bounced} | rejected=${total_rejected} | pending=${total_pending}

state: \`${STATE_FILE}\`"
  slack_post "$SLACK_CHANNEL" "$report" >/dev/null
  echo "[SLACK] reported"
else
  echo "[QUIET] no new replies/bounces"
fi

echo "[DONE] $(jq '[.outreach_log[] | select(.status == "replied")] | length' "$STATE_FILE") replied, $(jq '[.outreach_log[] | select(.status == "bounced")] | length' "$STATE_FILE") bounced, $(jq '[.outreach_log[] | select((.status // "sent") == "sent")] | length' "$STATE_FILE") pending"
