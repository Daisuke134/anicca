#!/usr/bin/env bash
# adapters/custom/lancers/scripts/login.sh
# Lancers session bootstrap. Live-verified 2026-06-03:
#   - Google OAuth path FAILS ("この Google で会員登録されていません") because
#     `keiodaisuke@gmail.com` is not linked. The Lancers account is registered
#     under `keiodaisuke+anicca@gmail.com` + raw password (= existing MEMORY.md
#     entry: "Lancers Google login 違反 = re-link 宿題").
#   - Working path: email-pw login → email 2FA code → /mypage redirect.
#   - 2FA code is auto-fetched from Gmail via `gog` CLI (forwarded from the
#     +anicca alias to keiodaisuke@gmail.com).
#
# Exit:
#   0 = /mypage reached (session live)
#   2 = camofox down / env missing / login failure
#   3 = CAPTCHA hit (per HARD RULE #-1, no Dais escalation)

set -uo pipefail
[ -f "$HOME/.openclaw/.env" ] && set -a && . "$HOME/.openclaw/.env" && set +a

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ADAPTER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
STATE_DIR="$ADAPTER_DIR/state"
mkdir -p "$STATE_DIR"

USER_ID="anicca"
SESSION_KEY="lancers"
CAMOFOX="http://127.0.0.1:9377"

# 1. Health check
if ! curl -sS -m 10 "$CAMOFOX/health" | grep -q '"ok":true'; then
  echo "[lancers/login] camofox not alive on $CAMOFOX" >&2
  exit 2
fi

# 2. Probe existing session by hitting /mypage
TAB_ID=$(curl -sS -m 30 -X POST "$CAMOFOX/tabs" \
  -H 'Content-Type: application/json' \
  -d "{\"url\":\"https://www.lancers.jp/mypage\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" \
  | jq -r '.tabId // empty')

if [ -z "$TAB_ID" ]; then
  echo "[lancers/login] failed to open tab" >&2
  exit 2
fi
sleep 4

snapshot_text() {
  local raw
  raw=$(curl -sS -m 30 "$CAMOFOX/tabs/$TAB_ID/snapshot?userId=$USER_ID&sessionKey=$SESSION_KEY" 2>/dev/null || true)
  local t
  t=$(echo "$raw" | jq -r '.snapshot // empty' 2>/dev/null)
  [ -z "$t" ] && t="$raw"
  echo "$t"
}

current_url() {
  curl -sS -m 30 "$CAMOFOX/tabs/$TAB_ID/snapshot?userId=$USER_ID&sessionKey=$SESSION_KEY" 2>/dev/null \
    | jq -r '.url // empty' 2>/dev/null
}

SNAP=$(snapshot_text)
URL=$(current_url)

if echo "$SNAP" | grep -qiE 'captcha|recaptcha|hcaptcha|cloudflare challenge'; then
  echo "[lancers/login] CAPTCHA — exit per HARD RULE #-1" >&2
  echo "$SNAP" | head -c 4000 > "$STATE_DIR/last-captcha-block.txt"
  exit 3
fi

# Real /mypage shows the user role nav (ランサーメニュー / マイページ / etc.)
if echo "$URL" | grep -q '/mypage' && echo "$SNAP" | grep -qE 'ランサーメニュー|anicca_ai_jp|発注者に切り替え'; then
  STATUS="reused-existing-session"
