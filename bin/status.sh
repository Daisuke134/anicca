#!/usr/bin/env bash
# status.sh — REQ-CEO-010: reports every loop declared in config/loop-registry.json (`live` loops'
# own --status output; `external`/`stub` loops' declared status, without invoking anything for
# them). Degrades to the original hardcoded bounty/affiliate/gig list when the registry is
# missing/unreadable.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY=/opt/homebrew/bin/python3; [ -x "$PY" ] || PY=python3
REGISTRY="$ROOT/config/loop-registry.json"

if [ ! -f "$REGISTRY" ]; then
  printf 'bounty\t'
  bash "$ROOT/skills/bounty/bounty-cli.sh" --status
  printf 'affiliate\t'
  bash "$ROOT/skills/affiliate/affiliate-cli.sh" --status
  printf 'gig\t'
  bash "$ROOT/skills/gig-work/gig-cli.sh" --status
  exit 0
fi

LOOPS="$("$PY" -c "
import json
with open('$REGISTRY') as f:
    reg = json.load(f)
for name, entry in reg.get('loops', {}).items():
    skill_dir = entry.get('skill_dir', 'skills/' + name)
    print(name + chr(9) + entry.get('status', '') + chr(9) + skill_dir)
" 2>/dev/null)"

while IFS=$'\t' read -r loop status skill_dir; do
  [ -z "$loop" ] && continue
  printf '%s\t%s\t' "$loop" "$status"
  if [ "$status" = "live" ]; then
    CLI="$ROOT/$skill_dir/$loop-cli.sh"
    if [ -f "$CLI" ]; then
      bash "$CLI" --status
    else
      echo "UNKNOWN (cli missing)"
    fi
  else
    echo "external/stub (not managed by this repo)"
  fi
done <<LOOPLIST
$LOOPS
LOOPLIST

if [ -f "$ROOT/bin/ceo-status.sh" ]; then
  echo "--- ceo-status ---"
  bash "$ROOT/bin/ceo-status.sh"
fi
