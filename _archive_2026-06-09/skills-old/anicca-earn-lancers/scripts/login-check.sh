#!/usr/bin/env bash
# login-check.sh — ensure the camofox session is logged into Lancers.
#
# Lancers reality (live-verified 2026-06-03 by adapter-smith, re-verified
# 2026-06-05): the Google-OAuth path is DEAD — the account is registered under
# the LANCERS_EMAIL (+anicca) alias + a raw password and is NOT linked to the
# bare Google account ("この Google で会員登録されていません"). So the only
# working path is the email/pw form + email 2FA. We mirror the proven adapter
# flow verbatim (adapters/custom/lancers/scripts/login.sh, gig 5552409).
#
# Login signal is taken from /mypage (NOT the cookie endpoint, which returns an
# HTML error page on this camofox build): url contains /mypage AND the snapshot
# shows the lancer nav (ランサーメニュー / 発注者に切り替え).
#
# 2FA: the 6-digit code is auto-fetched from Gmail via `gog` (the +anicca alias
# forwards login codes to redacted@example.invalid). No human in the loop.
#
# HARD-BLOCK (only): a real CAPTCHA element (recaptcha/hcaptcha/turnstile/
# cloudflare challenge) renders. Record the verbatim snapshot subset at
# ~/.hermes/state/earn-lancers-login-hardblock.json and exit non-0. The earn
# task stays OPEN (do NOT close it).
#
# Exit:
#   0 = logged in (session live)
#   3 = camofox down
#   4 = login could not complete (no creds / refs / 2FA) — hardblock json written
#   9 = real CAPTCHA element rendered — hardblock json written

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"

HARDBLOCK_PATH="${HERMES_STATE_DIR:-$HOME/.hermes/state}/earn-lancers-login-hardblock.json"

save_hardblock() {
  mkdir -p "$(dirname "$HARDBLOCK_PATH")"
  printf '%s' "$1" | head -c 4000 > "$HARDBLOCK_PATH"
}

# logged_in <snapshot-text> <url> → 0 if the lancer nav is present on /mypage
logged_in() {
  case "$2" in *"/mypage"*) ;; *) return 1 ;; esac
  printf '%s' "$1" | grep -qE 'ランサーメニュー|発注者に切り替え'
}

# ref_for <snapshot-text> <role> <label> → first e<digits> ref on the matching line
ref_for() {
  printf '%s' "$1" | grep -E "$2 \"$3\"" | grep -oE 'e[0-9]+' | head -1
}

cf_health || { err "camofox down"; exit 3; }

# ── 1. Probe existing session via /mypage ──────────────────────────────────
TAB=$(cf_open "https://www.lancers.jp/mypage")
[ -z "$TAB" ] && { err "tab open failed"; exit 3; }
sleep 5
SNAP=$(cf_snapshot_text "$TAB")
URL=$(cf_url "$TAB")

if logged_in "$SNAP" "$URL"; then
  ok "lancers session live (/mypage reused)"
  cf_close "$TAB"
  exit 0
fi

# CAPTCHA guard on the probe snapshot
if printf '%s' "$SNAP" | grep -qiE 'recaptcha|hcaptcha|turnstile|cloudflare challenge'; then
  save_hardblock "$SNAP"
  err "real CAPTCHA element rendered on probe — snapshot saved to $HARDBLOCK_PATH (task stays OPEN)"
  cf_close "$TAB"
  exit 9
fi

log "no live session — running email/pw login (Google path is dead on Lancers)"

# ── 2. Email/pw form fallback ──────────────────────────────────────────────
if [ -z "${LANCERS_EMAIL:-}" ] || [ -z "${LANCERS_PASSWORD:-}" ]; then
  save_hardblock "$SNAP"
  err "LANCERS_EMAIL / LANCERS_PASSWORD missing in env — cannot log in"
  cf_close "$TAB"
  exit 4
fi

cf_navigate "$TAB" "https://www.lancers.jp/user/login"
sleep 4
SNAP=$(cf_snapshot_text "$TAB")

EMAIL_REF=$(ref_for "$SNAP" textbox "メールアドレス")
PW_REF=$(ref_for "$SNAP" textbox "パスワード")
LOGIN_REF=$(ref_for "$SNAP" button "ログイン")