else
  # 3. Need fresh login. Email-pw is the only path that works.
  if [ -z "${LANCERS_EMAIL:-}" ] || [ -z "${LANCERS_PASSWORD:-}" ]; then
    echo "[lancers/login] LANCERS_EMAIL / LANCERS_PASSWORD missing in env" >&2
    exit 2
  fi

  # Navigate to login page
  curl -sS -m 30 -X POST "$CAMOFOX/tabs" \
    -H 'Content-Type: application/json' \
    -d "{\"url\":\"https://www.lancers.jp/user/login\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" >/dev/null
  sleep 4
  SNAP=$(snapshot_text)

  # Find email + password + login button refs (text snapshot)
  EMAIL_REF=$(echo "$SNAP" | grep -E 'textbox\s+"メールアドレス"' | grep -oE 'e[0-9]+' | head -1)
  PW_REF=$(echo "$SNAP" | grep -E 'textbox\s+"パスワード"' | grep -oE 'e[0-9]+' | head -1)
  LOGIN_REF=$(echo "$SNAP" | grep -E 'button\s+"ログイン"' | grep -oE 'e[0-9]+' | head -1)

  if [ -z "$EMAIL_REF" ] || [ -z "$PW_REF" ] || [ -z "$LOGIN_REF" ]; then
    echo "[lancers/login] login form refs not found (EMAIL=$EMAIL_REF PW=$PW_REF LOGIN=$LOGIN_REF)" >&2
    exit 2
  fi

  curl -sS -m 30 -X POST "$CAMOFOX/tabs/$TAB_ID/type" \
    -H 'Content-Type: application/json' \
    -d "$(jq -nc --arg ref "$EMAIL_REF" --arg t "$LANCERS_EMAIL" '{ref:$ref,text:$t,userId:"anicca",sessionKey:"lancers"}')" >/dev/null
  curl -sS -m 30 -X POST "$CAMOFOX/tabs/$TAB_ID/type" \
    -H 'Content-Type: application/json' \
    -d "$(jq -nc --arg ref "$PW_REF" --arg t "$LANCERS_PASSWORD" '{ref:$ref,text:$t,userId:"anicca",sessionKey:"lancers"}')" >/dev/null

  # Submit; click endpoint can stall on nav, treat timeout as fire-and-forget
  curl -sS -m 60 -X POST "$CAMOFOX/tabs/$TAB_ID/click" \
    -H 'Content-Type: application/json' \
    -d "{\"ref\":\"$LOGIN_REF\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" >/dev/null 2>&1 || true
  sleep 4

  URL=$(current_url)
  if echo "$URL" | grep -q 'verify_code'; then
    # 4. Fetch 6-digit code from Gmail using `gog` if available
    CODE=""
    if command -v gog >/dev/null 2>&1; then
      CODE=$(gog gmail search 'from:lancers.co.jp subject:ログイン認証コード newer_than:1h' --limit 1 --json 2>/dev/null \
        | jq -r '.[0].snippet // empty' 2>/dev/null \
        | grep -oE '[0-9]{6}' | head -1)
    fi
    if [ -z "$CODE" ]; then
      echo "[lancers/login] verify_code page reached but no gog CLI / Gmail code found" >&2
      echo "[lancers/login] use an external Gmail fetcher to type the 6-digit code into ref [textbox '認証コード']" >&2
      exit 2
    fi
    SNAP=$(snapshot_text)
    CODE_REF=$(echo "$SNAP" | grep -E 'textbox\s+"認証コード"' | grep -oE 'e[0-9]+' | head -1)
    VERIFY_REF=$(echo "$SNAP" | grep -E 'button\s+"認証する"' | grep -oE 'e[0-9]+' | head -1)
    if [ -n "$CODE_REF" ] && [ -n "$VERIFY_REF" ]; then
      curl -sS -m 30 -X POST "$CAMOFOX/tabs/$TAB_ID/type" \
        -H 'Content-Type: application/json' \
        -d "$(jq -nc --arg ref "$CODE_REF" --arg t "$CODE" '{ref:$ref,text:$t,userId:"anicca",sessionKey:"lancers"}')" >/dev/null
      curl -sS -m 60 -X POST "$CAMOFOX/tabs/$TAB_ID/click" \
        -H 'Content-Type: application/json' \
        -d "{\"ref\":\"$VERIFY_REF\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" >/dev/null 2>&1 || true
      sleep 4
    fi
  fi

  # 5. Confirm by re-probing /mypage
  curl -sS -m 30 -X POST "$CAMOFOX/tabs" \
    -H 'Content-Type: application/json' \
    -d "{\"url\":\"https://www.lancers.jp/mypage\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" >/dev/null
  sleep 3
  FINAL=$(snapshot_text)
  if echo "$FINAL" | grep -qE 'ランサーメニュー|発注者に切り替え'; then
    STATUS="fresh-login-ok"
  else
    STATUS="login-attempt-unconfirmed"
  fi
fi

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
case "$STATUS" in
  reused-existing-session|fresh-login-ok) exit 0 ;;
  *) exit 2 ;;
esac
