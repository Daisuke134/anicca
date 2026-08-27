#!/usr/bin/env bash
# start-all.sh — REQ-CEO-010: starts every `live` loop declared in config/loop-registry.json and
# prints (without starting) the declared status of every `external`/`stub` loop. Degrades to the
# original hardcoded bounty/affiliate/gig list when the registry is missing/unreadable.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY=/opt/homebrew/bin/python3; [ -x "$PY" ] || PY=python3
REGISTRY="$ROOT/config/loop-registry.json"

_degrade() {
  echo "start-all: config/loop-registry.json missing/unreadable -- degrading to the hardcoded bounty/affiliate/gig list"
  bash "$ROOT/skills/bounty/bounty-cli.sh"
  bash "$ROOT/skills/affiliate/affiliate-cli.sh"
  bash "$ROOT/skills/gig-work/gig-cli.sh"
  bash "$ROOT/bin/status.sh"
}

if [ ! -f "$REGISTRY" ]; then
  _degrade
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

if [ -z "$LOOPS" ]; then
  _degrade
  exit 0
fi

while IFS=$'\t' read -r loop status skill_dir; do
  [ -z "$loop" ] && continue
  if [ "$status" = "live" ]; then
    CLI="$ROOT/$skill_dir/$loop-cli.sh"
    if [ -f "$CLI" ]; then
      bash "$CLI"
    else
      echo "start-all: ERROR $loop is live but $CLI does not exist -- skipping"
    fi
  else
    echo "start-all: $loop status=$status (external/stub, not started by this repo)"
  fi
done <<LOOPLIST
$LOOPS
LOOPLIST

bash "$ROOT/bin/status.sh"

# REQ-CEO-015: the CEO's own daily light pass runs on its own schedule, see
# launchd/ai.anicca.ceo-runner.plist (not started here -- it is a launchd-driven pass, not a
# tmux/claude core like the loops above).
