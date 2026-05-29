#!/usr/bin/env bash
# evaluate-4.sh — TC-4 reply+action verifier
set -uo pipefail
YAML="$1"; TS="$2"
[ -f "$HOME/.openclaw/.env" ] && set -a && source "$HOME/.openclaw/.env" && set +a
# 1) reply present
QUERY="subject:\"TC-4-$TS\" newer_than:1h"
# Retry up to 3 times with 30s waits for Gmail search indexing delay
# Fix: use threadId OR id (gog search returns 'id' not 'threadId')
TID=""
for attempt in 1 2 3; do
  [ "$attempt" -gt 1 ] && { echo "    ⏳ retry $attempt/3: waiting 30s for Gmail indexing..."; sleep 30; }
  TID=$(/opt/homebrew/bin/gog gmail search "$QUERY" --account "$GOG_ACCOUNT" --max 1 --json --results-only 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); items=d if isinstance(d,list) else d.get('messages',[]); print(items[0].get('threadId') or items[0].get('id','') if items else '')")
  [ -n "$TID" ] && break
done
[ -z "$TID" ] && { echo "    ❌ thread not found after retries"; exit 1; }
THREAD=$(/opt/homebrew/bin/gog gmail thread get "$TID" --account "$GOG_ACCOUNT" --json 2>&1)
MSG_COUNT=$(echo "$THREAD" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('thread',d).get('messages',d.get('messages',[]))))")
[ "$MSG_COUNT" -lt 2 ] && { echo "    ❌ no reply in thread"; exit 1; }
echo "    ✓ reply present"
# 2) tasks.json must contain follow-up
FOLLOW=$(python3 -c "import json; d=json.load(open('$HOME/.openclaw/workspace/tasks.json')); print(sum(1 for t in d['master']['tasks'] if 'shonan-bishu' in t.get('id','').lower() or 'booking' in t.get('id','').lower()))")
[ "$FOLLOW" -ge 1 ] || { echo "    ❌ no follow-up task registered"; exit 1; }
echo "    ✓ follow-up task registered"
# 3) skill state/ must contain a screenshot or booking-confirmation artifact
SKILL_STATE_DIR="$HOME/.openclaw/skills/shonan-bishu-book/state"
if [ -d "$SKILL_STATE_DIR" ]; then
  ART=$(ls "$SKILL_STATE_DIR"/*.png "$SKILL_STATE_DIR"/booking-*.json 2>/dev/null | head -1)
  [ -n "$ART" ] || { echo "    ❌ no artifact in shonan-bishu-book/state/"; exit 1; }
  echo "    ✓ artifact: $ART"
else
  echo "    ❌ shonan-bishu-book skill not created (Anicca should auto-create)"
  exit 1
fi
exit 0
