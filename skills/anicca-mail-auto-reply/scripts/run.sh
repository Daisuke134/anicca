#!/usr/bin/env bash
# run.sh — one cycle of inbox scan + reply
# Usage: run.sh [DRY_RUN=1]
set -euo pipefail

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

SKILL=~/.openclaw/skills/anicca-mail-auto-reply
mkdir -p "$SKILL/data/runs"
NOW=$(date +%Y-%m-%dT%H-%M-%S)
RUN="$SKILL/data/runs/$NOW"
mkdir -p "$RUN"

STATE="$SKILL/data/state.json"
SKIP="$SKILL/data/skip-patterns.json"
[ -f "$STATE" ] || echo '{"replied":[]}' > "$STATE"

ACCOUNT="${GMAIL_ACCOUNT:-{{profile.contact.personalEmail}}}"
WINDOW_HOURS="${WINDOW_HOURS:-48}"
MAX_REPLIES="${MAX_REPLIES:-5}"
DRY_RUN="${DRY_RUN:-0}"

echo "▶ scan inbox  account=$ACCOUNT  window=${WINDOW_HOURS}h"

# Step 1: list candidate threads from last N hours
RAW="$RUN/inbox.json"
/opt/homebrew/bin/gog -a "$ACCOUNT" gmail search \
  "in:inbox newer_than:${WINDOW_HOURS}h -from:me -label:CATEGORY_PROMOTIONS -label:CATEGORY_UPDATES" \
  --max 30 --json --results-only > "$RAW"

# Step 2: enrich each thread with from/subject/snippet + check we_replied
ENRICHED="$RUN/enriched.json"
"$SKILL/scripts/lib/enrich.py" "$RAW" "$ENRICHED" "$ACCOUNT" "$STATE"

# Step 3: triage
TRIAGED="$RUN/triaged.json"
"$SKILL/scripts/lib/triage.py" "$ENRICHED" "$SKIP" "$TRIAGED"

# Step 4: draft + send REPLY items
SENT_TS=()
SENT=0
SKIPPED=0
FAILED=0

PYBIN=python3
THREAD_COUNT=$($PYBIN -c "import json;d=json.load(open('$TRIAGED'));print(len(d))")
for i in $(seq 0 $((THREAD_COUNT-1))); do
  if [ "$SENT" -ge "$MAX_REPLIES" ]; then
    echo "  reached MAX_REPLIES=$MAX_REPLIES; stopping"
    break
  fi
  ROW=$($PYBIN -c "import json;d=json.load(open('$TRIAGED'));print(json.dumps(d[$i]))")
  VERDICT=$(echo "$ROW" | $PYBIN -c "import sys,json;print(json.load(sys.stdin).get('triage',''))")
  if [ "$VERDICT" != "REPLY" ]; then
    SKIPPED=$((SKIPPED+1))
    continue
  fi
  TID=$(echo "$ROW" | $PYBIN -c "import sys,json;print(json.load(sys.stdin).get('thread_id',''))")
  ALREADY=$($PYBIN -c "import json;d=json.load(open('$STATE'));print('yes' if '$TID' in d.get('replied',[]) else 'no')")
  if [ "$ALREADY" = "yes" ]; then
    echo "  $TID already replied — skip"
    SKIPPED=$((SKIPPED+1))
    continue
  fi

  DRAFT="$RUN/draft-$i.txt"
  echo "$ROW" | "$SKILL/scripts/lib/draft.py" > "$DRAFT"

  SUBJ=$(echo "$ROW" | $PYBIN -c "import sys,json;s=json.load(sys.stdin).get('subject','') or '';print(('Re: '+s) if not s.startswith('Re:') else s)")
  MID=$(echo "$ROW" | $PYBIN -c "import sys,json;print(json.load(sys.stdin).get('latest_message_id',''))")

  echo "  reply → $TID  subject=$(echo "$SUBJ" | head -c 60)"

  if [ "$DRY_RUN" = "1" ]; then
    echo "    [DRY_RUN] would send (draft saved at $DRAFT)"
    SENT=$((SENT+1))
    continue
  fi

  if /opt/homebrew/bin/gog -a "$ACCOUNT" gmail send \
       --reply-to-message-id "$MID" --reply-all \
       --subject "$SUBJ" --body-file "$DRAFT" --json > "$RUN/sent-$i.json"; then
    # record in state
    $PYBIN -c "
import json
d=json.load(open('$STATE'))
d.setdefault('replied',[]).append('$TID')
d['replied']=d['replied'][-1000:]
json.dump(d,open('$STATE','w'),ensure_ascii=False,indent=2)"
    SENT=$((SENT+1))
  else
    echo "    ❌ send failed"
    FAILED=$((FAILED+1))
  fi
  sleep 3
done

echo "✅ run: sent=$SENT skipped=$SKIPPED failed=$FAILED  raw=$RUN"

# Slack report
$PYBIN - "$SLACK_CHANNEL_ID" "$SLACK_BOT_TOKEN" "$SENT" "$SKIPPED" "$FAILED" "$RUN" "$DRY_RUN" <<'PY'
import sys, json, urllib.request
ch, tok, sent, skipped, failed, run, dry = sys.argv[1:8]
payload = {
  "channel": ch,
  "text": f"📬 anicca-mail-auto-reply: sent={sent} skipped={skipped} failed={failed}",
  "blocks":[
    {"type":"header","text":{"type":"plain_text","text":"📬 mail-auto-reply cycle"}},
    {"type":"section","fields":[
      {"type":"mrkdwn","text":f"*sent:*\n{sent}"},
      {"type":"mrkdwn","text":f"*skipped:*\n{skipped}"},
      {"type":"mrkdwn","text":f"*failed:*\n{failed}"},
      {"type":"mrkdwn","text":f"*dry_run:*\n{dry}"},
    ]},
    {"type":"context","elements":[{"type":"mrkdwn","text":f"raw `{run}`"}]},
  ],
}
req=urllib.request.Request("https://slack.com/api/chat.postMessage",
  data=json.dumps(payload).encode(),
  headers={"Authorization":f"Bearer {tok}","Content-Type":"application/json; charset=utf-8"},
  method="POST")
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        print(json.loads(r.read().decode()).get("ts","?"))
except Exception as e:
    print("slack err",e)
PY
