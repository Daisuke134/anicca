#!/usr/bin/env bash
set -euo pipefail

# Phase 0 — Location discovery + Gmail outreach (idempotent).
# Reads candidates.json master list, sends to those not yet contacted,
# records message_id in state.json, reports summary to Slack.

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$SKILL_DIR/data"
TEMPLATE_DIR="$DATA_DIR/templates"
CANDIDATES_FILE="$DATA_DIR/candidates.json"
export STATE_FILE="$DATA_DIR/state.json"

# shellcheck source=lib/state.sh
source "$SKILL_DIR/scripts/lib/state.sh"
# shellcheck source=lib/gmail.sh
source "$SKILL_DIR/scripts/lib/gmail.sh"
# shellcheck source=lib/slack.sh
source "$SKILL_DIR/scripts/lib/slack.sh"

# Auto-load env from ~/.openclaw/.env if available
if [ -f "$HOME/.openclaw/.env" ] && [ -z "${GOG_KEYRING_PASSWORD:-}" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$HOME/.openclaw/.env"
  set +a
fi

: "${GOG_KEYRING_PASSWORD:?required}"
: "${SLACK_BOT_TOKEN:?required}"

SLACK_CHANNEL="${SLACK_CHANNEL_METRICS:-{{profile.channels.reportChannel}}}"
DRY_RUN="${DRY_RUN:-false}"

state_init

sent=0
skipped=0
failed=0
no_{{profile.lateness.stakeholders.channel}}=0
sent_log=""

unverified=0

while IFS= read -r cid; do
  {{profile.lateness.stakeholders.channel}}=$(jq -r --arg id "$cid" '.candidates[] | select(.id == $id) | .{{profile.lateness.stakeholders.channel}} // empty' "$CANDIDATES_FILE")
  verified=$(jq -r --arg id "$cid" '.candidates[] | select(.id == $id) | .verified // false' "$CANDIDATES_FILE")
  name=$(jq -r --arg id "$cid" '.candidates[] | select(.id == $id) | .name' "$CANDIDATES_FILE")
  subject=$(jq -r --arg id "$cid" '.candidates[] | select(.id == $id) | .subject' "$CANDIDATES_FILE")
  template=$(jq -r --arg id "$cid" '.candidates[] | select(.id == $id) | .template // "venue"' "$CANDIDATES_FILE")
  template_file="$TEMPLATE_DIR/${template}.txt"

  if state_already_sent "$cid"; then
    echo "[SKIP] $cid (already sent)"
    skipped=$((skipped + 1))
    continue
  fi

  if [ -z "${{profile.lateness.stakeholders.channel}}" ]; then
    echo "[NO-EMAIL] $cid (skipped — needs camofox form or manual verification)"
    no_{{profile.lateness.stakeholders.channel}}=$((no_{{profile.lateness.stakeholders.channel}} + 1))
    continue
  fi

  # HARD RULE (5/11 Dais 怒): never send to unverified {{profile.lateness.stakeholders.channel}}s
  # candidate must have verified=true (set after firecrawl scrape confirms {{profile.lateness.stakeholders.channel}})
  if [ "$verified" != "true" ]; then
    echo "[UNVERIFIED] $cid → ${{profile.lateness.stakeholders.channel}} — verified=$verified, skipping. Run sourcing skill to verify first."
    unverified=$((unverified + 1))
    continue
  fi

  if [ ! -f "$template_file" ]; then
    echo "[FAIL] $cid: template file not found: $template_file" >&2
    failed=$((failed + 1))
    continue
  fi

  if [ "$DRY_RUN" = "true" ]; then
    echo "[DRY] $cid → ${{profile.lateness.stakeholders.channel}} (template: $template)"
    sent=$((sent + 1))
    continue
  fi

  echo "[SEND] $cid → ${{profile.lateness.stakeholders.channel}}"
  if mid=$(gmail_send "${{profile.lateness.stakeholders.channel}}" "$subject" "$template_file"); then
    state_record_send "$cid" "$mid" "gmail" "${{profile.lateness.stakeholders.channel}}"
    sent_log="${sent_log}
• ${name} (${{{profile.lateness.stakeholders.channel}}}) → \`${mid}\`"
    sent=$((sent + 1))
    sleep 2
  else
    echo "[FAIL] $cid"
    failed=$((failed + 1))
  fi
done < <(jq -r '.candidates[].id' "$CANDIDATES_FILE")

# Slack report
total_in_state=$(jq '.outreach_log | length' "$STATE_FILE")
report="🏞️ *Anicca Retreats Phase 0 — skill run* ($(date '+%Y-%m-%d %H:%M JST'))
*new sent*: ${sent} | *skipped*: ${skipped} | *no-{{profile.lateness.stakeholders.channel}}*: ${no_{{profile.lateness.stakeholders.channel}}} | *unverified*: ${unverified} | *failed*: ${failed}
*total in state*: ${total_in_state} candidates
${sent_log:-(no new outreach this run)}

state: \`${STATE_FILE}\`
candidates master: \`${CANDIDATES_FILE}\` ($(jq '.candidates | length' "$CANDIDATES_FILE") entries)
script: \`${BASH_SOURCE[0]}\`"

if ts=$(slack_post "$SLACK_CHANNEL" "$report"); then
  echo "[SLACK] posted ts=$ts"
fi

echo "[DONE] sent=$sent skipped=$skipped no_{{profile.lateness.stakeholders.channel}}=$no_{{profile.lateness.stakeholders.channel}} failed=$failed total_in_state=$total_in_state"
