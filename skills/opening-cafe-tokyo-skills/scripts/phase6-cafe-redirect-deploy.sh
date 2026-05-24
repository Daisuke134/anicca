#!/usr/bin/env bash
# phase6-cafe-redirect-deploy.sh — landing /cafe を Uber Eats store URL にリダイレクト
# Prerequisites: Phase 4 live + Phase 5 menu published
set -uo pipefail

SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills
CONFIG="$SKILL/data/config.json"
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

MID=$(jq -r '.merchant_id // empty' "$SKILL/data/cafe/uber_signup.json" 2>/dev/null)
LIVE_AT=$(jq -r '.live_at // empty' "$SKILL/data/cafe/uber_signup.json" 2>/dev/null)
[ -z "$MID" ] || [ -z "$LIVE_AT" ] && { echo "ERR: Uber merchant not live yet"; exit 1; }

REDIRECT_PATH=$(jq -r '.landing_redirect_path' "$CONFIG")
UBER_STORE_URL="https://www.ubereats.com/jp/store/$MID"
LANDING_REPO=~/anicca-products
NEXT_CONFIG="$LANDING_REPO/apps/landing/next.config.mjs"

echo "▶ Phase 6: $REDIRECT_PATH → $UBER_STORE_URL"

[ ! -f "$NEXT_CONFIG" ] && { echo "ERR: $NEXT_CONFIG missing"; exit 1; }

# TODO: idempotent edit — skip if redirect already added
echo "  TODO: edit $NEXT_CONFIG redirects() に追加: { source: '$REDIRECT_PATH', destination: '$UBER_STORE_URL', permanent: false }"
echo "  TODO: TheEmpireProducts.tsx の cafe card href も $UBER_STORE_URL に変更"
echo "  TODO: git add+commit+push → Netlify auto-deploy → URL 動作確認"

mkdir -p "$SKILL/data/cafe"
cat > "$SKILL/data/cafe/redirect.json" <<EOF
{
  "status": "pending_implementation",
  "redirect_path": "$REDIRECT_PATH",
  "destination": "$UBER_STORE_URL",
  "merchant_id": "$MID",
  "deployed_at": null
}
EOF

# Slack 報告 (5/9 v27 fix)
PYTHON=python3
TS=$("$PYTHON" - "$SLACK_CHANNEL_ID" "$SLACK_BOT_TOKEN" "$REDIRECT_PATH" "$UBER_STORE_URL" "$MID" <<'PY'
import sys, json, urllib.request
ch, token, rpath, uurl, mid = sys.argv[1:6]
payload = {
    "channel": ch,
    "text": f"🌐 cafe-phase6-redirect: {rpath} → Uber",
    "blocks": [
        {"type":"header","text":{"type":"plain_text","text":"🌐 cafe-phase6-redirect-deploy"}},
        {"type":"section","fields":[
            {"type":"mrkdwn","text":f"*landing path:*\n{rpath}"},
            {"type":"mrkdwn","text":f"*uber store URL:*\n{uurl}"},
            {"type":"mrkdwn","text":f"*merchant_id:*\n`{mid}`"},
            {"type":"mrkdwn","text":"*status:*\npending_implementation"},
        ]},
        {"type":"context","elements":[{"type":"mrkdwn","text":"TODO: next.config.mjs redirects() + git push → Netlify deploy"}]},
    ]
}
req = urllib.request.Request(
    "https://slack.com/api/chat.postMessage",
    data=json.dumps(payload).encode(),
    headers={"Authorization":f"Bearer {token}","Content-Type":"application/json; charset=utf-8"},
    method="POST")
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        print(json.loads(r.read().decode()).get("ts","?"))
except Exception:
    print("?")
PY
)

echo "✅ phase6-redirect-deploy: $REDIRECT_PATH → $UBER_STORE_URL | slack ts=$TS"
