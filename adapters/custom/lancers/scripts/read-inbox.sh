#!/usr/bin/env bash
# adapters/custom/lancers/scripts/read-inbox.sh
# Open lancers inbox via camofox saved session, snapshot DOM, extract recent threads as JSON.
#
# Output (stdout, JSON):
#   { "fetched_at": "...", "thread_count": N, "threads": [ { "title", "url", "snippet", "unread" }, ... ] }
#
# Exit 0 = JSON written, 2 = camofox/session error, 3 = CAPTCHA.

set -uo pipefail

[ -f "$HOME/.openclaw/.env" ] && set -a && . "$HOME/.openclaw/.env" && set +a

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ADAPTER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
STATE_DIR="$ADAPTER_DIR/state"
mkdir -p "$STATE_DIR"

USER_ID="anicca"
SESSION_KEY="lancers"
CAMOFOX="http://127.0.0.1:9377"
INBOX_URL="https://www.lancers.jp/mypage/inbox"

if ! curl -sS "$CAMOFOX/health" | grep -q '"ok":true'; then
  echo '{"error":"camofox-not-alive"}' >&2
  exit 2
fi

TAB_ID=$(curl -sS -X POST "$CAMOFOX/tabs" \
  -H 'Content-Type: application/json' \
  -d "{\"url\":\"$INBOX_URL\",\"userId\":\"$USER_ID\",\"sessionKey\":\"$SESSION_KEY\"}" \
  | jq -r '.tabId // empty')

[ -z "$TAB_ID" ] && { echo '{"error":"tab-open-failed"}' >&2; exit 2; }
sleep 2

SNAP_RAW=$(curl -sS "$CAMOFOX/tabs/$TAB_ID/snapshot?userId=$USER_ID&sessionKey=$SESSION_KEY")
SNAP=$(echo "$SNAP_RAW" | jq -r '.snapshot // empty' 2>/dev/null)
[ -z "$SNAP" ] && SNAP="$SNAP_RAW"

if echo "$SNAP" | grep -qiE 'captcha|recaptcha|hcaptcha'; then
  echo '{"error":"captcha"}' >&2
  exit 3
fi

# Parse text-format snapshot. Camofox emits:
#   link "title text" [eN]:
#     - /url: /mypage/inbox/12345
# We pair adjacent lines, filter URLs matching the thread shape.
THREADS=$(echo "$SNAP" | awk '
  /^[[:space:]]*-?[[:space:]]*link[[:space:]]+"/ {
    match($0, /"[^"]*"/);
    title = substr($0, RSTART+1, RLENGTH-2);
    next_is_url = 1;
    next;
  }
  next_is_url && /\/url:/ {
    sub(/.*\/url:[[:space:]]*/, "");
    url = $0;
    if (url ~ /\/inbox\/[0-9]+|\/message\/|\/work\/detail\//) {
      gsub(/"/, "\\\"", title);
      gsub(/"/, "\\\"", url);
      printf("{\"title\":\"%s\",\"url\":\"%s\",\"snippet\":\"\",\"unread\":false}\n", title, url);
    }
    next_is_url = 0;
  }
' | jq -sc 'unique_by(.url) | .[0:10]' 2>/dev/null)

if [ -z "$THREADS" ] || [ "$THREADS" = "null" ]; then
  THREADS="[]"
fi

jq -nc \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --argjson threads "$THREADS" \
  '{fetched_at:$ts, thread_count:($threads|length), threads:$threads}' \
  | tee "$STATE_DIR/last-inbox.json"

chmod 600 "$STATE_DIR/last-inbox.json"
exit 0
