#!/usr/bin/env bash
# MODE=reply_watch — poll Gmail for staffer replies.
set -euo pipefail
SKILL="${SKILL:-$(cd "$(dirname "$0")/.." && pwd)}"
MODE=reply_watch
source "$SKILL/scripts/lib/slack_format.sh"

DRY="${POLITICIAN_DRY_RUN:-true}"
LOB="${LOBBYIST_HIRED:-false}"

# reply_watch is ALWAYS-LIVE read-only — no env gate beyond cron-runner Gmail
# auth. The bash script cannot call MCP tools directly, so it writes a queue
# file the cron runner picks up and resolves via mcp__gmail__search_threads
# / mcp__gmail__get_thread, then writes the result back.

QUEUE_DIR="$HOME/.openclaw/state/politician/reply_watch"
mkdir -p "$QUEUE_DIR"
TS_NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
REQ_FILE="$QUEUE_DIR/${TS_NOW}.req.json"
RESP_FILE="$QUEUE_DIR/${TS_NOW}.resp.json"
GMAIL_QUERY="from:(*.house.gov OR *.senate.gov OR *.mail.house.gov) newer_than:1d is:unread -in:sent"

cat > "$REQ_FILE" <<JSON
{
  "kind": "gmail_search_threads",
  "query": "${GMAIL_QUERY}",
  "label_ids": ["INBOX"],
  "max": 50,
  "callback": "${RESP_FILE}",
  "post_process": {
    "classify_sentiment": true,
    "update_crm": true,
    "crm_db": "${CRM_DB:-$SKILL/data/crm.sqlite}"
  }
}
JSON

# If a previous response is already on disk (cron runner resolved a prior
# request), aggregate counts now.
NEW=0; POS=0; NEU=0; NEG=0
if compgen -G "$QUEUE_DIR/*.resp.json" >/dev/null; then
  AGG=$(python3 - "$QUEUE_DIR" <<'PY'
import json, glob, sys, os, time
cutoff = time.time() - 24*3600
new = pos = neu = neg = 0
for p in glob.glob(os.path.join(sys.argv[1],"*.resp.json")):
    if os.path.getmtime(p) < cutoff: continue
    try: d = json.load(open(p))
    except Exception: continue
    for t in d.get("threads",[]):
        new += 1
        s = (t.get("sentiment") or "neutral").lower()
        if s == "positive": pos += 1
        elif s == "negative" or s == "hostile": neg += 1
        else: neu += 1
print(f"{new}|{pos}|{neu}|{neg}")
PY
  )
  IFS='|' read -r NEW POS NEU NEG <<< "$AGG"
fi

slack_post "📥 Staffer reply poll" \
  "new_replies=$NEW positive=$POS neutral=$NEU negative=$NEG queue=\"$REQ_FILE\""
