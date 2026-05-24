#!/usr/bin/env bash
# core-status.sh — single source of truth for "is the beat alive + what is it doing".
# Ported from Sutando's core-status.json contract (proactive-loop step 0).
#
# The autonomous beat writes its liveness + current step here at the start of a
# pass, updates `step` as it progresses, and writes idle when it ends. A stale
# core-status (running but mtime older than ~2 beat intervals) is the signal the
# self-diagnose health-check uses to detect a stuck / crashed loop.
#
# Usage:
#   core-status.sh running "Starting pass..."   # at beat start
#   core-status.sh step    "picked: ship iOS CI fix (ROI high)"   # mid-pass
#   core-status.sh idle                          # at beat end
#   core-status.sh read                          # print current JSON
set -euo pipefail
ANICCA_HOME="${ANICCA_HOME:-$HOME/.openclaw}"
WS="${ANICCA_WORKSPACE:-$ANICCA_HOME/workspace}"
F="$WS/core-status.json"
mkdir -p "$WS"

now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
host() { hostname | sed 's/\..*//'; }

cmd="${1:-read}"
case "$cmd" in
  running|idle)
    status="$cmd"; step="${2:-}"
    python3 - "$F" "$status" "$step" "$(now)" "$(host)" <<'PY'
import json,sys
f,status,step,ts,host=sys.argv[1:6]
json.dump({"status":status,"step":step,"ts":ts,"host":host}, open(f,"w"), ensure_ascii=False, indent=2)
PY
    ;;
  step)
    step="${2:?usage: core-status.sh step <text>}"
    python3 - "$F" "$step" "$(now)" "$(host)" <<'PY'
import json,sys,os
f,step,ts,host=sys.argv[1:5]
try: d=json.load(open(f))
except Exception: d={"status":"running"}
d.update({"step":step,"ts":ts,"host":host})
json.dump(d, open(f,"w"), ensure_ascii=False, indent=2)
PY
    ;;
  read)
    [ -f "$F" ] && cat "$F" || echo '{"status":"unknown"}'
    ;;
  *) echo "usage: core-status.sh {running|step|idle|read} [text]" >&2; exit 2 ;;
esac
