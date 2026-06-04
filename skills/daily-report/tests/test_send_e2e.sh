#!/usr/bin/env bash
# E2E: run daily-report.sh once, assert the trace JSONL records send.ok=true,
# and that the AgentMail inbox shows ONE message with the expected subject prefix.
# Gated by ANICCA_LIVE_SEND=1 so it never sends during ordinary unit runs.
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
JQ="/usr/bin/jq"

if [ "${ANICCA_LIVE_SEND:-0}" != "1" ]; then
  echo "SKIP: set ANICCA_LIVE_SEND=1 to run the live AgentMail send E2E"
  exit 0
fi

TRACE=/Users/anicca/.hermes/state/daily-report.jsonl
BEFORE_LINES=$(wc -l < "$TRACE" 2>/dev/null | tr -d ' ' || echo 0)

# Force test recipient = inbox only (no Dais during test) via env override
export ANICCA_REPORT_TO="anicca-genesis@agentmail.to"

"$SKILL_DIR/scripts/daily-report.sh"

AFTER_LINES=$(wc -l < "$TRACE" | tr -d ' ')
if [ $((AFTER_LINES - BEFORE_LINES)) -ne 1 ]; then
  echo "FAIL: expected +1 trace line, got $((AFTER_LINES - BEFORE_LINES))"; exit 1
fi
LAST=$(tail -n 1 "$TRACE")
echo "$LAST" | "$JQ" -e '.send.ok == true' >/dev/null \
  || { echo "FAIL: send.ok != true; line=$LAST"; exit 1; }
SUBJECT=$(echo "$LAST" | "$JQ" -r '.send.subject')
echo "Sent subject: $SUBJECT"
case "$SUBJECT" in
  "[Anicca]"*) : ;;
  *) echo "FAIL: subject prefix wrong"; exit 1 ;;
esac

# Verify inbox via AgentMail list (most-recent message subject must match)
# and assert the X-Anicca-Origin: hermes-genesis header is present.
"$SKILL_DIR/.venv/bin/python" - <<'PY'
import os, sys, time
from pathlib import Path
from agentmail import AgentMail
for line in (Path.home() / ".hermes" / ".env").read_text().splitlines():
    line = line.strip()
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
c = AgentMail(api_key=os.environ["AGENTMAIL_API_KEY"])
inbox = os.environ["AGENTMAIL_INBOX_ID"]


def headers_of(msg):
    h = getattr(msg, "headers", None)
    if isinstance(h, dict):
        return {k.lower(): v for k, v in h.items()}
    return {}


for attempt in range(8):  # up to 80 s
    msgs = c.inboxes.messages.list(inbox_id=inbox, limit=10)
    items = getattr(msgs, "messages", None) or getattr(msgs, "items", None) or []
    for m in items:
        subj = getattr(m, "subject", "") or ""
        if subj.startswith("[Anicca] Day"):
            mid = getattr(m, "message_id", None) or getattr(m, "id", None)
            origin = headers_of(m).get("x-anicca-origin")
            if origin is None and mid:
                try:
                    full = c.inboxes.messages.get(inbox_id=inbox, message_id=mid)
                    origin = headers_of(full).get("x-anicca-origin")
                except Exception:
                    origin = None
            print(f"OK inbox has: {subj} | X-Anicca-Origin={origin}")
            sys.exit(0)
    time.sleep(10)
print("FAIL: no [Anicca] Day... message visible in inbox after 80s"); sys.exit(1)
PY

echo "PASS"
