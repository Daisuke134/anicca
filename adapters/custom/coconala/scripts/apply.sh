#!/usr/bin/env bash
# adapters/custom/coconala/scripts/apply.sh <request_id> <proposal_file> [amount_jpy] [delivery_yyyy-mm-dd]
#
# Submit a proposal to a Coconala request using the camofox session from login.sh.
#
# Live-verified 2026-06-04: Coconala blocks 応募 (apply-to-request) at the
# account-policy level when 本人確認 (identity verification) is `未登録`. Both
# the inline 応募する button and the direct `/requests/<id>/apply` URL silently
# refuse — the URL returns "ご指定のページが見つかりませんでした /
# ログイン中のアカウントではアクセスできない". This is parallel to how Lancers
# gates 出金 (withdrawal) on eKYC: Coconala gates 応募 itself.
#
# Therefore this script:
#   1. Probes the apply URL first.
#   2. If it 404s with the auth-block message, writes a deterministic
#      `{status:"id-verification-required"}` record + exits 5.
#   3. Otherwise (= 本人確認 done in a future round), proceeds to fill the
#      form (proposal text + amount + delivery + AI-disclosure if asked) and
#      submits, then verifies via /mypage/proposals.
#
# Exit:
#   0 = submitted + verified
#   2 = camofox down / session not authenticated / form drift
#   3 = CAPTCHA hit
#   5 = 本人確認 missing on account (= deterministic policy block,
#       follow-up = upload gov-ID + selfie via /mypage/user_identification,
#       which is a HARD RULE #-1 physical exception)

set -uo pipefail
[ -f "$HOME/.openclaw/.env" ] && set -a && . "$HOME/.openclaw/.env" && set +a

REQUEST_ID="${1:-}"
PROPOSAL_FILE="${2:-}"
AMOUNT="${3:-3000}"
DELIVERY="${4:-}"

if [ -z "$REQUEST_ID" ] || [ -z "$PROPOSAL_FILE" ] || [ ! -f "$PROPOSAL_FILE" ]; then
  echo "usage: apply.sh <request_id> <proposal_file> [amount_jpy] [delivery_yyyy-mm-dd]" >&2
  exit 2
fi

if [ -z "$DELIVERY" ]; then
  if command -v gdate >/dev/null 2>&1; then
    DELIVERY=$(gdate -u -d '+7 days' +%Y-%m-%d)
  else
    DELIVERY=$(date -u -v+7d +%Y-%m-%d 2>/dev/null || date -u +%Y-%m-%d)
  fi
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ADAPTER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
STATE_DIR="$ADAPTER_DIR/state"
PROPOSALS_DIR="$STATE_DIR/proposals"
mkdir -p "$PROPOSALS_DIR"
LOG="$STATE_DIR/apply-log.jsonl"
touch "$LOG"
chmod 600 "$LOG" 2>/dev/null || true

USER_ID="anicca"
SESSION_KEY="coconala"
CAMOFOX="http://127.0.0.1:9377"

if ! curl -sS -m 10 "$CAMOFOX/health" | grep -q '"ok":true'; then
  echo "[coconala/apply] camofox not alive" >&2
  exit 2
fi

PROPOSAL_BODY=$(cat "$PROPOSAL_FILE")

# Probe direct apply URL — Coconala 404s here with the auth-block message
# when the account doesn't have 本人確認.
TAB_ID=$(curl -sS -m 30 -X POST "$CAMOFOX/tabs" \
  -H 'Content-Type: application/json' \
  -d "{\"url\":\"https://coconala.com/requests/$REQUEST_ID/apply\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" \
  | jq -r '.tabId // empty')
[ -z "$TAB_ID" ] && { echo "[coconala/apply] tab open failed" >&2; exit 2; }
sleep 5

SNAP_RAW=$(curl -sS -m 30 "$CAMOFOX/tabs/$TAB_ID/snapshot?userId=$USER_ID&sessionKey=$SESSION_KEY")
URL=$(echo "$SNAP_RAW" | jq -r '.url // empty' 2>/dev/null)
SNAP=$(echo "$SNAP_RAW" | jq -r '.snapshot // empty' 2>/dev/null)
[ -z "$SNAP" ] && SNAP="$SNAP_RAW"

if echo "$SNAP" | grep -qiE 'captcha|recaptcha|hcaptcha|cloudflare challenge'; then
  echo "[coconala/apply] CAPTCHA — exit per HARD RULE #-1" >&2
  exit 3
fi

