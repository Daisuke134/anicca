#!/usr/bin/env bash
set -euo pipefail

# Phase 4 — Followup scanner: scans state.outreach_log for entries with followup_scheduled_at <= today,
# sends followup {{profile.lateness.stakeholders.channel}} (template per entry), records followup_sent_at, threads via --reply-to-message-id when our_reply_message_id exists.
#
# Recipe (exact tools):
#   1. jq filter state.outreach_log → entries due (followup_scheduled_at <= today AND followup_sent_at not set)
#   2. For each: read template from data/templates/<followup_template>.txt
#   3. gog gmail send -a {{profile.contact.personalEmail}} --to <followup_recipient or recipient> --reply-to-message-id <our_reply_message_id or message_id> --quote --subject "Re: ..."
#   4. Record followup_message_id + followup_sent_at in state.json
#   5. Slack #metrics notify
#
# Idempotent (skips entries already sent OR not yet due).

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$SKILL_DIR/data"
TEMPLATES_DIR="$DATA_DIR/templates"
export STATE_FILE="$DATA_DIR/state.json"

# shellcheck source=lib/state.sh
source "$SKILL_DIR/scripts/lib/state.sh"
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

TODAY=$(date '+%Y-%m-%d')
sent=0
skipped=0
failed=0
sent_log=""

# Find entries due for followup
while IFS= read -r oid; do
  followup_due=$(jq -r --arg id "$oid" --arg today "$TODAY" \
    '.outreach_log[] | select(.candidate_id == $id) | select((.followup_scheduled_at // "9999-12-31") <= $today and (.followup_sent_at // "") == "") | .candidate_id' \
    "$STATE_FILE")

  if [ -z "$followup_due" ]; then
    skipped=$((skipped + 1))
    continue
  fi

  # Determine reply target {{profile.lateness.stakeholders.channel}} — prefer reply_from (the actual person who replied) over recipient
  reply_from=$(jq -r --arg id "$oid" '.outreach_log[] | select(.candidate_id == $id) | .reply_from // ""' "$STATE_FILE")
  recipient=$(jq -r --arg id "$oid" '.outreach_log[] | select(.candidate_id == $id) | .recipient // ""' "$STATE_FILE")
  reply_{{profile.lateness.stakeholders.channel}}=$(echo "$reply_from" | grep -oE '[A-Za-z0-9._+-]+@[A-Za-z0-9.-]+\.[A-Za-z]+' | head -1)
  to_{{profile.lateness.stakeholders.channel}}="${reply_{{profile.lateness.stakeholders.channel}}:-$recipient}"

  template_name=$(jq -r --arg id "$oid" '.outreach_log[] | select(.candidate_id == $id) | .followup_template // ""' "$STATE_FILE")
  template_file="$TEMPLATES_DIR/${template_name}.txt"

  if [ ! -f "$template_file" ]; then
    echo "[FAIL] $oid: template $template_file not found"
    failed=$((failed + 1))
    continue
  fi

  # Thread the followup as a reply to either our last reply OR the original outreach
  thread_anchor=$(jq -r --arg id "$oid" '.outreach_log[] | select(.candidate_id == $id) | (.our_reply_message_id // .reply_message_id // .message_id)' "$STATE_FILE")
  original_subject=$(jq -r --arg id "$oid" '.outreach_log[] | select(.candidate_id == $id) | .reply_subject // .subject // "Anicca Retreats followup"' "$STATE_FILE")
  # Strip any existing Re: prefix to avoid Re: Re: Re:
  clean_subj=$(echo "$original_subject" | sed -E 's/^(Re: |RE: |Re:|RE:)+//')
  reply_subject="Re: ${clean_subj}"

  echo "[FOLLOWUP] $oid → $to_{{profile.lateness.stakeholders.channel}} (template=$template_name, anchor=$thread_anchor)"

  if mid=$(GOG_KEYRING_PASSWORD="$GOG_KEYRING_PASSWORD" /opt/homebrew/bin/gog gmail send \
    -a "$GMAIL_ACCOUNT" \
    --to "$to_{{profile.lateness.stakeholders.channel}}" \
    --subject "$reply_subject" \
    --body-file "$template_file" \
    --reply-to-message-id "$thread_anchor" \
    --quote \
    -j --results-only 2>&1 | jq -r '.messageId // empty'); then

    if [ -n "$mid" ]; then
      tmp=$(mktemp)
      jq --arg id "$oid" --arg mid "$mid" --arg ts "$(date -Iseconds)" --arg to "$to_{{profile.lateness.stakeholders.channel}}" \
        '.outreach_log = (.outreach_log | map(if .candidate_id == $id then .followup_message_id = $mid | .followup_sent_at = $ts | .followup_to = $to else . end))' \
        "$STATE_FILE" > "$tmp" && mv "$tmp" "$STATE_FILE"
      sent_log="${sent_log}
• ${oid} → ${to_{{profile.lateness.stakeholders.channel}}} → \`${mid}\`"
      sent=$((sent + 1))
      sleep 2
    else
      echo "[FAIL] $oid: no messageId in response"
      failed=$((failed + 1))
    fi
  else
    echo "[FAIL] $oid: gog send error"
    failed=$((failed + 1))
  fi

done < <(jq -r '.outreach_log[].candidate_id' "$STATE_FILE")

# Slack report (always — daily heartbeat for visibility)
report="🗓 *Anicca Retreats — Phase 4 followup scanner* ($(date '+%Y-%m-%d %H:%M JST'))
*sent today*: ${sent} | *skipped (not due)*: ${skipped} | *failed*: ${failed}
${sent_log:-(no followups due today)}

state: \`${STATE_FILE}\`"

if [ "$sent" -gt 0 ] || [ "$failed" -gt 0 ]; then
  slack_post "$SLACK_CHANNEL" "$report" >/dev/null
fi

echo "[DONE] sent=$sent skipped=$skipped failed=$failed"
