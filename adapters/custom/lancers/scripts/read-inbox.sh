#!/usr/bin/env bash
# adapters/custom/lancers/scripts/read-inbox.sh
# Open Lancers /mypage/message (= the canonical inbox URL — `/mypage/inbox`
# does NOT exist on the live site, verified 2026-06-03), snapshot the board
# list, emit JSON of recent threads.
#
# A Lancers message thread lives at `/mypage/message?boardId=<N>`. The board
# list in the left panel renders each thread as:
#   - paragraph: anicca_ai_jpさんとのメッセージ <thread title>
#   - paragraph: <counterparty name>
#   - button [eN]   <- click opens that boardId
#
# We pair adjacent paragraph rows and emit one record per thread.
#
# Output:
#   { "fetched_at": "...", "thread_count": N, "threads":
#     [ { "title", "counterparty", "url", "snippet", "unread" }, ... ] }
#
# NOTE: boardId values are NOT in the static snapshot (= they hydrate after a
# button click). Until a click happens we emit url = "" — callers should treat
# the entry as a thread-list row and click via camofox/refs to descend.

set -uo pipefail
[ -f "$HOME/.openclaw/.env" ] && set -a && . "$HOME/.openclaw/.env" && set +a

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ADAPTER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
STATE_DIR="$ADAPTER_DIR/state"
mkdir -p "$STATE_DIR"

USER_ID="anicca"
SESSION_KEY="lancers"
CAMOFOX="http://127.0.0.1:9377"
INBOX_URL="https://www.lancers.jp/mypage/message"

if ! curl -sS -m 10 "$CAMOFOX/health" | grep -q '"ok":true'; then
  echo '{"error":"camofox-not-alive"}' >&2
  exit 2
fi

TAB_ID=$(curl -sS -m 30 -X POST "$CAMOFOX/tabs" \
  -H 'Content-Type: application/json' \
  -d "{\"url\":\"$INBOX_URL\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" \
  | jq -r '.tabId // empty')
[ -z "$TAB_ID" ] && { echo '{"error":"tab-open-failed"}' >&2; exit 2; }
sleep 6

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

# Auth check by URL: redirected to /user/login = not authenticated.
if echo "$URL" | grep -qE '/user/login|/user/verify_code'; then
  jq -nc --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{fetched_at:$ts, thread_count:0, threads:[], auth:"not-authenticated", hint:"run login.sh first"}' \
    | tee "$STATE_DIR/last-inbox.json"
  chmod 600 "$STATE_DIR/last-inbox.json"
  exit 0
fi

if echo "$SNAP" | grep -qiE 'captcha|recaptcha|hcaptcha'; then
  echo '{"error":"captcha"}' >&2
  exit 3
fi

# Close any blocking dialog (Lancers shows a video-call promo modal on first
# visit) so the inbox board list is exposed in the snapshot.
DIALOG_CLOSE_REF=$(echo "$SNAP" | awk '/^- dialog:/{in_d=1} in_d && /button "閉じる"/{ if (match($0,/\[e[0-9]+\]/)) { print substr($0,RSTART+1,RLENGTH-2); exit } } /^[^ ]/ && !/dialog/{in_d=0}')
if [ -n "$DIALOG_CLOSE_REF" ]; then
  curl -sS -m 30 -X POST "$CAMOFOX/tabs/$TAB_ID/click" \
    -H 'Content-Type: application/json' \
    -d "{\"ref\":\"$DIALOG_CLOSE_REF\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" >/dev/null 2>&1 || true
  sleep 2
  CHUNK=$(snap_pull)
  SNAP=$(echo "$CHUNK" | awk '/^--URL--$/{exit} {print}')
fi

# Parse board list. Each thread is two consecutive paragraph rows where the
# first contains "anicca_ai_jpさんとのメッセージ ".
THREADS=$(echo "$SNAP" | awk '
  /paragraph: anicca_ai_jpさんとのメッセージ / {
    sub(/.*anicca_ai_jpさんとのメッセージ /, "");
    title = $0;
    gsub(/"/, "\\\"", title);
    have_title = 1;
    next;
  }
  have_title && /paragraph: / {
    sub(/.*paragraph: */, "");
    counter = $0;
    gsub(/"/, "\\\"", counter);
    printf("{\"title\":\"%s\",\"counterparty\":\"%s\",\"url\":\"\",\"snippet\":\"\",\"unread\":false}\n", title, counter);
    have_title = 0;
  }
' | jq -sc '.[0:10]' 2>/dev/null)

[ -z "$THREADS" ] || [ "$THREADS" = "null" ] && THREADS="[]"

jq -nc \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --argjson threads "$THREADS" \
  '{fetched_at:$ts, thread_count:($threads|length), threads:$threads, auth:"authenticated"}' \
  | tee "$STATE_DIR/last-inbox.json"

chmod 600 "$STATE_DIR/last-inbox.json"
exit 0
