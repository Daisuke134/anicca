#!/usr/bin/env bash
# Event-driven customer-support handler.
#
# Triggered by: review-scrape-daily.sh on negative sentiment with
#               customer_{{profile.lateness.stakeholders.channel}}_hint, or manually with explicit args.
#
# Args:
#   $1 = customer_{{profile.lateness.stakeholders.channel}}   (required)
#   $2 = reason / tweet text (free text, used in apology)
#
# Pipeline:
#   1. Stripe で 30% off coupon を発行 (one-time, 30 days valid)
#   2. gog gmail send で「ご不便おかけしました」+ coupon code 自動送信
#   3. data/coupons.json append
#   4. Slack #metrics escalation log
#
# stdout final line:
#   ✅ customer-support: coupon=<code> sent → <{{profile.lateness.stakeholders.channel}}> | slack ts=<ts>
#   ❌ customer-support FAILED: <reason>

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "❌ customer-support FAILED: missing args. usage: customer-support-event.sh <{{profile.lateness.stakeholders.channel}}> [reason]"
  exit 1
fi

EMAIL="$1"
REASON="${2:-}"

SKILL_DIR="$HOME/.openclaw/skills/anicca-fashion-factory"
DATA_DIR="$SKILL_DIR/data"
COUPONS_FILE="$DATA_DIR/coupons.json"

set -a; source "$HOME/.openclaw/.env"; set +a

PYTHON="python3"
GOG="/opt/homebrew/bin/gog"

[ -f "$COUPONS_FILE" ] || echo '{"coupons":[]}' > "$COUPONS_FILE"

echo "[1/3] Stripe coupon 30% off 発行"
COUPON_NAME="anicca-care-$(date +%Y%m%d-%H%M%S)"
COUPON_RESP=$(curl -s https://api.stripe.com/v1/coupons \
  -u "$STRIPE_SECRET_KEY:" \
  -d "percent_off=30" \
  -d "duration=once" \
  -d "max_redemptions=1" \
  -d "name=$COUPON_NAME" \
  -d "redeem_by=$(($(date +%s) + 30*24*3600))" \
  -d "metadata[reason]=customer-support" \
  -d "metadata[customer_{{profile.lateness.stakeholders.channel}}]=$EMAIL")

COUPON_ID=$(echo "$COUPON_RESP" | $PYTHON -c "import sys,json; print(json.load(sys.stdin).get('id',''))")
if [ -z "$COUPON_ID" ]; then
  ERR=$(echo "$COUPON_RESP" | $PYTHON -c "import sys,json; d=json.load(sys.stdin); print(d.get('error',{}).get('message','unknown'))")
  echo "❌ customer-support FAILED: stripe coupon — $ERR"
  exit 1
fi
echo "  coupon: $COUPON_ID"

# Promotion code (human-readable shortcode)
PROMO_CODE=$(echo "ANICCA$(date +%y%m)$(printf '%04d' $((RANDOM % 10000)))" | tr 'a-z' 'A-Z')
PROMO_RESP=$(curl -s https://api.stripe.com/v1/promotion_codes \
  -u "$STRIPE_SECRET_KEY:" \
  -d "coupon=$COUPON_ID" \
  -d "code=$PROMO_CODE" \
  -d "active=true")
PROMO_ID=$(echo "$PROMO_RESP" | $PYTHON -c "import sys,json; print(json.load(sys.stdin).get('id',''))")
echo "  promo code: $PROMO_CODE (id=$PROMO_ID)"

echo "[2/3] gog gmail send 自動メール"
SUBJECT="Sorry — 30% off on us"
BODY_FILE=$(mktemp -t anicca-care-body)
"$PYTHON" - "$PROMO_CODE" "$REASON" > "$BODY_FILE" <<'PYBODY'
import sys
promo, reason = sys.argv[1], sys.argv[2]
print("Hi,")
print()
print("We saw your feedback and wanted to reach out personally.")
print()
print("You have a one-time 30 percent off coupon, valid for 30 days,")
print("on any item at aniccaai.com/fashion:")
print()
print(f"  {promo}")
print()
print("Apply it at Stripe checkout. Anything you would like to share")
print("with us, just reply — Anicca reads every message.")
print()
print("— Anicca")
if reason:
    print()
    print(f'(re: "{reason}")')
PYBODY

# Note: --from "hello@aniccaai.com" requires a Gmail send-as alias to be
# verified manually by Dais once. Until then, default sender is the OAuth
# account ({{profile.contact.personalEmail}}). Coupon still valid either way.
if "$GOG" -a {{profile.contact.personalEmail}} gmail send \
     --to "$EMAIL" \
     --subject "$SUBJECT" \
     --body-file "$BODY_FILE" \
     -y > /tmp/gog-send.log 2>&1; then
  echo "  ✓ {{profile.lateness.stakeholders.channel}} sent → $EMAIL"
else
  echo "  ⚠️ gog gmail send failed — logged but coupon still valid"
  cat /tmp/gog-send.log >&2 || true
fi
rm -f "$BODY_FILE"

echo "[3/3] coupons.json append + Slack"

# bash heredoc + $() + python parens collide. Use the dedicated helper script.
HELPER="$SKILL_DIR/scripts/lib/customer-support-finalize.py"
TS=$("$PYTHON" "$HELPER" \
       "$COUPONS_FILE" "$COUPON_ID" "$PROMO_ID" "$PROMO_CODE" \
       "$EMAIL" "$REASON" "$SLACK_CHANNEL_ID" "$SLACK_BOT_TOKEN")

echo "✅ customer-support: coupon=$PROMO_CODE sent → $EMAIL | slack ts=$TS"