if [ -z "$EMAIL_REF" ] || [ -z "$PW_REF" ] || [ -z "$LOGIN_REF" ]; then
  save_hardblock "$SNAP"
  err "login form refs not found (refs missing) — snapshot saved to $HARDBLOCK_PATH"
  cf_close "$TAB"
  exit 4
fi

curl -sS -m 30 -X POST "$CAMOFOX/tabs/$TAB/type" \
  -H 'Content-Type: application/json' \
  -d "$("$JQ" -n --arg r "$EMAIL_REF" --arg t "$LANCERS_EMAIL" \
                  --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
                  '{ref:$r, text:$t, userId:$uid, sessionKey:$sk}')" >/dev/null
curl -sS -m 30 -X POST "$CAMOFOX/tabs/$TAB/type" \
  -H 'Content-Type: application/json' \
  -d "$("$JQ" -n --arg r "$PW_REF" --arg t "$LANCERS_PASSWORD" \
                  --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
                  '{ref:$r, text:$t, userId:$uid, sessionKey:$sk}')" >/dev/null

# Submit; click endpoint can stall on navigation — fire-and-forget
curl -sS -m 60 -X POST "$CAMOFOX/tabs/$TAB/click" \
  -H 'Content-Type: application/json' \
  -d "$("$JQ" -n --arg r "$LOGIN_REF" --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
                  '{ref:$r, userId:$uid, sessionKey:$sk}')" >/dev/null 2>&1 || true
sleep 5

# ── 3. Email 2FA (autonomous via gog) ──────────────────────────────────────
URL=$(cf_url "$TAB")
case "$URL" in
  *verify_code*)
    CODE=""
    if command -v gog >/dev/null 2>&1; then
      for _ in 1 2 3 4; do
        CODE=$(gog gmail search 'from:lancers.co.jp subject:ログイン認証コード newer_than:1h' \
                 --limit 1 --json 2>/dev/null \
               | "$JQ" -r '.[0].snippet // empty' 2>/dev/null \
               | grep -oE '[0-9]{6}' | head -1)
        [ -n "$CODE" ] && break
        sleep 8
      done
    fi
    if [ -z "$CODE" ]; then
      SNAP=$(cf_snapshot_text "$TAB")
      save_hardblock "$SNAP"
      err "verify_code page reached but no 2FA code from Gmail — snapshot saved to $HARDBLOCK_PATH"
      cf_close "$TAB"
      exit 4
    fi
    SNAP=$(cf_snapshot_text "$TAB")
    CODE_REF=$(ref_for "$SNAP" textbox "認証コード")
    VERIFY_REF=$(ref_for "$SNAP" button "認証する")
    if [ -n "$CODE_REF" ] && [ -n "$VERIFY_REF" ]; then
      curl -sS -m 30 -X POST "$CAMOFOX/tabs/$TAB/type" \
        -H 'Content-Type: application/json' \
        -d "$("$JQ" -n --arg r "$CODE_REF" --arg t "$CODE" \
                        --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
                        '{ref:$r, text:$t, userId:$uid, sessionKey:$sk}')" >/dev/null
      curl -sS -m 60 -X POST "$CAMOFOX/tabs/$TAB/click" \
        -H 'Content-Type: application/json' \
        -d "$("$JQ" -n --arg r "$VERIFY_REF" --arg uid "$USER_ID" --arg sk "$SESSION_KEY" \
                        '{ref:$r, userId:$uid, sessionKey:$sk}')" >/dev/null 2>&1 || true
      sleep 5
    fi
    ;;
esac

# ── 4. Confirm by re-probing /mypage ───────────────────────────────────────
cf_navigate "$TAB" "https://www.lancers.jp/mypage"
sleep 4
SNAP=$(cf_snapshot_text "$TAB")
URL=$(cf_url "$TAB")
cf_close "$TAB"

if logged_in "$SNAP" "$URL"; then
  ok "lancers session obtained (email/pw login)"
  exit 0
fi

save_hardblock "$SNAP"
err "login flow ran but /mypage not confirmed — snapshot saved to $HARDBLOCK_PATH (task stays OPEN, retry next beat)"
exit 4
