#!/usr/bin/env bash
# adapters/custom/coconala/scripts/login.sh
# Open coconala.com via camofox visible mode, complete Google OAuth using env creds,
# persist cookie under ~/.camofox/profiles/anicca/coconala/.
#
# Exit:
#   0 = session live
#   2 = camofox not running / OAuth failure
#   3 = CAPTCHA hit

set -uo pipefail
[ -f "$HOME/.openclaw/.env" ] && set -a && . "$HOME/.openclaw/.env" && set +a

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ADAPTER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
STATE_DIR="$ADAPTER_DIR/state"
mkdir -p "$STATE_DIR"

USER_ID="anicca"
SESSION_KEY="coconala"
CAMOFOX="http://127.0.0.1:9377"
TARGET="https://coconala.com/mypage/inbox"

if ! curl -sS "$CAMOFOX/health" | grep -q '"ok":true'; then
  echo "[coconala/login] camofox not alive" >&2
  exit 2
fi

TAB_ID=$(curl -sS -X POST "$CAMOFOX/tabs" \
  -H 'Content-Type: application/json' \
  -d "{\"url\":\"$TARGET\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" \
  | jq -r '.tabId // empty')

[ -z "$TAB_ID" ] && { echo "[coconala/login] tab open failed" >&2; exit 2; }
sleep 2

SNAP_RAW=$(curl -sS "$CAMOFOX/tabs/$TAB_ID/snapshot?userId=$USER_ID&sessionKey=$SESSION_KEY")
SNAP=$(echo "$SNAP_RAW" | jq -r '.snapshot // empty' 2>/dev/null)
[ -z "$SNAP" ] && SNAP="$SNAP_RAW"

if echo "$SNAP" | grep -qiE 'captcha|recaptcha|hcaptcha|cloudflare challenge'; then
  echo "[coconala/login] CAPTCHA — exit per HARD RULE #-1" >&2
  echo "$SNAP" | head -c 2000 > "$STATE_DIR/last-captcha-block.txt"
  exit 3
fi

if echo "$SNAP" | grep -qE 'マイページ|やりとり一覧|新着メッセージ|お知らせ'; then
  STATUS="reused-existing-session"
else
  curl -sS -X POST "$CAMOFOX/tabs" \
    -H 'Content-Type: application/json' \
    -d "{\"url\":\"https://coconala.com/login\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" >/dev/null
  sleep 2

  if [ -z "${GOOGLE_LOGIN_EMAIL:-}" ] || [ -z "${GOOGLE_LOGIN_PASSWORD:-}" ]; then
    echo "[coconala/login] GOOGLE_LOGIN_EMAIL / PASSWORD missing" >&2
    exit 2
  fi

  sleep 1
  LOGIN_SNAP_RAW=$(curl -sS "$CAMOFOX/tabs/$TAB_ID/snapshot?userId=$USER_ID&sessionKey=$SESSION_KEY" || true)
  LOGIN_SNAP=$(echo "$LOGIN_SNAP_RAW" | jq -r '.snapshot // empty' 2>/dev/null)
  [ -z "$LOGIN_SNAP" ] && LOGIN_SNAP="$LOGIN_SNAP_RAW"

  GOOGLE_REF=$(echo "$LOGIN_SNAP" | grep -iE '"[^"]*google[^"]*"\s*\[e[0-9]+\]' | grep -oE 'e[0-9]+' | head -1)

  if [ -n "$GOOGLE_REF" ] && [ "$GOOGLE_REF" != "null" ]; then
    curl -sS -X POST "$CAMOFOX/tabs/$TAB_ID/click" \
      -H 'Content-Type: application/json' \
      -d "{\"ref\":\"$GOOGLE_REF\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" >/dev/null
    sleep 3
  fi
  STATUS="oauth-initiated"
fi

COOKIE_DIR="$HOME/.camofox/profiles/$USER_ID/$SESSION_KEY"
cat > "$STATE_DIR/coconala-session.json" <<EOF
{
  "userId": "$USER_ID",
  "sessionKey": "$SESSION_KEY",
  "cookie_dir": "$COOKIE_DIR",
  "tab_id": "$TAB_ID",
  "status": "$STATUS",
  "last_login_attempt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
chmod 600 "$STATE_DIR/coconala-session.json"

echo "[coconala/login] $STATUS — session meta saved to $STATE_DIR/coconala-session.json"
exit 0
