#!/usr/bin/env bash
# adapters/custom/lancers/scripts/apply.sh <gig_id> <proposal_file> [amount_jpy] [delivery_yyyy-mm-dd]
#
# Submit a proposal to a Lancers gig using the camofox session from login.sh.
# Live-verified 2026-06-04 against gig 5552409: navigates through
# /work/detail → /work/propose_start → /work/propose_confirm → /work/propose_finish.
#
# Args:
#   $1 gig_id        — numeric gig ID from /work/detail/<id>
#   $2 proposal_file — path to a UTF-8 text file with the proposal body (≤ 8000 chars)
#   $3 amount_jpy    — contract amount in yen (default: 5000; Lancers min varies by gig)
#   $4 delivery      — YYYY-MM-DD (default: 7 days from today via gdate)
#
# Exit:
#   0 = /work/propose_finish/<gig_id> reached AND proposal visible in /mypage/proposals
#   2 = camofox down / form validation failure / session not authenticated
#   3 = CAPTCHA hit
#   4 = AI-disclosure radio missing on the form (= form spec changed)

set -uo pipefail
[ -f "$HOME/.openclaw/.env" ] && set -a && . "$HOME/.openclaw/.env" && set +a

GIG_ID="${1:-}"
PROPOSAL_FILE="${2:-}"
AMOUNT="${3:-5000}"
DELIVERY="${4:-}"

if [ -z "$GIG_ID" ] || [ -z "$PROPOSAL_FILE" ] || [ ! -f "$PROPOSAL_FILE" ]; then
  echo "usage: apply.sh <gig_id> <proposal_file> [amount_jpy] [delivery_yyyy-mm-dd]" >&2
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
SESSION_KEY="lancers"
CAMOFOX="http://127.0.0.1:9377"

if ! curl -sS -m 10 "$CAMOFOX/health" | grep -q '"ok":true'; then
  echo "[lancers/apply] camofox not alive" >&2
  exit 2
fi

PROPOSAL_BODY=$(cat "$PROPOSAL_FILE")

# 1. Open /work/detail to confirm gig accessibility + session
TAB_ID=$(curl -sS -m 30 -X POST "$CAMOFOX/tabs" \
  -H 'Content-Type: application/json' \
  -d "{\"url\":\"https://www.lancers.jp/work/detail/$GIG_ID\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" \
  | jq -r '.tabId // empty')
[ -z "$TAB_ID" ] && { echo "[lancers/apply] tab open failed" >&2; exit 2; }
sleep 4

snap_pull() {
  local raw t url
  raw=$(curl -sS -m 30 "$CAMOFOX/tabs/$TAB_ID/snapshot?userId=$USER_ID&sessionKey=$SESSION_KEY" 2>/dev/null)
  url=$(echo "$raw" | jq -r '.url // empty' 2>/dev/null)
  t=$(echo "$raw" | jq -r '.snapshot // empty' 2>/dev/null)
  [ -z "$t" ] && t="$raw"
  printf "%s\n--URL--\n%s\n" "$t" "$url"
}
do_click() {
  curl -sS -m 60 -X POST "$CAMOFOX/tabs/$TAB_ID/click" \
    -H 'Content-Type: application/json' \
    -d "{\"ref\":\"$1\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" >/dev/null 2>&1 || true
}
do_type() {
  curl -sS -m 30 -X POST "$CAMOFOX/tabs/$TAB_ID/type" \
    -H 'Content-Type: application/json' \
    -d "$(jq -nc --arg ref "$1" --arg t "$2" --arg u "$USER_ID" --arg s "$SESSION_KEY" '{ref:$ref,text:$t,userId:$u,sessionKey:$s}')" >/dev/null 2>&1 || true
}

CHUNK=$(snap_pull)
SNAP=$(echo "$CHUNK" | awk '/^--URL--$/{exit} {print}')
URL=$(echo "$CHUNK" | awk '/^--URL--$/{flag=1; next} flag {print}')

if echo "$SNAP" | grep -qiE 'captcha|recaptcha|hcaptcha'; then
  echo "[lancers/apply] CAPTCHA — exit per HARD RULE #-1" >&2
  exit 3
fi
if echo "$URL" | grep -qE '/user/login'; then
  echo "[lancers/apply] redirected to /user/login — run login.sh first" >&2
  exit 2
fi

# 2. Click 提案する on detail page
PROPOSE_REF=$(echo "$SNAP" | grep -E 'link "提案する"|button "提案する"' | grep -oE 'e[0-9]+' | head -1)
[ -z "$PROPOSE_REF" ] && { echo "[lancers/apply] 提案する link not found on /work/detail/$GIG_ID" >&2; exit 2; }
do_click "$PROPOSE_REF"
sleep 4

CHUNK=$(snap_pull)
SNAP=$(echo "$CHUNK" | awk '/^--URL--$/{exit} {print}')
URL=$(echo "$CHUNK" | awk '/^--URL--$/{flag=1; next} flag {print}')

if ! echo "$URL" | grep -q "propose_start/$GIG_ID"; then
  echo "[lancers/apply] expected propose_start URL but got $URL" >&2
  exit 2
fi

# 3. Type proposal text into the first textbox of the form (= 提案文)
PROPOSAL_REF=$(echo "$SNAP" | awk '/heading "提案文 必須"/{found=1} found && /^[[:space:]]*- textbox \[e[0-9]+\]/{match($0,/e[0-9]+/); print substr($0,RSTART,RLENGTH); exit}')
[ -z "$PROPOSAL_REF" ] && PROPOSAL_REF=$(echo "$SNAP" | grep -E '^[[:space:]]*- textbox \[e[0-9]+\]' | grep -oE 'e[0-9]+' | head -1)
do_type "$PROPOSAL_REF" "$PROPOSAL_BODY"

