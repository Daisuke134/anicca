#!/usr/bin/env bash
# MODE=stripe_pac — monthly Stripe LLC → Super PAC sweep.
# Stays DRY until PAC_FORMED=true AND POLITICIAN_DRY_RUN=false.
set -euo pipefail
SKILL="${SKILL:-$(cd "$(dirname "$0")/.." && pwd)}"
MODE=stripe_pac
source "$SKILL/scripts/lib/api_clients.sh"
source "$SKILL/scripts/lib/slack_format.sh"
source "$SKILL/scripts/lib/coordination_wall.sh"
source "$SKILL/scripts/lib/ledger.sh"

DRY="${POLITICIAN_DRY_RUN:-true}"
PAC="${PAC_FORMED:-false}"

# In DRY: print "would transfer $X" using a stub MRR.
MRR_STUB="${POL_FAKE_MRR:-0}"
PCT="${POL_PAC_SWEEP_PCT:-10}"   # default 10% of MRR sweep

# Compute target — use python to avoid bc dependency.
TARGET=$(python3 -c "print(round(${MRR_STUB} * ${PCT} / 100, 2))")

if [[ "$DRY" == "true" || "$PAC" != "true" ]]; then
  COORD_INFO="$(coord_summary 2>/dev/null || echo 'wall=missing')"
  cat >&2 <<EOF
[would-sweep Stripe → Super PAC]
  source: Anicca AI Politics LLC (DE) Stripe USD account
  dest:   Anicca for Sentience Super PAC (Amalgamated Bank, account TBD)
  amount: \$${TARGET} (${PCT}% of MRR=\$${MRR_STUB})
  api:    POST /v1/transfers (Stripe Connect or external wire-to-bank)
  guardrail: foreign-national check — JP Stripe revenue is excluded from this sweep
  guardrail: coordination wall — $COORD_INFO
EOF
  slack_post "🏦 Stripe → PAC sweep" \
    "mrr=\$${MRR_STUB} sweep_pct=${PCT}% would_transfer=\$${TARGET} coord_wall=\"$COORD_INFO\" unlock=DRY (PAC_FORMED=$PAC POLITICIAN_DRY_RUN=$DRY)"
  exit 0
fi

# LIVE path (PAC_FORMED=true && POLITICIAN_DRY_RUN=false).
# Uses STRIPE_API_KEY_PAC — a SEPARATE Stripe key for the PAC's Connected
# account. NEVER use STRIPE_SECRET_KEY (that's the operating LLC's key).
pol_require_env STRIPE_API_KEY_PAC "(stripe_pac LIVE requires PAC's Stripe key)" || { slack_post "🏦 Stripe → PAC sweep" "live_path=blocked reason=STRIPE_API_KEY_PAC-missing"; exit 0; }

# Pull live MRR from the dashboard endpoint; fall back to env-stub.
DASH_URL="${POL_MRR_URL:-https://aniccaai.com/dashboard.json}"
LIVE_MRR=$(curl -fsSL --max-time 8 "$DASH_URL" 2>/dev/null | jq -r '.mrr.total_usd // empty')
[[ -n "$LIVE_MRR" ]] || LIVE_MRR="$MRR_STUB"
TARGET=$(python3 -c "print(round(${LIVE_MRR} * ${PCT} / 100, 2))")
AMOUNT_CENTS=$(python3 -c "print(int(round(${TARGET} * 100)))")

# PAC connected account ID from canonical state.
PAC_DEST="$(python3 -c "import json,os;p='$HOME/.openclaw/state/anicca.json';d=json.load(open(p)) if os.path.exists(p) else {};print((d.get('politician') or {}).get('pac_stripe_account_id') or '')")"
if [[ -z "$PAC_DEST" ]]; then
  slack_post "🏦 Stripe → PAC sweep" "live_path=blocked reason=anicca.json-pac_stripe_account_id-empty"
  exit 0
fi

