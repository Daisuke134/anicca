#!/usr/bin/env bash
# evaluate-3.sh — TC-3 reply-with-imagination verifier
set -uo pipefail
YAML="$1"; TS="$2"
[ -f "$HOME/.openclaw/.env" ] && set -a && source "$HOME/.openclaw/.env" && set +a
QUERY="subject:\"TC-3-$TS\" newer_than:1h"
# Retry up to 3 times with 30s waits for Gmail search indexing delay
# Fix: use threadId OR id (gog search returns 'id' not 'threadId')
TID=""
for attempt in 1 2 3; do
  [ "$attempt" -gt 1 ] && { echo "    ⏳ retry $attempt/3: waiting 30s for Gmail indexing..."; sleep 30; }
  TID=$(/opt/homebrew/bin/gog gmail search "$QUERY" --account "$GOG_ACCOUNT" --max 1 --json --results-only 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); items=d if isinstance(d,list) else d.get('messages',[]); print(items[0].get('threadId') or items[0].get('id','') if items else '')")
  [ -n "$TID" ] && break
done
[ -z "$TID" ] && { echo "    ❌ thread not found after retries"; exit 1; }
# Fetch thread; expect ≥ 2 messages (original + reply)
THREAD=$(/opt/homebrew/bin/gog gmail thread get "$TID" --account "$GOG_ACCOUNT" --json 2>&1)
REPLY_BODY=$(echo "$THREAD" | python3 -c "
import sys, json, base64
d = json.load(sys.stdin)
msgs = d.get('thread', d).get('messages', d.get('messages', []))
if len(msgs) < 2: print(''); sys.exit(0)
last = msgs[-1]
def walk(p):
    if p.get('mimeType','').startswith('text/'):
        data = (p.get('body',{}) or {}).get('data','')
        if data: return base64.urlsafe_b64decode(data + '===').decode('utf-8','replace')
    out = ''
    for sub in (p.get('parts') or []): out += walk(sub)
    return out
print(walk(last.get('payload',{})))
")
[ -z "$REPLY_BODY" ] && { echo "    ❌ no reply message in thread"; exit 1; }
# Required substrings
for s in '成田 大祐' '新宿区南元町' 'anicca' '日本' '給与'; do
  echo "$REPLY_BODY" | grep -qF "$s" || { echo "    ❌ missing required '$s'"; exit 1; }
done
# Forbidden substrings
for s in '[記入]' '[fill in]' '[TBD]' 'on behalf of Daisuke' '+1 (336)' '+1 336'; do
  echo "$REPLY_BODY" | grep -qF "$s" && { echo "    ❌ forbidden '$s' present"; exit 1; }
done
# Signature
echo "$REPLY_BODY" | grep -qE 'Anicca$|Anicca[[:space:]]' || { echo "    ❌ signature 'Anicca' missing"; exit 1; }
echo "    ✓ reply body passes required + forbidden + signature checks"; exit 0
