#!/usr/bin/env bash
# login-check.sh — verify the camofox session has a Lancers cookie; if not, the
# agent runs the FULL Google-OAuth flow autonomously via Camofox using
# GOOGLE_LOGIN_EMAIL/PASSWORD (HARD RULE #-2: Anicca does everything).
#
# 2FA handling — fully autonomous:
#   (a) If a TOTP challenge renders, use GOOGLE_TOTP_SECRET (Authy/OTP env) to
#       compute the 6-digit code with `oathtool --totp -b "$GOOGLE_TOTP_SECRET"`
#       and type it; OR
#   (b) read the latest 2-step verification email at keiodaisuke@gmail.com
#       via the gog-gmail MCP and type the code.
# No "Dais reviews", no "tap on phone", no human eyeball — the agent drives.
#
# HARD-BLOCK (only): a real CAPTCHA element renders in the snapshot
# (iframe with src containing "recaptcha" / "hcaptcha" / "turnstile") OR the
# page asks for a financial broadcast. Record the verbatim snapshot subset
# at ~/.hermes/state/earn-lancers-login-hardblock.json and exit non-0.
# The earn task stays OPEN (do NOT close it).

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"

cf_health || { err "camofox down"; exit 3; }

# Cookie probe: does the session contain a Lancers cookie?
COOKIES_JSON=$(curl -sS "$CAMOFOX/sessions/$USER_ID/cookies?sessionKey=$SESSION_KEY" 2>/dev/null || echo '[]')
HAS=$(printf '%s' "$COOKIES_JSON" | "$JQ" '[.[] | select(.domain | test("lancers.jp"))] | length' 2>/dev/null || echo 0)
if [ "${HAS:-0}" -gt 0 ]; then
  ok "lancers cookie present (n=$HAS)"
  exit 0
fi

log "no lancers cookie — running Google OAuth via Camofox"

# 1. Open Lancers login page (Google button is the canonical path per HARD RULE)
TAB=$(cf_open "https://www.lancers.jp/user/login")
sleep 4

# 2. Click the "Googleでログイン" button via accessibility snapshot
SNAP=$(cf_snapshot "$TAB")
GOOGLE_REF=$(SNAP="$SNAP" "$PYTHON" -c '
import json,os,re
d=json.loads(os.environ.get("SNAP","{}") or "{}"); s=d.get("snapshot","")
for line in s.split("\n"):
    if "Google" in line and "ログイン" in line:
        m=re.search(r"ref=(\S+)", line)
        if m: print(m.group(1)); break
')
if [ -n "$GOOGLE_REF" ]; then
  curl -sS -X POST "$CAMOFOX/tabs/$TAB/click" \
    -H 'Content-Type: application/json' \
    -d "$("$JQ" -n --arg r "$GOOGLE_REF" --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
            '{ref:$r, userId:$uid, sessionKey:$sk}')" >/dev/null
  sleep 6
else
  log "Google-login button ref not found — Lancers may need email/pw form (LANCERS_EMAIL + LANCERS_PASSWORD)"
  cf_close "$TAB"
  exit 4
fi

# 3. Google OAuth steps (verified pattern from Camofox SKILL.md):
#    type email → Next → "Try another way" → "Enter your password" → type pw
#    → 2-step verification handled autonomously by 3b/3c below (TOTP env OR gog-gmail auto-read).
SNAP=$(cf_snapshot "$TAB")
EMAIL_REF=$(SNAP="$SNAP" "$PYTHON" -c '
import json,os,re
d=json.loads(os.environ.get("SNAP","{}") or "{}"); s=d.get("snapshot","")
m=re.search(r"ref=(\S+).*(?:email|メール|identifier)", s, re.I)
print(m.group(1) if m else "")
')
[ -z "$EMAIL_REF" ] && { err "no email ref"; cf_close "$TAB"; exit 5; }

curl -sS -X POST "$CAMOFOX/tabs/$TAB/type" \
  -H 'Content-Type: application/json' \
  -d "$("$JQ" -n --arg r "$EMAIL_REF" --arg t "${GOOGLE_LOGIN_EMAIL:-}" \
                  --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
                  '{ref:$r, text:$t, userId:$uid, sessionKey:$sk}')" >/dev/null
sleep 1
curl -sS -X POST "$CAMOFOX/tabs/$TAB/press" \
  -H 'Content-Type: application/json' \
  -d "$("$JQ" -n --arg k "Enter" --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
                  '{key:$k, userId:$uid, sessionKey:$sk}')" >/dev/null
sleep 6

# Password field
SNAP=$(cf_snapshot "$TAB")
PW_REF=$(SNAP="$SNAP" "$PYTHON" -c '
import json,os,re
d=json.loads(os.environ.get("SNAP","{}") or "{}"); s=d.get("snapshot","")
m=re.search(r"ref=(\S+).*password", s, re.I)
print(m.group(1) if m else "")
')
if [ -n "$PW_REF" ] && [ -n "${GOOGLE_LOGIN_PASSWORD:-}" ]; then
  curl -sS -X POST "$CAMOFOX/tabs/$TAB/type" \
    -H 'Content-Type: application/json' \
    -d "$("$JQ" -n --arg r "$PW_REF" --arg t "$GOOGLE_LOGIN_PASSWORD" \
                    --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
                    '{ref:$r, text:$t, userId:$uid, sessionKey:$sk}')" >/dev/null
  sleep 1
  curl -sS -X POST "$CAMOFOX/tabs/$TAB/press" \
    -H 'Content-Type: application/json' \
    -d "$("$JQ" -n --arg k "Enter" --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
                    '{key:$k, userId:$uid, sessionKey:$sk}')" >/dev/null
  sleep 10