# Coordination wall — for the LLC→PAC sweep this should be a no-op (intra-org
# transfer, no candidate involvement). But if the canonical state ever sets
# pac_destination_legislator_id (e.g., a future direct-to-IE-vendor path),
# the wall fires here. By federal law (52 U.S.C. § 30116; SpeechNow), a
# Super PAC cannot contribute to a candidate or to a coordinated PAC; this
# check is the second line of defense against accidental coordination.
PAC_DEST_LEGID="$(python3 -c "import json,os;p='$HOME/.openclaw/state/anicca.json';d=json.load(open(p)) if os.path.exists(p) else {};print((d.get('politician') or {}).get('pac_destination_legislator_id') or '')")"
if [[ -n "$PAC_DEST_LEGID" ]]; then
  if ! coord_check_recipient "$PAC_DEST_LEGID" ""; then
    slack_post "🏦 Stripe → PAC sweep" "live_path=blocked reason=coordination-wall-block legislator_id=$PAC_DEST_LEGID"
    exit 0
  fi
fi

if (( AMOUNT_CENTS <= 0 )); then
  slack_post "🏦 Stripe → PAC sweep" "skipped reason=zero-target mrr=\$${LIVE_MRR}"
  exit 0
fi

# Ledger path/init handled by lib/ledger.sh (POLITICIAN_LEDGER override OK).

RESP="$(curl -sS -o /tmp/stripe_resp_$$ -w '%{http_code}' \
  -X POST 'https://api.stripe.com/v1/transfers' \
  -u "${STRIPE_API_KEY_PAC}:" \
  -d "amount=${AMOUNT_CENTS}" \
  -d "currency=usd" \
  -d "destination=${PAC_DEST}" \
  --data-urlencode "description=Anicca AI Politics LLC monthly PAC contribution ($(date -u +%Y-%m))" \
  || echo 000)"
HTTP_CODE="$RESP"

if [[ "$HTTP_CODE" =~ ^2 ]]; then
  TRANSFER_ID=$(jq -r .id /tmp/stripe_resp_$$ 2>/dev/null || echo "")
  # Build invariant-compliant ledger entry. The LLC→PAC sweep is
  # internal-transfer (not a line_11a candidate contribution).
  ENTRY="$(jq -n \
    --arg date "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --argjson amount "$TARGET" \
    --arg currency "USD" \
    --arg domicile "Super-PAC" \
    --arg rectype "internal-transfer" \
    --arg kind "llc_to_pac_sweep" \
    --arg tid "$TRANSFER_ID" \
    --arg dest "$PAC_DEST" \
    --arg memo "Anicca LLC → Super PAC monthly sweep $(date -u +%Y-%m)" \
    '{date:$date, amount:$amount, currency:$currency, entity_domicile:$domicile, recipient_type:$rectype, kind:$kind, stripe_transfer_id:$tid, destination:$dest, memo:$memo}'
  )"
  if ledger_append "$ENTRY"; then
    slack_post "🏦 Stripe → PAC sweep" \
      "mrr=\$${LIVE_MRR} sweep_pct=${PCT}% transferred=\$${TARGET} dest=${PAC_DEST} transfer_id=${TRANSFER_ID} ledger_status=ok status=ok"
  else
    slack_post "🏦 Stripe → PAC sweep" \
      "mrr=\$${LIVE_MRR} sweep_pct=${PCT}% transferred=\$${TARGET} dest=${PAC_DEST} transfer_id=${TRANSFER_ID} ledger_status=INVARIANT-FAIL status=ok-but-ledger-not-written"
  fi
else
  ERR=$(jq -r '.error.message // "unknown"' /tmp/stripe_resp_$$ 2>/dev/null || echo "unknown")
  slack_post "🏦 Stripe → PAC sweep" \
    "mrr=\$${LIVE_MRR} sweep_pct=${PCT}% would_transfer=\$${TARGET} status=stripe-error code=$HTTP_CODE err=\"$ERR\""
fi
rm -f /tmp/stripe_resp_$$
