#!/usr/bin/env bash
set -euo pipefail

# anicca-retreat-crowdfund — daily report
# 1. Poll Stripe for new retreat-build-fund donations
# 2. Check Camp Fire JP project 951165 status
# 3. Update progress.json
# 4. Slack #metrics report (always posts daily summary)

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$SKILL_DIR/data"
PROGRESS_FILE="$DATA_DIR/progress.json"
mkdir -p "$DATA_DIR"

# Auto-load env
if [ -f "$HOME/.openclaw/.env" ]; then
  set -a
  source "$HOME/.openclaw/.env"
  set +a
fi

# shellcheck source=lib/stripe-poll.sh
source "$SKILL_DIR/scripts/lib/stripe-poll.sh"
# shellcheck source=lib/campfire-status.sh
source "$SKILL_DIR/scripts/lib/campfire-status.sh"
# shellcheck source=lib/slack.sh
source "$SKILL_DIR/scripts/lib/slack.sh"

: "${SLACK_BOT_TOKEN:?required}"
: "${STRIPE_SECRET_KEY:?required}"
SLACK_CHANNEL="${SLACK_CHANNEL_METRICS:-{{profile.channels.reportChannel}}}"

# Init progress.json
if [ ! -f "$PROGRESS_FILE" ]; then
  echo '{"target_jpy": 30000000, "stripe_total_jpy": 0, "stripe_donor_count": 0, "last_run_at": null, "campfire_status": "draft_active", "history": []}' > "$PROGRESS_FILE"
fi

PREV_TOTAL=$(jq -r '.stripe_total_jpy // 0' "$PROGRESS_FILE")
PREV_COUNT=$(jq -r '.stripe_donor_count // 0' "$PROGRESS_FILE")

# 1. Stripe poll
echo "[1/3] Stripe poll..."
STRIPE_RESULT=$(stripe_poll_donations 0)
NEW_TOTAL=$(echo "$STRIPE_RESULT" | jq -r '.total_amount_jpy // 0')
NEW_COUNT=$(echo "$STRIPE_RESULT" | jq -r '.total_count // 0')
DELTA_TOTAL=$((NEW_TOTAL - PREV_TOTAL))
DELTA_COUNT=$((NEW_COUNT - PREV_COUNT))

# 2. Camp Fire status (best-effort, don't fail entire run on this)
echo "[2/3] Camp Fire status..."
CF_STATUS=$(campfire_status 2>&1 | grep "^STATUS:" | head -1 | awk '{print $2}' || echo "unknown")
CF_STATUS="${CF_STATUS:-unknown}"

# 3. Update progress
TS_NOW=$(date -Iseconds)
TARGET=$(jq -r '.target_jpy // 30000000' "$PROGRESS_FILE")
PCT=$(awk -v n="$NEW_TOTAL" -v t="$TARGET" 'BEGIN{ if(t>0){ printf("%.2f", n/t*100) } else { print "0" } }')

tmp=$(mktemp)
jq --arg ts "$TS_NOW" --arg cf "$CF_STATUS" --argjson new_total "$NEW_TOTAL" --argjson new_count "$NEW_COUNT" \
  '.stripe_total_jpy = $new_total | .stripe_donor_count = $new_count | .last_run_at = $ts | .campfire_status = $cf
   | .history += [{ts: $ts, stripe_total_jpy: $new_total, stripe_donor_count: $new_count, campfire_status: $cf}]' \
  "$PROGRESS_FILE" > "$tmp" && mv "$tmp" "$PROGRESS_FILE"

# 4. Slack report (always — daily heartbeat)
echo "[3/3] Slack report..."
TARGET_FMT=$(printf "¥%'d" "$TARGET")
NEW_TOTAL_FMT=$(printf "¥%'d" "$NEW_TOTAL")
DELTA_FMT=$(printf "¥%'d" "$DELTA_TOTAL")

REPORT="🏗 *Anicca Retreats — Build the Center daily report* ($(date '+%Y-%m-%d %H:%M JST'))

*Stripe direct (aniccaai.com/retreat/build):*
• total raised: ${NEW_TOTAL_FMT} / ${TARGET_FMT} (${PCT}%)
• donors: ${NEW_COUNT}
• today's delta: ${DELTA_FMT} (+${DELTA_COUNT} donors)

*Camp Fire JP (project 951165):*
• status: \`${CF_STATUS}\`

state: \`${PROGRESS_FILE}\`"

TS=$(slack_post "$SLACK_CHANNEL" "$REPORT")
echo "[SLACK] ts=$TS"
echo "[DONE] stripe=${NEW_TOTAL_FMT} donors=${NEW_COUNT} cf=${CF_STATUS}"