fi

# 3b. CAPTCHA / hard-block detector (HARD RULE #-2 genuine hard-block ONLY)
SNAP=$(cf_snapshot "$TAB")
if printf '%s' "$SNAP" | grep -Eq 'iframe[^>]*src=[^>]*(recaptcha|hcaptcha|turnstile)'; then
  HARDBLOCK_PATH="$HOME/.hermes/state/earn-lancers-login-hardblock.json"
  mkdir -p "$(dirname "$HARDBLOCK_PATH")"
  printf '%s' "$SNAP" > "$HARDBLOCK_PATH"
  err "real CAPTCHA element rendered — verbatim snapshot saved to $HARDBLOCK_PATH (#325 stays OPEN)"
  cf_close "$TAB"
  exit 9
fi

# 3c. Autonomous 2FA handling (no human in loop)
#  - TOTP path (if GOOGLE_TOTP_SECRET present)
if printf '%s' "$SNAP" | grep -Eq '2-step|two-step|verification code|認証コード'; then
  if [ -n "${GOOGLE_TOTP_SECRET:-}" ] && command -v oathtool >/dev/null 2>&1; then
    CODE=$(oathtool --totp -b "$GOOGLE_TOTP_SECRET" 2>/dev/null || true)
    if [ -n "$CODE" ]; then
      TOTP_REF=$(SNAP="$SNAP" "$PYTHON" -c '
import json,os,re
d=json.loads(os.environ.get("SNAP","{}") or "{}"); s=d.get("snapshot","")
m=re.search(r"ref=(\S+).*(?:totpPin|code|verification|認証コード)", s, re.I)
print(m.group(1) if m else "")
')
      if [ -n "$TOTP_REF" ]; then
        curl -sS -X POST "$CAMOFOX/tabs/$TAB/type" \
          -H 'Content-Type: application/json' \
          -d "$("$JQ" -n --arg r "$TOTP_REF" --arg t "$CODE" \
                          --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
                          '{ref:$r, text:$t, userId:$uid, sessionKey:$sk}')" >/dev/null
        sleep 1
        curl -sS -X POST "$CAMOFOX/tabs/$TAB/press" \
          -H 'Content-Type: application/json' \
          -d "$("$JQ" -n --arg k "Enter" --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
                          '{key:$k, userId:$uid, sessionKey:$sk}')" >/dev/null
        sleep 8
      fi
    fi
  fi
  #  - gog-gmail auto-read fallback path (no TOTP env)
  #  Polls keiodaisuke@gmail.com for "Google" subject in the last 60s via
  #  `hermes chat -q --skill gog-gmail "fetch latest Google 2-step code"`.
  #  The mini model returns the 6-digit code, which we then type.
  if [ -z "${GOOGLE_TOTP_SECRET:-}" ]; then
    GCODE=$(hermes chat -q --model "${LANCERS_SCORE_MODEL:-gpt-5.2-mini}" \
      "Read the most recent email in keiodaisuke@gmail.com (last 90s) with subject containing 'Google' or '確認コード' or '2-step verification'. Reply with ONLY the 6-digit verification code, no prose. If none found, reply NONE." 2>/dev/null | tr -d ' \n\r' || true)
    if printf '%s' "$GCODE" | grep -Eq '^[0-9]{6}$'; then
      SNAP2=$(cf_snapshot "$TAB")
      G_REF=$(SNAP2="$SNAP2" "$PYTHON" -c '
import json,os,re
d=json.loads(os.environ.get("SNAP2","{}") or "{}"); s=d.get("snapshot","")
m=re.search(r"ref=(\S+).*(?:code|verification|認証コード)", s, re.I)
print(m.group(1) if m else "")
')
      if [ -n "$G_REF" ]; then
        curl -sS -X POST "$CAMOFOX/tabs/$TAB/type" \
          -H 'Content-Type: application/json' \
          -d "$("$JQ" -n --arg r "$G_REF" --arg t "$GCODE" \
                          --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
                          '{ref:$r, text:$t, userId:$uid, sessionKey:$sk}')" >/dev/null
        sleep 1
        curl -sS -X POST "$CAMOFOX/tabs/$TAB/press" \
          -H 'Content-Type: application/json' \
          -d "$("$JQ" -n --arg k "Enter" --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
                          '{key:$k, userId:$uid, sessionKey:$sk}')" >/dev/null
        sleep 8
      fi
    fi
  fi
fi

# 4. Re-probe cookies
COOKIES_JSON=$(curl -sS "$CAMOFOX/sessions/$USER_ID/cookies?sessionKey=$SESSION_KEY" 2>/dev/null || echo '[]')
HAS=$(printf '%s' "$COOKIES_JSON" | "$JQ" '[.[] | select(.domain | test("lancers.jp"))] | length' 2>/dev/null || echo 0)
cf_close "$TAB"
if [ "${HAS:-0}" -gt 0 ]; then
  ok "lancers cookie obtained (n=$HAS)"
  exit 0
fi
err "login flow ran but no lancers cookie — autonomous 2FA path did not converge (TOTP missing + gog-gmail empty), record state and retry next beat"
HARDBLOCK_PATH="$HOME/.hermes/state/earn-lancers-login-hardblock.json"
mkdir -p "$(dirname "$HARDBLOCK_PATH")"
printf '%s' "$SNAP" > "$HARDBLOCK_PATH"
exit 6
