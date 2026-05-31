#!/usr/bin/env bash
# evaluate-1.sh — TC-1 silent-archive verifier
set -uo pipefail
YAML="$1"; TS="$2"
[ -f "$HOME/.openclaw/.env" ] && set -a && source "$HOME/.openclaw/.env" && set +a
QUERY=$(python3 -c "import yaml; d=yaml.safe_load(open('$YAML')); print([v['thread_query'] for v in d['verify'] if v['type']=='gmail_label'][0].replace('{ts}','$TS'))")
# Retry up to 3 times with 30s waits for Gmail search indexing delay
# Fix: use threadId OR id (gog search returns 'id' not 'threadId')
TID=""
for attempt in 1 2 3; do
  [ "$attempt" -gt 1 ] && { echo "    ⏳ retry $attempt/3: waiting 30s for Gmail indexing..."; sleep 30; }
  TID=$(/opt/homebrew/bin/gog gmail search "$QUERY" --account "$GOG_ACCOUNT" --max 1 --json --results-only 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); items=d if isinstance(d,list) else d.get('messages',[]); print(items[0].get('threadId') or items[0].get('id','') if items else '')")
  [ -n "$TID" ] && break
done
[ -z "$TID" ] && { echo "    ❌ thread not found after retries for $QUERY"; exit 1; }
LABELS=$(/opt/homebrew/bin/gog gmail thread get "$TID" --account "$GOG_ACCOUNT" --json 2>&1 | python3 -c "import json,sys; d=json.load(sys.stdin); msgs=d.get('thread',d).get('messages',d.get('messages',[])); print(','.join(sorted({l for m in msgs for l in m.get('labelIds',[])})))")
echo "$LABELS" | grep -qw "INBOX" && { echo "    ❌ INBOX still present · labels=$LABELS"; exit 1; }
echo "    ✓ INBOX absent · labels=$LABELS"; exit 0
