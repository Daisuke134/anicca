#!/usr/bin/env bash
# phase1-call-from-list.sh — Call every entry in a JSON list and log result
# Usage: phase1-call-from-list.sh <list.json> <subject>
# JSON shape:
#   [
#     {"name":"慈恵院 信濃町別院","phone":"+81xxxxxxxxxx","context":"AIお墓建立の相談…","first_message":"…"},
#     ...
#   ]
set -euo pipefail

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
SKILL=~/.openclaw/skills/anicca-outbound-recruit
source "$SKILL/scripts/lib/outbound-realtime.sh"

LIST="${1:?list.json required}"
SUBJECT="${2:?subject required}"
[ -f "$LIST" ] || { echo "❌ list not found: $LIST"; exit 1; }

NOW=$(date +%Y-%m-%dT%H-%M-%S)
RUN_DIR="$SKILL/data/runs/$NOW"
mkdir -p "$RUN_DIR"

COUNT=$(python3 -c "import sys,json;print(len(json.load(open(sys.argv[1]))))" "$LIST")
echo "▶ phase1-call-from-list  $NOW  count=$COUNT  subject=$SUBJECT"

OK=0; FAIL=0
for i in $(seq 0 $((COUNT-1))); do
  ENTRY=$(python3 -c "import sys,json;print(json.dumps(json.load(open(sys.argv[1]))[int(sys.argv[2])]))" "$LIST" "$i")
  NAME=$(echo "$ENTRY" | python3 -c "import sys,json;print(json.load(sys.stdin).get('name','?'))")
  TO=$(echo "$ENTRY" | python3 -c "import sys,json;print(json.load(sys.stdin).get('phone',''))")
  CTX=$(echo "$ENTRY" | python3 -c "import sys,json;print(json.load(sys.stdin).get('context',''))")
  FIRST=$(echo "$ENTRY" | python3 -c "import sys,json;print(json.load(sys.stdin).get('first_message',''))")

  if [ -z "$TO" ]; then
    echo "  [$i/$COUNT] $NAME — no phone, skip"
    continue
  fi

  echo "  [$i/$COUNT] calling $NAME ($TO)"
  RESP=$(outbound_call "$TO" "$CTX" "${FIRST:-Hello, this is Anicca calling on behalf of Anicca AI.}")
  echo "$RESP" > "$RUN_DIR/call-$i-init.json"
  CONV=$(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('conversation_id',''))")
  if [ -z "$CONV" ]; then
    echo "    ❌ outbound failed:"
    echo "    $RESP"
    FAIL=$((FAIL+1))
    continue
  fi
  echo "    conv=$CONV  polling…"
  CONV_JSON=$(poll_conversation "$CONV" 360)
  echo "$CONV_JSON" > "$RUN_DIR/call-$i-conv.json"
  slack_report_call "$TO" "$CONV_JSON" "$SUBJECT — $NAME" >/dev/null || true
  OK=$((OK+1))
  sleep 2
done

# summary
python3 - "$SLACK_CHANNEL_ID" "$SLACK_BOT_TOKEN" "$SUBJECT" "$COUNT" "$OK" "$FAIL" "$RUN_DIR" <<'PY'
import sys, json, urllib.request
ch, token, subject, total, ok, fail, run_dir = sys.argv[1:8]
payload = {
  "channel": ch,
  "text": f"📞 {subject} — done ({ok}/{total} ok, {fail} fail)",
  "blocks":[
    {"type":"header","text":{"type":"plain_text","text":f"📞 {subject} — batch done"}},
    {"type":"section","fields":[
      {"type":"mrkdwn","text":f"*total:*\n{total}"},
      {"type":"mrkdwn","text":f"*ok:*\n{ok}"},
      {"type":"mrkdwn","text":f"*fail:*\n{fail}"},
    ]},
    {"type":"context","elements":[{"type":"mrkdwn","text":f"raw: `{run_dir}`"}]},
  ],
}
req=urllib.request.Request("https://slack.com/api/chat.postMessage",
    data=json.dumps(payload).encode(),
    headers={"Authorization":f"Bearer {token}","Content-Type":"application/json; charset=utf-8"},
    method="POST")
try:
    with urllib.request.urlopen(req,timeout=15) as r:
        print(json.loads(r.read().decode()).get("ts","?"))
except Exception as e:
    print("?",e)
PY

echo "✅ phase1: total=$COUNT ok=$OK fail=$FAIL  raw=$RUN_DIR"
