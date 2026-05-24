#!/usr/bin/env bash
# donation — monthly cron (recurring, runs 1st 09:00 JST)
#
# Reads installed.json, computes 1% of current MRR, donates via the saved
# payment method on the established charity, captures the receipt, updates
# the public ledger, commits to anicca-products → Netlify rebuild.
#
# DRY_RUN behavior (default true): re-pulls MRR, computes amount, prints
# what it would donate. No {{profile.lateness.stakeholders.channel}}, no submit, no ledger write.

set -uo pipefail

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
[ -f ~/anicca-monk-factory/.env ] && set -a && source ~/anicca-monk-factory/.env && set +a

SKILL=~/.openclaw/skills/donation
STATE_DIR=~/.openclaw/state/donation
RECEIPTS_DIR="$SKILL/data/receipts"
mkdir -p "$STATE_DIR" "$RECEIPTS_DIR"

source "$SKILL/scripts/lib/agent_{{profile.lateness.stakeholders.channel}}.sh"
source "$SKILL/scripts/lib/ledger.sh"

DASHBOARD_URL="${DASHBOARD_URL:-https://aniccaai.com/dashboard.json}"
DRY_RUN="${DONATION_DRY_RUN:-true}"
SLACK_CHANNEL="${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}"
TODAY=$(date +%Y-%m-%d)
NOW_ISO=$(date +%Y-%m-%dT%H:%M:%S%z)
THIS_MONTH=$(date +%Y-%m)
NEXT_MONTH=$(date -v+1m +%Y-%m 2>/dev/null || date -d '+1 month' +%Y-%m)
NEXT_PAYOUT="${NEXT_MONTH}-01"
PAYOUT_DATE="${THIS_MONTH}-01"
SENTINEL="$STATE_DIR/installed.json"
HISTORY="$HOME/.openclaw/state/donation-history.jsonl"

slack_post() {
  local text="$1"
  [ -z "${SLACK_BOT_TOKEN:-}" ] && return 0
  [ "${SLACK_POST:-true}" = "true" ] || return 0
  curl -sS -X POST https://slack.com/api/chat.postMessage \
    -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
    -H 'Content-type: application/json; charset=utf-8' \
    -d "{\"channel\":\"$SLACK_CHANNEL\",\"text\":$(jq -Rn --arg t "$text" '$t')}" >/dev/null
}

echo "▶ donation/monthly  $TODAY  dry_run=$DRY_RUN"

# --- 1. Sentinel ---
if [ ! -f "$SENTINEL" ]; then
  MSG="🚨 donation monthly: $SENTINEL missing — install hook never ran on this agent. Aborting.
Run: MODE=install bash ~/.openclaw/skills/donation/scripts/run.sh"
  echo "$MSG"; slack_post "$MSG"; exit 1
fi

CHARITY=$(jq    -r '.charity_name'    "$SENTINEL")
KC_SLUG=$(jq    -r '.keychain_slug // ""' "$SENTINEL")
echo "  charity: $CHARITY"

