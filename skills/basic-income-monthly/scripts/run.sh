#!/usr/bin/env bash
# basic-income-monthly — distribute 10% of MRR to active recipients
# DRY_RUN=true to skip Stripe calls and DB writes

set -uo pipefail

# Load envs
[ -f ~/anicca-monk-factory/.env ] && set -a && source ~/anicca-monk-factory/.env && set +a
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

DRY_RUN="${DRY_RUN:-false}"
DASHBOARD_URL="https://aniccaai.com/dashboard.json"
MONTH=$(date -u +%Y-%m)
SLACK_CHANNEL="${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}"

require() {
  for v in "$@"; do
    if [ -z "${!v:-}" ]; then echo "❌ env $v missing" >&2; exit 1; fi
  done
}
require STRIPE_SECRET_KEY SUPABASE_URL SUPABASE_SERVICE_ROLE_KEY

echo "▶ basic-income-monthly $MONTH (dry_run=$DRY_RUN)"

# 1. Fetch MRR
MRR=$(curl -sS "$DASHBOARD_URL" | jq -r '.mrr.total_usd // 0')
echo "  MRR: \$$MRR"

POOL_CENTS=$(echo "$MRR" | awk '{ printf "%d\n", $1 * 100 * 0.10 }')
echo "  Pool (cents): $POOL_CENTS"

# 2. Fetch active recipients
RECIPIENTS=$(curl -sS \
  "$SUPABASE_URL/rest/v1/recipients?select=id,{{profile.lateness.stakeholders.channel}},stripe_account_id&status=eq.active&kyc_complete=eq.true" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY")
COUNT=$(echo "$RECIPIENTS" | jq 'length')
echo "  Active recipients: $COUNT"

if [ "$COUNT" -eq 0 ]; then
  echo "  ℹ️  no active recipients — nothing to do"
  exit 0
fi

PER_PERSON_CENTS=$(( POOL_CENTS / COUNT ))
echo "  Per-person (cents): $PER_PERSON_CENTS"

if [ "$PER_PERSON_CENTS" -lt 1 ]; then
  echo "  ⚠️  pool too small ($PER_PERSON_CENTS cents/person) — skip"
  exit 0
fi

SUCCESS=0
FAIL=0
TOTAL_PAID=0

for ROW in $(echo "$RECIPIENTS" | jq -c '.[]'); do
  R_ID=$(echo "$ROW" | jq -r '.id')
  R_EMAIL=$(echo "$ROW" | jq -r '.{{profile.lateness.stakeholders.channel}}')
  R_ACCT=$(echo "$ROW" | jq -r '.stripe_account_id')

  if [ "$DRY_RUN" = "true" ]; then
    echo "  [DRY] would transfer $PER_PERSON_CENTS cents to $R_EMAIL ($R_ACCT)"
    SUCCESS=$((SUCCESS + 1))
    TOTAL_PAID=$((TOTAL_PAID + PER_PERSON_CENTS))
    continue
  fi

  TR=$(curl -sS -X POST https://api.stripe.com/v1/transfers \
    -u "$STRIPE_SECRET_KEY:" \
    -d "amount=$PER_PERSON_CENTS" \
    -d "currency=usd" \
    -d "destination=$R_ACCT" \
    -d "description=Anicca Basic Income — $MONTH" \
    -d "metadata[recipient_{{profile.lateness.stakeholders.channel}}]=$R_EMAIL" \
    -d "metadata[month]=$MONTH")

  TR_ID=$(echo "$TR" | jq -r '.id // empty')
  TR_ERR=$(echo "$TR" | jq -r '.error.message // empty')

  if [ -n "$TR_ID" ]; then
    SUCCESS=$((SUCCESS + 1))
    TOTAL_PAID=$((TOTAL_PAID + PER_PERSON_CENTS))
    AMOUNT_USD=$(awk "BEGIN { printf \"%.2f\", $PER_PERSON_CENTS / 100 }")
    curl -sS -X POST "$SUPABASE_URL/rest/v1/payouts" \
      -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
      -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
      -H "Content-Type: application/json" \
      -d "{\"recipient_id\":\"$R_ID\",\"stripe_transfer_id\":\"$TR_ID\",\"amount_usd\":$AMOUNT_USD,\"month\":\"$MONTH\",\"status\":\"succeeded\"}" >/dev/null
    echo "  ✅ $R_EMAIL: \$$AMOUNT_USD ($TR_ID)"
  else
    FAIL=$((FAIL + 1))
    echo "  ❌ $R_EMAIL: $TR_ERR"
  fi
done

TOTAL_USD=$(awk "BEGIN { printf \"%.2f\", $TOTAL_PAID / 100 }")
SUMMARY="💸 basic-income $MONTH: \$$TOTAL_USD → $SUCCESS humans (failed: $FAIL)"
echo "$SUMMARY"

if [ "$DRY_RUN" != "true" ] && command -v openclaw &>/dev/null; then
  openclaw message send --channel slack --target "$SLACK_CHANNEL" --text "$SUMMARY" 2>/dev/null || true
fi
