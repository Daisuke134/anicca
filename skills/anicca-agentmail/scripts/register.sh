#!/usr/bin/env bash
# anicca-agentmail/scripts/register.sh
# agentmail.to に Anicca own inbox を REST API 経由で作成

set -uo pipefail
[ -f "$HOME/.openclaw/.env" ] && set -a && source "$HOME/.openclaw/.env" && set +a

SKILL_DIR="$HOME/.openclaw/skills/anicca-agentmail"
STATE="$SKILL_DIR/state"
mkdir -p "$STATE"

if [ -f "$STATE/inbox.json" ]; then
  echo "[anicca-agentmail] existing inbox found, skipping"
  cat "$STATE/inbox.json"
  exit 0
fi

if [ -z "${AGENTMAIL_API_KEY:-}" ]; then
  cat <<'EOF' >&2
[anicca-agentmail] AGENTMAIL_API_KEY not set.

Day 0 bootstrap (1 回限り):
  1. Open https://agentmail.to in a browser
  2. Sign up (= 1 度 必要、 install user の既存 AI tool / Anicca自身が camofox で)
  3. Get API key from dashboard
  4. Add to ~/.openclaw/.env:
       AGENTMAIL_API_KEY=ak_...
  5. Re-run this script

After this 1-time setup all subsequent inboxes auto-create via API.
EOF
  exit 2
fi

# Create inbox via REST API
RESP=$(curl -sS -X POST "https://agentmail.to/api/v1/inboxes" \
  -H "Authorization: Bearer $AGENTMAIL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Anicca Agent",
    "purpose": "autonomous AI agent identity"
  }')

if echo "$RESP" | jq -e '.email' > /dev/null 2>&1; then
  echo "$RESP" | jq '{
    email: .email,
    inbox_id: .id,
    created_at: .created_at
  }' > "$STATE/inbox.json"
  chmod 600 "$STATE/inbox.json"

  EMAIL=$(jq -r .email "$STATE/inbox.json")
  echo "[anicca-agentmail] ✓ Created inbox: $EMAIL"

  # Save to .env
  ENV="$HOME/.openclaw/.env"
  if ! grep -q "^ANICCA_EMAIL=" "$ENV" 2>/dev/null; then
    echo "" >> "$ENV"
    echo "# anicca-agentmail (auto-generated $(date +%Y-%m-%d))" >> "$ENV"
    echo "ANICCA_EMAIL=$EMAIL" >> "$ENV"
  fi
else
  echo "[anicca-agentmail] ERR: agentmail.to API returned:" >&2
  echo "$RESP" >&2
  exit 1
fi