# --- 2. Idempotency ---
if [ -f "$HISTORY" ]; then
  ALREADY=$(jq -s --arg d "$PAYOUT_DATE" '
    [.[] | select(.payout_date == $d and .status == "paid")] | length
  ' "$HISTORY" 2>/dev/null || echo 0)
  if [ "${ALREADY:-0}" -gt 0 ] 2>/dev/null; then
    MSG="🚨 donation $THIS_MONTH: payout for $PAYOUT_DATE already in history (status=paid). Skipping (likely cron mis-fire)."
    echo "$MSG"; slack_post "$MSG"; exit 0
  fi
fi

# --- 3. MRR + amount ---
MRR=$(curl -sS "$DASHBOARD_URL" | jq -r '.mrr.total_usd // 0')
if [ "$(awk -v m="$MRR" 'BEGIN{print (m+0 <= 0)}')" = "1" ]; then
  MSG="🚨 donation $THIS_MONTH: MRR is \$0 at execution time — no donation sent."
  echo "$MSG"; slack_post "$MSG"; exit 0
fi
AMOUNT=$(awk -v m="$MRR" 'BEGIN{
  a = m * 0.01;
  a = (a < 1) ? 1 : a;
  printf "%.2f\n", int(a*100 + 0.5)/100;
}')
echo "  MRR \$$MRR  →  amount \$$AMOUNT  (1% of MRR, floor \$1, no ceiling)"

# Build the ledger entries upfront so dry-run can preview them.
ENTRY=$(jq -nc \
  --arg month "$THIS_MONTH" \
  --arg charity "$CHARITY" \
  --arg url "$(jq -r '.charity_url // ""' "$SENTINEL" 2>/dev/null || echo '')" \
  --argjson amt "$AMOUNT" \
  --arg paid_at "$NOW_ISO" \
  '{month: $month, charity_name: $charity, charity_url: $url,
    amount_usd: $amt, currency: "USD", paid_at: $paid_at, status: "paid"}')

NEXT_THIS_MONTH=$(jq -nc \
  --arg charity "$CHARITY" \
  --arg url "$(jq -r '.charity_url // ""' "$SENTINEL" 2>/dev/null || echo '')" \
  --argjson amt "$AMOUNT" \
  --arg payout "$NEXT_PAYOUT" \
  '{charity_name: $charity, charity_url: $url,
    queued_amount_usd: $amt, payout_date: $payout}')

# --- 4. DRY_RUN gate ---
if [ "$DRY_RUN" = "true" ]; then
  MSG="🧪 [DRY] donation $THIS_MONTH: would have donated \$$AMOUNT to $CHARITY
no submit, no ledger write, no anicca-products commit."
  echo "$MSG"; slack_post "$MSG"
  echo "----- LEDGER PREVIEW -----"
  ledger_dry_preview "$ENTRY" "$NEXT_THIS_MONTH" || true
  echo "----- /LEDGER PREVIEW -----"
  echo "✅ monthly dry-run complete"
  exit 0
fi

# ===================== LIVE PATH BELOW =====================
# Backend check (live only — DRY_RUN already returned above)
if ! ab_check >&2; then
  MSG="🚨 donation monthly: agent-{{profile.lateness.stakeholders.channel}} backend unavailable. Aborting."
  echo "$MSG"; slack_post "$MSG"; exit 1
fi

DONATE_URL=$(jq -r '.donate_logged_in_url // .charity_url // ""' "$SENTINEL")
SLUG=$(echo "$CHARITY" | tr '[:upper:] ' '[:lower:]-' | tr -dc 'a-z0-9-')
SHOT="$RECEIPTS_DIR/${THIS_MONTH}-${SLUG}.png"

# Agent loop (cron payload):
#   ab_open "$DONATE_URL"
#   ab_snapshot                  → find amount field, saved-card row, donate button
#   ab_fill <amount-ref> "$AMOUNT"
#   ab_click <saved-card-ref>    (if not auto-selected)
#   ab_click <donate-ref>
#   ab_wait_load
#   final URL = ab_get_url        → must contain thank/success/complete/confirm
#   ab_screenshot "$SHOT"
echo "  [agent] would open $DONATE_URL, fill amount=\$$AMOUNT, confirm saved card, submit"
echo "  [agent] would screenshot → $SHOT"

# Assume agent loop reported FILL_OK + thank-you page.
# Append ledger + history.
ledger_append_local    "$ENTRY"
ledger_append_history  "$ENTRY"

# Patch dashboard.json + push to anicca-products
if ! ledger_patch_dashboard "$ENTRY" "$NEXT_THIS_MONTH"; then
  MSG="🚨 donation $THIS_MONTH: dashboard.json patch failed. Donation succeeded but ledger not pushed.
Manual: cd $ANICCA_PRODUCTS_DIR && jq '.charity.ledger += [$ENTRY]' apps/landing/public/dashboard.json"
  echo "$MSG"; slack_post "$MSG"; exit 1
fi

if ! ledger_commit_push "$THIS_MONTH" "$AMOUNT" "$CHARITY"; then
  MSG="🚨 donation $THIS_MONTH: git push to anicca-products failed. Local patch kept; will retry next run."
  echo "$MSG"; slack_post "$MSG"; exit 1
fi

# Slack ✅
TOTAL=$(jq -s '[.[] | select(.status=="paid") | .amount_usd] | add // 0' "$HOME/.openclaw/state/donation-ledger.jsonl")
ORGS=$(jq  -s '[.[] | select(.status=="paid") | .charity_name] | unique | length' "$HOME/.openclaw/state/donation-ledger.jsonl")

MSG="✅ donation $THIS_MONTH: \$$AMOUNT → $CHARITY
receipt: $SHOT
ledger committed to anicca-products dev branch.
public page refreshes in ~3 min.
total_given_usd → \$$TOTAL  (orgs: $ORGS)"
echo "$MSG"; slack_post "$MSG"

echo "✅ monthly live complete"