# 4. Type delivery date into 完了予定日 textbox (refs may shift after typing)
sleep 2
CHUNK=$(snap_pull)
SNAP=$(echo "$CHUNK" | awk '/^--URL--$/{exit} {print}')
DATE_REF=$(echo "$SNAP" | awk '/group "完了予定日 必須":/{found=1; next} found && /textbox \[e[0-9]+\]/{match($0,/e[0-9]+/); print substr($0,RSTART,RLENGTH); exit}')
[ -n "$DATE_REF" ] && do_type "$DATE_REF" "$DELIVERY"

# 5. Set contract amount in 契約金額 spinbutton
sleep 2
CHUNK=$(snap_pull)
SNAP=$(echo "$CHUNK" | awk '/^--URL--$/{exit} {print}')
AMOUNT_REF=$(echo "$SNAP" | awk '/group "契約金額（税抜） 必須":/{found=1; next} found && /spinbutton \[e[0-9]+\]/{match($0,/e[0-9]+/); print substr($0,RSTART,RLENGTH); exit}')
[ -n "$AMOUNT_REF" ] && do_type "$AMOUNT_REF" "$AMOUNT"

# 6. Select 生成AI使用 radio (= e19-equivalent: "using AI, copyright-safe, can revise")
sleep 2
CHUNK=$(snap_pull)
SNAP=$(echo "$CHUNK" | awk '/^--URL--$/{exit} {print}')
AI_RADIO_REF=$(echo "$SNAP" | grep -E 'radio "生成AIを使用している / 使用するが' | grep -oE 'e[0-9]+' | head -1)
if [ -z "$AI_RADIO_REF" ]; then
  echo "[lancers/apply] AI-disclosure radio not found on form — spec drift, exit 4" >&2
  exit 4
fi
do_click "$AI_RADIO_REF"
sleep 2

# 7. Click 内容を確認する
CHUNK=$(snap_pull)
SNAP=$(echo "$CHUNK" | awk '/^--URL--$/{exit} {print}')
REVIEW_REF=$(echo "$SNAP" | grep -E 'button "内容を確認する"' | grep -oE 'e[0-9]+' | head -1)
[ -z "$REVIEW_REF" ] && { echo "[lancers/apply] 内容を確認する button not found" >&2; exit 2; }
do_click "$REVIEW_REF"
sleep 5

CHUNK=$(snap_pull)
SNAP=$(echo "$CHUNK" | awk '/^--URL--$/{exit} {print}')
URL=$(echo "$CHUNK" | awk '/^--URL--$/{flag=1; next} flag {print}')

if ! echo "$URL" | grep -q "propose_confirm/$GIG_ID"; then
  echo "[lancers/apply] expected propose_confirm URL but got $URL — likely a 必須 field validation error" >&2
  exit 2
fi

# 8. Final submit
FINAL_REF=$(echo "$SNAP" | grep -E 'button "利用規約に同意して提案する"' | grep -oE 'e[0-9]+' | head -1)
[ -z "$FINAL_REF" ] && { echo "[lancers/apply] final submit button not found" >&2; exit 2; }
do_click "$FINAL_REF"
sleep 6

CHUNK=$(snap_pull)
URL=$(echo "$CHUNK" | awk '/^--URL--$/{flag=1; next} flag {print}')
SNAP=$(echo "$CHUNK" | awk '/^--URL--$/{exit} {print}')

PROPOSAL_ID=""
if echo "$URL" | grep -q "propose_finish/$GIG_ID"; then
  PROPOSAL_ID=$(echo "$SNAP" | grep -oE '/work/proposal/[0-9]+' | head -1 | grep -oE '[0-9]+$')
  STATUS="submitted"
else
  STATUS="submit-unconfirmed"
fi

# 9. Take a screenshot of the finish page
curl -sS -m 30 "$CAMOFOX/tabs/$TAB_ID/screenshot?userId=$USER_ID&sessionKey=$SESSION_KEY" \
  -o "$PROPOSALS_DIR/${GIG_ID}-finish.png" 2>/dev/null || true

# 10. Independent verify: gig appears on /mypage/proposals
curl -sS -m 30 -X POST "$CAMOFOX/tabs" \
  -H 'Content-Type: application/json' \
  -d "{\"url\":\"https://www.lancers.jp/mypage/proposals\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" >/dev/null
sleep 4
VERIF=$(curl -sS -m 30 "$CAMOFOX/tabs/$TAB_ID/snapshot?userId=$USER_ID&sessionKey=$SESSION_KEY" 2>/dev/null \
  | jq -r '.snapshot // empty' 2>/dev/null)
if echo "$VERIF" | grep -q "/work/detail/$GIG_ID"; then
  VERIFY_STATUS="visible-on-mypage-proposals"
else
  VERIFY_STATUS="not-seen-on-mypage-proposals"
fi

jq -nc \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg gig "$GIG_ID" \
  --arg amount "$AMOUNT" \
  --arg delivery "$DELIVERY" \
  --arg proposal_id "$PROPOSAL_ID" \
  --arg status "$STATUS" \
  --arg verify "$VERIFY_STATUS" \
  '{ts:$ts, gig_id:$gig, amount_jpy:($amount|tonumber), delivery:$delivery, proposal_id:$proposal_id, status:$status, verify:$verify}' \
  >> "$LOG"

echo "[lancers/apply] gig=$GIG_ID status=$STATUS proposal_id=$PROPOSAL_ID verify=$VERIFY_STATUS"
[ "$STATUS" = "submitted" ] && [ "$VERIFY_STATUS" = "visible-on-mypage-proposals" ] && exit 0
exit 2
