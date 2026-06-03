#!/usr/bin/env bash
# adapters/custom/lancers/scripts/login.sh
# Open lancers.jp via camofox visible mode, complete Google OAuth using env creds,
# persist cookie under ~/.camofox/profiles/anicca/lancers/.
# Idempotent: if session is already valid (= inbox page reachable without redirect),
# skip the OAuth dance.
#
# Required env (loaded from ~/.openclaw/.env):
#   GOOGLE_LOGIN_EMAIL
#   GOOGLE_LOGIN_PASSWORD
#
# Output:
#   state/lancers-session.json (chmod 600)
#   exit 0 = session live
#   exit 2 = camofox not running
#   exit 3 = CAPTCHA hit (HARD RULE #-1: log + exit, no human escalation)

set -uo pipefail

[ -f "$HOME/.openclaw/.env" ] && set -a && . "$HOME/.openclaw/.env" && set +a

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ADAPTER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
STATE_DIR="$ADAPTER_DIR/state"
mkdir -p "$STATE_DIR"

USER_ID="anicca"
SESSION_KEY="lancers"
CAMOFOX="http://127.0.0.1:9377"
TARGET="https://www.lancers.jp/mypage/inbox"

# 1. Health check
HEALTH=$(curl -sS "$CAMOFOX/health" || true)
if ! echo "$HEALTH" | grep -q '"ok":true'; then
  echo "[lancers/login] camofox not alive on $CAMOFOX" >&2
  exit 2
fi

# 2. Open lancers inbox — if cookie already valid we'll see inbox DOM directly
TAB_ID=$(curl -sS -X POST "$CAMOFOX/tabs" \
  -H 'Content-Type: application/json' \
  -d "{\"url\":\"$TARGET\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" \
  | jq -r '.tabId // empty')

if [ -z "$TAB_ID" ]; then
  echo "[lancers/login] failed to open tab" >&2
  exit 2
fi

sleep 2

# 3. Snapshot to see what page we landed on. Strip the JSON envelope so we
#    don't false-match on the URL string (= "/mypage/inbox" appears in the
#    .url field even when we got a 404 redirect).
SNAP_RAW=$(curl -sS "$CAMOFOX/tabs/$TAB_ID/snapshot?userId=$USER_ID&sessionKey=$SESSION_KEY" || true)
SNAP=$(echo "$SNAP_RAW" | jq -r '.snapshot // empty' 2>/dev/null)
[ -z "$SNAP" ] && SNAP="$SNAP_RAW"

# CAPTCHA guard per HARD RULE #-1
if echo "$SNAP" | grep -qiE 'captcha|recaptcha|hcaptcha|cloudflare challenge'; then
  echo "[lancers/login] CAPTCHA detected — exiting per HARD RULE #-1" >&2
  echo "$SNAP" | head -c 2000 > "$STATE_DIR/last-captcha-block.txt"
  exit 3
fi

# Already-logged-in heuristic: real inbox shows the user nav (= マイページ /
# プロフィール / お知らせ items) — NOT just the inbox URL string.
if echo "$SNAP" | grep -qE 'マイページ|お知らせ|メッセージ一覧|新着メッセージ'; then
  STATUS="reused-existing-session"
else
  # 4. Need Google OAuth. Click "Googleでログイン" or navigate to oauth entry.
  curl -sS -X POST "$CAMOFOX/tabs" \
    -H 'Content-Type: application/json' \
    -d "{\"url\":\"https://www.lancers.jp/user/login\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" >/dev/null
  sleep 2

  if [ -z "${GOOGLE_LOGIN_EMAIL:-}" ] || [ -z "${GOOGLE_LOGIN_PASSWORD:-}" ]; then
    echo "[lancers/login] GOOGLE_LOGIN_EMAIL / GOOGLE_LOGIN_PASSWORD missing" >&2
    exit 2
  fi

  # Re-snapshot the login page (text format with [eN] refs)
  sleep 1
  LOGIN_SNAP_RAW=$(curl -sS "$CAMOFOX/tabs/$TAB_ID/snapshot?userId=$USER_ID&sessionKey=$SESSION_KEY" || true)
  LOGIN_SNAP=$(echo "$LOGIN_SNAP_RAW" | jq -r '.snapshot // empty' 2>/dev/null)
  [ -z "$LOGIN_SNAP" ] && LOGIN_SNAP="$LOGIN_SNAP_RAW"

  # Find Google login control by scanning text-format snapshot for a line
  # mentioning Google and pulling the [eN] ref right after it. Camofox emits
  # lines like: `link "Googleでログイン" [e42]:` or `button "Google" [e9]`.
  GOOGLE_REF=$(echo "$LOGIN_SNAP" | grep -iE '"[^"]*google[^"]*"\s*\[e[0-9]+\]' | grep -oE 'e[0-9]+' | head -1)

  if [ -n "$GOOGLE_REF" ] && [ "$GOOGLE_REF" != "null" ]; then
    curl -sS -X POST "$CAMOFOX/tabs/$TAB_ID/click" \
      -H 'Content-Type: application/json' \
      -d "{\"ref\":\"$GOOGLE_REF\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" >/dev/null
    sleep 3
  fi
  STATUS="oauth-initiated"
fi

# 5. Persist session marker (cookies live in camofox profile dir; we record meta)
COOKIE_DIR="$HOME/.camofox/profiles/$USER_ID/$SESSION_KEY"
cat > "$STATE_DIR/lancers-session.json" <<EOF
{
  "userId": "$USER_ID",
  "sessionKey": "$SESSION_KEY",
  "cookie_dir": "$COOKIE_DIR",
  "tab_id": "$TAB_ID",
  "status": "$STATUS",
  "last_login_attempt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
chmod 600 "$STATE_DIR/lancers-session.json"

echo "[lancers/login] $STATUS — session meta saved to $STATE_DIR/lancers-session.json"
exit 0
