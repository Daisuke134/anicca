#!/usr/bin/env bash
# Buy a US phone number from SMSPool, save to accounts/<persona>/tiktok.json (phone field).
# Service: TikTok (~$0.50/number on SMSPool).
set -euo pipefail
PERSONA="${1:?persona required}"
ROOT="$HOME/anicca-monk-factory"
ACCOUNTS_DIR="$ROOT/accounts/$PERSONA"
mkdir -p "$ACCOUNTS_DIR"
set -a; . "$ROOT/.env"; set +a

if [ -z "${SMSPOOL_API_KEY:-}" ]; then
  echo "🛑 SMSPOOL_API_KEY missing in .env — Dais must:"
  echo "   1. Sign up at smspool.net"
  echo "   2. Add credit (\$5 minimum)"
  echo "   3. Get API key, add to ~/anicca-monk-factory/.env"
  exit 11
fi

# SMSPool order endpoint: POST /purchase/sms.php with key, country=1 (US), service=1142 (TikTok)
echo "  📞 SMSPool: ordering US phone for TikTok..."
RESP=$(curl -sS -X POST "https://api.smspool.net/purchase/sms" \
  -d "key=$SMSPOOL_API_KEY" -d "country=1" -d "service=1142" -d "max_price=1.00")

ORDER_ID=$(echo "$RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('order_id') or d.get('orderid') or '')" 2>/dev/null)
PHONE=$(echo "$RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('phonenumber') or d.get('number') or '')" 2>/dev/null)

if [ -z "$ORDER_ID" ] || [ -z "$PHONE" ]; then
  echo "❌ smspool order failed: $(echo "$RESP" | head -c 300)"
  exit 12
fi

# Persist
python3 - <<PY
import json
out = {"phone": "$PHONE", "sms_pool_order_id": "$ORDER_ID", "service": "tiktok", "country": "us"}
import os
path = os.path.expanduser("$ACCOUNTS_DIR/tiktok.json")
existing = {}
try: existing = json.load(open(path))
except: pass
existing.update(out)
json.dump(existing, open(path, "w"), indent=2)
PY
echo "  ✅ phone $PHONE (order $ORDER_ID) → $ACCOUNTS_DIR/tiktok.json"
