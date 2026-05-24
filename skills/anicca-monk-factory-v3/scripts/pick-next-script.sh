#!/usr/bin/env bash
# Rotation through the prepared bank — pick the next UNUSED script (never generate new).
# Usage:
#   pick-next-script.sh next   → prints the next unused script's ID + its script text (JSON {id, script})
#   pick-next-script.sh mark <ID>   → record <ID> as used (call AFTER a successful post)
# When all 30 are used, the used log resets → rotation cycles from the top again.
set -euo pipefail
SKILL="$HOME/.openclaw/skills/anicca-monk-factory-v3"
BANK="$SKILL/04-script/bank_en.jsonl"
USED="$SKILL/04-script/used.log"
touch "$USED"
MODE="${1:-next}"

if [ "$MODE" = "mark" ]; then
  [ -n "${2:-}" ] || { echo "usage: mark <ID>"; exit 1; }
  echo "$2" >> "$USED"; echo "marked $2 used"; exit 0
fi

python3 - "$BANK" "$USED" <<'PY'
import json,sys,os
bank,used=sys.argv[1],sys.argv[2]
ids=[]; rec={}
for line in open(bank):
    line=line.strip()
    if not line: continue
    o=json.loads(line); ids.append(o['id']); rec[o['id']]=o
usedset=set(x.strip() for x in open(used) if x.strip())
nxt=next((i for i in ids if i not in usedset), None)
if nxt is None:           # all used → reset rotation, start over
    open(used,'w').close(); nxt=ids[0]
o=rec[nxt]
print(json.dumps({"id":nxt,"track":o.get("track"),"script":o.get("script","")}))
PY
