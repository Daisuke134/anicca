#!/usr/bin/env bash
# evaluate-5.sh — TC-5 ask-for-help verifier
set -uo pipefail
YAML="$1"; TS="$2"
[ -f "$HOME/.openclaw/.env" ] && set -a && source "$HOME/.openclaw/.env" && set +a
# 1) codex invocation evidence: log MUST contain TC-5-$TS context
LOG="$HOME/.openclaw/skills/_shared/claude-codex/state/invocations.jsonl"
if [ -f "$LOG" ]; then
  grep -F "TC-5-$TS" "$LOG" >/dev/null 2>&1 || { echo "    ❌ no codex invocation referencing TC-5-$TS"; exit 1; }
else
  echo "    ❌ codex invocation log missing (Plan-T16 must create it)"; exit 1
fi
echo "    ✓ codex invoked"
# 2) learnings entry
grep -F "TC-5-$TS" "$HOME/.openclaw/.learnings/LEARNINGS.md" >/dev/null 2>&1 || grep -F "uber.license" "$HOME/.openclaw/.learnings/LEARNINGS.md" >/dev/null 2>&1 || { echo "    ❌ no LEARNINGS entry for TC-5"; exit 1; }
echo "    ✓ LEARNINGS entry present"
# 3) reply present (Round 3 outcome)
QUERY="subject:\"TC-5-$TS\" newer_than:1h"
TID=$(/opt/homebrew/bin/gog gmail search "$QUERY" --account "$GOG_ACCOUNT" --max 1 --json --results-only 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); items=d if isinstance(d,list) else d.get('messages',[]); print((items[0].get('threadId') or items[0].get('id','')) if items else '')")
[ -z "$TID" ] && { echo "    ❌ thread not found"; exit 1; }
MSG_COUNT=$(/opt/homebrew/bin/gog gmail thread get "$TID" --account "$GOG_ACCOUNT" --json 2>&1 | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('thread',d).get('messages',d.get('messages',[]))))")
[ "$MSG_COUNT" -lt 2 ] && { echo "    ❌ no reply"; exit 1; }
echo "    ✓ reply present"
exit 0
