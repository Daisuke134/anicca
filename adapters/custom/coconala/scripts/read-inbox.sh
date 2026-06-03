#!/usr/bin/env bash
# adapters/custom/coconala/scripts/read-inbox.sh
# Open Coconala inbox at /message (= canonical URL, verified 2026-06-03 live).
# Each thread is a `link "<counter> <date> <snippet>" [eN]` row with
# `/url: /mypage/direct_message/<id>`. Emit JSON list of recent threads.

set -uo pipefail
[ -f "$HOME/.openclaw/.env" ] && set -a && . "$HOME/.openclaw/.env" && set +a

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ADAPTER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
STATE_DIR="$ADAPTER_DIR/state"
mkdir -p "$STATE_DIR"

USER_ID="anicca"
SESSION_KEY="coconala"
CAMOFOX="http://127.0.0.1:9377"
INBOX_URL="https://coconala.com/message"

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

SNAP_RAW=$(curl -sS -m 30 "$CAMOFOX/tabs/$TAB_ID/snapshot?userId=$USER_ID&sessionKey=$SESSION_KEY")
URL=$(echo "$SNAP_RAW" | jq -r '.url // empty' 2>/dev/null)
SNAP=$(echo "$SNAP_RAW" | jq -r '.snapshot // empty' 2>/dev/null)
[ -z "$SNAP" ] && SNAP="$SNAP_RAW"

# Auth gate: bounce to /login = unauthenticated.
if echo "$URL" | grep -qE '/login'; then
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

# Pair adjacent rows:
#   - link "<title bag>" [eN]:
#     - /url: /mypage/direct_message/<id>
# Emit a record per match.
THREADS=$(echo "$SNAP" | awk '
  /^[[:space:]]*- link "/ {
    match($0, /"[^"]*"/);
    title = substr($0, RSTART+1, RLENGTH-2);
    next_is_url = 1;
    next;
  }
  next_is_url && /\/url:[[:space:]]*\/mypage\/direct_message\// {
    sub(/.*\/url:[[:space:]]*/, "");
    url = $0;
    gsub(/"/, "\\\"", title);
    gsub(/"/, "\\\"", url);
    printf("{\"title\":\"%s\",\"url\":\"%s\",\"snippet\":\"\",\"unread\":false}\n", title, url);
    next_is_url = 0;
  }
  /^[[:space:]]*- / && !/^[[:space:]]*-[[:space:]]*\/url:/ { next_is_url = 0 }
' | jq -sc 'unique_by(.url) | .[0:10]' 2>/dev/null)

[ -z "$THREADS" ] || [ "$THREADS" = "null" ] && THREADS="[]"

jq -nc \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --argjson threads "$THREADS" \
  '{fetched_at:$ts, thread_count:($threads|length), threads:$threads, auth:"authenticated"}' \
  | tee "$STATE_DIR/last-inbox.json"

chmod 600 "$STATE_DIR/last-inbox.json"
exit 0
