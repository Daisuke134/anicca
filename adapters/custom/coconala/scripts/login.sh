#!/usr/bin/env bash
# adapters/custom/coconala/scripts/login.sh
# Coconala session bootstrap. Mirrors Lancers pattern: tries email-pw first
# (= COCONALA_EMAIL / COCONALA_PASSWORD from ~/.openclaw/.env), then falls back
# to Google OAuth if the credentials are not set.
#
# Exit:
#   0 = /mypage reached
#   2 = camofox down / env missing / login failure
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

if ! curl -sS -m 10 "$CAMOFOX/health" | grep -q '"ok":true'; then
  echo "[coconala/login] camofox not alive on $CAMOFOX" >&2
  exit 2
fi

# Coconala redirects /mypage → / on first hit, so probe the actual dashboard.
TAB_ID=$(curl -sS -m 30 -X POST "$CAMOFOX/tabs" \
  -H 'Content-Type: application/json' \
  -d "{\"url\":\"https://coconala.com/mypage/dashboard_provider\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" \
  | jq -r '.tabId // empty')
[ -z "$TAB_ID" ] && { echo "[coconala/login] tab open failed" >&2; exit 2; }
sleep 5

snap_pull() {
  local raw t url
  raw=$(curl -sS -m 30 "$CAMOFOX/tabs/$TAB_ID/snapshot?userId=$USER_ID&sessionKey=$SESSION_KEY" 2>/dev/null)
  url=$(echo "$raw" | jq -r '.url // empty' 2>/dev/null)
  t=$(echo "$raw" | jq -r '.snapshot // empty' 2>/dev/null)
  [ -z "$t" ] && t="$raw"
  printf "%s\n--URL--\n%s\n" "$t" "$url"
}

CHUNK=$(snap_pull)
URL=$(echo "$CHUNK" | awk '/^--URL--$/{flag=1; next} flag {print}')
SNAP=$(echo "$CHUNK" | awk '/^--URL--$/{exit} {print}')

if echo "$SNAP" | grep -qiE 'captcha|recaptcha|hcaptcha|cloudflare challenge'; then
  echo "[coconala/login] CAPTCHA — exit per HARD RULE #-1" >&2
  echo "$SNAP" | head -c 4000 > "$STATE_DIR/last-captcha-block.txt"
  exit 3
fi

# Authenticated marker: dashboard nav rendered (ダッシュボード / 取引管理 / etc.),
# OR URL is dashboard_provider without /login redirect.
if echo "$SNAP" | grep -qE 'link "ダッシュボード"|link "取引管理"|link "サービス管理"|発注モードへ切替'; then
  STATUS="reused-existing-session"
else
  # Fresh login. Try email-pw if present, else fall back to Google OAuth.
  curl -sS -m 30 -X POST "$CAMOFOX/tabs" \
    -H 'Content-Type: application/json' \
    -d "{\"url\":\"https://coconala.com/login\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" >/dev/null
  sleep 5
  CHUNK=$(snap_pull)
  SNAP=$(echo "$CHUNK" | awk '/^--URL--$/{exit} {print}')

  STATUS="login-attempt-unconfirmed"

  if [ -n "${COCONALA_EMAIL:-}" ] && [ -n "${COCONALA_PASSWORD:-}" ]; then
    EMAIL_REF=$(echo "$SNAP" | grep -iE 'textbox\s+"(メール|Email|ID)' | grep -oE 'e[0-9]+' | head -1)
    PW_REF=$(echo "$SNAP" | grep -iE 'textbox\s+"(パスワード|Password)' | grep -oE 'e[0-9]+' | head -1)
    # Coconala's email-pw button label is " メールアドレスでログインする" (leading space).
    LOGIN_REF=$(echo "$SNAP" | grep -iE 'button\s+"[^"]*メールアドレスでログイン' | grep -oE 'e[0-9]+' | head -1)
    [ -z "$LOGIN_REF" ] && LOGIN_REF=$(echo "$SNAP" | grep -iE 'button\s+"[^"]*ログイン[^"]*"' | grep -oE 'e[0-9]+' | head -1)

    if [ -n "$EMAIL_REF" ] && [ -n "$PW_REF" ] && [ -n "$LOGIN_REF" ]; then
      curl -sS -m 30 -X POST "$CAMOFOX/tabs/$TAB_ID/type" \
        -H 'Content-Type: application/json' \
        -d "$(jq -nc --arg ref "$EMAIL_REF" --arg t "$COCONALA_EMAIL" '{ref:$ref,text:$t,userId:"anicca",sessionKey:"coconala"}')" >/dev/null
      curl -sS -m 30 -X POST "$CAMOFOX/tabs/$TAB_ID/type" \
        -H 'Content-Type: application/json' \
        -d "$(jq -nc --arg ref "$PW_REF" --arg t "$COCONALA_PASSWORD" '{ref:$ref,text:$t,userId:"anicca",sessionKey:"coconala"}')" >/dev/null
      curl -sS -m 60 -X POST "$CAMOFOX/tabs/$TAB_ID/click" \
        -H 'Content-Type: application/json' \
        -d "{\"ref\":\"$LOGIN_REF\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" >/dev/null 2>&1 || true
      sleep 5
    fi
  elif [ -n "${GOOGLE_LOGIN_EMAIL:-}" ]; then
    # Google OAuth fallback (if Coconala account is Google-linked)
    GOOGLE_REF=$(echo "$SNAP" | grep -iE 'button\s+"[^"]*Google[^"]*"|link\s+"[^"]*Google[^"]*"' | grep -oE 'e[0-9]+' | head -1)
    if [ -n "$GOOGLE_REF" ]; then
      curl -sS -m 60 -X POST "$CAMOFOX/tabs/$TAB_ID/click" \
        -H 'Content-Type: application/json' \
        -d "{\"ref\":\"$GOOGLE_REF\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" >/dev/null 2>&1 || true
      sleep 5
    fi
  fi

  curl -sS -m 30 -X POST "$CAMOFOX/tabs" \
    -H 'Content-Type: application/json' \
    -d "{\"url\":\"https://coconala.com/mypage/dashboard_provider\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" >/dev/null
  sleep 5
  CHUNK=$(snap_pull)
  FINAL_SNAP=$(echo "$CHUNK" | awk '/^--URL--$/{exit} {print}')
  if echo "$FINAL_SNAP" | grep -qE 'link "ダッシュボード"|link "取引管理"|link "サービス管理"|発注モードへ切替'; then
    STATUS="fresh-login-ok"
  fi
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
case "$STATUS" in
  reused-existing-session|fresh-login-ok) exit 0 ;;
  *) exit 2 ;;
esac