# 404 / not-found = account policy block
if echo "$SNAP" | grep -qE 'ご指定のページが見つかりませんでした|ログイン中のアカウントではアクセスできない'; then
  # Cross-check 本人確認 status on /mypage/user
  curl -sS -m 30 -X POST "$CAMOFOX/tabs" \
    -H 'Content-Type: application/json' \
    -d "{\"url\":\"https://coconala.com/mypage/user\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" >/dev/null
  sleep 4
  PROF=$(curl -sS -m 30 "$CAMOFOX/tabs/$TAB_ID/snapshot?userId=$USER_ID&sessionKey=$SESSION_KEY" \
    | jq -r '.snapshot // empty' 2>/dev/null)
  # 本人確認 appears on /mypage/user as: `link "本人確認"` followed (within ~3
  # lines) by either `text: 未登録` / `text: 登録済`. awk pairs them.
  VERIFIED=$(echo "$PROF" | awk '
    /link "本人確認"/ { in_block=1; lines=0; next }
    in_block && lines++ > 4 { in_block=0 }
    in_block && /text:[[:space:]]*(未登録|登録済|認証済|未認証)/ {
      sub(/.*text:[[:space:]]*/, ""); print; in_block=0; exit
    }
  ')
  [ -z "$VERIFIED" ] && VERIFIED="unknown"

  jq -nc \
    --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg req "$REQUEST_ID" \
    --arg status "id-verification-required" \
    --arg verified "$VERIFIED" \
    '{ts:$ts, request_id:$req, status:$status, identity_verification:$verified, hint:"upload gov-ID + selfie at /mypage/user_identification (HARD RULE #-1 physical exception)"}' \
    >> "$LOG"
  echo "[coconala/apply] blocked: 本人確認=$VERIFIED — see /mypage/user_identification"
  exit 5
fi

# Future path (when 本人確認 lands): form structure is unknown until the page
# can render. The block below is a best-effort placeholder that the next
# round will populate based on real field refs.
PROPOSAL_REF=$(echo "$SNAP" | grep -E 'textbox\s+"[^"]*提案' | grep -oE 'e[0-9]+' | head -1)
AMOUNT_REF=$(echo "$SNAP" | grep -E 'spinbutton\s+"[^"]*金額' | grep -oE 'e[0-9]+' | head -1)
DATE_REF=$(echo "$SNAP" | grep -E 'textbox\s+"[^"]*納期' | grep -oE 'e[0-9]+' | head -1)
SUBMIT_REF=$(echo "$SNAP" | grep -E 'button\s+"[^"]*(送信|応募|提案)' | grep -oE 'e[0-9]+' | head -1)

if [ -z "$PROPOSAL_REF" ] || [ -z "$SUBMIT_REF" ]; then
  jq -nc \
    --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg req "$REQUEST_ID" \
    --arg status "form-refs-unknown" \
    --arg url "$URL" \
    '{ts:$ts, request_id:$req, status:$status, url:$url, hint:"unblock 本人確認 first, then re-snapshot apply form to populate field refs"}' \
    >> "$LOG"
  echo "[coconala/apply] form refs unknown on $URL — round-2 task to map fields after 本人確認"
  exit 2
fi

# Stubbed for future round
curl -sS -m 30 -X POST "$CAMOFOX/tabs/$TAB_ID/type" \
  -H 'Content-Type: application/json' \
  -d "$(jq -nc --arg ref "$PROPOSAL_REF" --arg t "$PROPOSAL_BODY" '{ref:$ref,text:$t,userId:"anicca",sessionKey:"coconala"}')" >/dev/null
[ -n "$AMOUNT_REF" ] && curl -sS -m 30 -X POST "$CAMOFOX/tabs/$TAB_ID/type" \
  -H 'Content-Type: application/json' \
  -d "$(jq -nc --arg ref "$AMOUNT_REF" --arg t "$AMOUNT" '{ref:$ref,text:$t,userId:"anicca",sessionKey:"coconala"}')" >/dev/null
[ -n "$DATE_REF" ] && curl -sS -m 30 -X POST "$CAMOFOX/tabs/$TAB_ID/type" \
  -H 'Content-Type: application/json' \
  -d "$(jq -nc --arg ref "$DATE_REF" --arg t "$DELIVERY" '{ref:$ref,text:$t,userId:"anicca",sessionKey:"coconala"}')" >/dev/null
sleep 2
curl -sS -m 60 -X POST "$CAMOFOX/tabs/$TAB_ID/click" \
  -H 'Content-Type: application/json' \
  -d "{\"ref\":\"$SUBMIT_REF\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" >/dev/null 2>&1 || true
sleep 5

FINAL_URL=$(curl -sS -m 30 "$CAMOFOX/tabs/$TAB_ID/snapshot?userId=$USER_ID&sessionKey=$SESSION_KEY" 2>/dev/null \
  | jq -r '.url // empty')
if echo "$FINAL_URL" | grep -qE '/applied|/finish|/complete|/proposals'; then
  STATUS="submitted"
else
  STATUS="submit-unconfirmed"
fi

curl -sS -m 30 "$CAMOFOX/tabs/$TAB_ID/screenshot?userId=$USER_ID&sessionKey=$SESSION_KEY" \
  -o "$PROPOSALS_DIR/${REQUEST_ID}-finish.png" 2>/dev/null || true

jq -nc \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg req "$REQUEST_ID" \
  --arg amount "$AMOUNT" \
  --arg delivery "$DELIVERY" \
  --arg status "$STATUS" \
  --arg url "$FINAL_URL" \
  '{ts:$ts, request_id:$req, amount_jpy:($amount|tonumber), delivery:$delivery, status:$status, final_url:$url}' \
  >> "$LOG"
echo "[coconala/apply] request=$REQUEST_ID status=$STATUS"
[ "$STATUS" = "submitted" ] && exit 0 || exit 2
