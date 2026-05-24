#!/usr/bin/env bash
# OTP relay: poll SMSPool for incoming SMS code, fall back to Slack DM if 90s timeout.
set -euo pipefail
PERSONA="${1:?persona required}"
ROOT="$HOME/anicca-monk-factory"
ACCOUNTS_DIR="$ROOT/accounts/$PERSONA"
set -a; . "$ROOT/.env"; set +a

ORDER_ID=$(python3 -c "import json; print(json.load(open('$ACCOUNTS_DIR/tiktok.json')).get('sms_pool_order_id',''))")
[ -n "$ORDER_ID" ] || { echo "❌ no sms_pool_order_id"; exit 31; }

echo "  🔄 polling SMSPool for OTP (90s timeout)..."
for i in $(seq 1 18); do
  RESP=$(curl -sS "https://api.smspool.net/sms/check?key=$SMSPOOL_API_KEY&orderid=$ORDER_ID" 2>/dev/null)
  CODE=$(echo "$RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('sms') or d.get('code') or '')" 2>/dev/null)
  if [ -n "$CODE" ]; then
    echo "  ✅ OTP received: $CODE"
    python3 -c "
import json
p = '$ACCOUNTS_DIR/tiktok.json'
d = json.load(open(p))
d['otp_code'] = '$CODE'
d['otp_received_at'] = '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
json.dump(d, open(p, 'w'), indent=2)
"
    exit 0
  fi
  sleep 5
done

# Fallback: ping Slack for manual entry
echo "  ⚠ SMSPool timeout (90s) — falling back to Slack relay"
if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
  curl -sS -X POST "$SLACK_WEBHOOK_URL" -H "Content-Type: application/json" \
    -d "$(python3 -c "import json; print(json.dumps({'text': f'⚠ TikTok OTP timeout for {\"$PERSONA\"}. SMSPool order $ORDER_ID. Reply with code in this channel within 5 min.'}))")" >/dev/null
  echo "  📣 Slack notified — waiting for manual code (5 min)..."
  # TODO: poll a Slack channel / DM for the code (would require Slack OAuth bot for true automation)
  echo "  🛑 Manual step: Dais types OTP into Playwright window. Re-run otp-relay.sh after entry."
  exit 32
else
  echo "❌ SLACK_WEBHOOK_URL missing — cannot fall back."
  exit 33
fi
