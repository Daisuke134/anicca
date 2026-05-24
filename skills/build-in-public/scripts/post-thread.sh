#!/usr/bin/env bash
# post-thread.sh — deterministic: body file -> thread-split -> Postiz DRAFT thread.
# No fragile inline python. jq builds the payload from thread-split's JSON.
#
# Usage: post-thread.sh <body_file> [integration_id] [type]
#   integration_id default = X main cmm6d7m5703rwpr0yr5vtme3w
#   type default = draft  (Dais policy: X = Postiz draft, never "now")
# Prints: postId on success, or "ERR: ..." on failure.
set -euo pipefail
SKILL="$HOME/.openclaw/skills/build-in-public"
BODY_FILE="${1:?usage: post-thread.sh <body_file> [integration_id] [type]}"
INT_ID="${2:-cmm6d7m5703rwpr0yr5vtme3w}"
PTYPE="${3:-draft}"
[ -f "$HOME/.openclaw/.env" ] && { set -a; . "$HOME/.openclaw/.env"; set +a; }
[ -n "${POSTIZ_API_KEY:-}" ] || { echo "ERR: POSTIZ_API_KEY unset" >&2; exit 3; }
[ -s "$BODY_FILE" ] || { echo "ERR: empty body file $BODY_FILE" >&2; exit 4; }

# 1) body -> thread-split.py -> JSON array of tweet strings (valid JSON, \n escaped)
THREAD_JSON=$(python3 "$SKILL/scripts/thread-split.py" --file "$BODY_FILE")
echo "$THREAD_JSON" | jq -e 'type=="array" and length>=1' >/dev/null \
  || { echo "ERR: thread-split did not return a JSON array: $THREAD_JSON" >&2; exit 5; }

# 2) jq builds the full Postiz payload. Postiz REQUIRES `date` (ISO8601, even
#    for draft) and each value element MUST have image:[] (array, not absent).
NOW_ISO=$(date -u +%Y-%m-%dT%H:%M:%S.000Z)
PAYLOAD=$(jq -nc --arg int "$INT_ID" --arg t "$PTYPE" --arg d "$NOW_ISO" --argjson tw "$THREAD_JSON" \
  '{type:$t, date:$d, shortLink:false, tags:[],
    posts:[{ integration:{id:$int},
             value:[ $tw[] | {content:., image:[]} ],
             settings:{__type:"x", who_can_reply_post:"everyone"} }]}')

# 3) POST
RESP=$(curl -sS -X POST "https://api.postiz.com/public/v1/posts" \
  -H "Authorization: $POSTIZ_API_KEY" -H "Content-Type: application/json" -d "$PAYLOAD")
PID=$(echo "$RESP" | jq -r 'if type=="array" then .[0].postId else (.posts[0].postId // .posts[0].id) end // empty' 2>/dev/null)
if [ -z "$PID" ]; then echo "ERR: no postId. Postiz said: $RESP" >&2; exit 6; fi
echo "$PID"
