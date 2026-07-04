#!/bin/bash
# pm-trade run.sh — THIN HARNESS. THIS FILE DECIDES NOTHING. (spec §0.25)
# The base agent (BlockRunAI/polymarket-agent) does its OWN analysis / sizing /
# execution with its OWN wallet. This wrapper only: kill-switch gate → one real
# live pass (NO dry-run, HARD 0.24) → append a structured trace line (H1).
set -u
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
STATE_DIR="$SKILL_DIR/../state"; mkdir -p "$STATE_DIR"
TRACE="$STATE_DIR/pm-trade.trace.jsonl"
AGENT_HOME="${PM_TRADE_AGENT_HOME:-$HOME/.anicca-founder/agents/polymarket-agent}"

now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# money-safety guard #1: kill-switch (touch KILL next to this script to stop)
if [ -f "$SKILL_DIR/KILL" ]; then
  echo "{\"ts\":\"$(now)\",\"slot\":\"earn/pm-trade\",\"action\":\"skip\",\"reason\":\"kill-switch\"}" >> "$TRACE"
  exit 0
fi

if [ ! -d "$AGENT_HOME" ]; then
  echo "{\"ts\":\"$(now)\",\"slot\":\"earn/pm-trade\",\"action\":\"error\",\"error\":\"agent home missing: $AGENT_HOME\"}" >> "$TRACE"
  echo "agent home missing: $AGENT_HOME" >&2
  exit 1
fi

# money-safety guard #2: per-trade cap lives in the agent's own config
# (.env MAX_BET_PERCENTAGE × INITIAL_BANKROLL, plus executor MAX_BET_SIZE).
cd "$AGENT_HOME"
OUT=$(printf 'yes\n' | timeout 900 .venv/bin/python main.py --live 2>&1); RC=$?
echo "$OUT" | tail -40

TRADES=$(echo "$OUT" | sed -n 's/.*Trades executed: \([0-9][0-9]*\).*/\1/p' | tail -1)
TAIL_ERR=""
[ "$RC" -ne 0 ] && TAIL_ERR=$(echo "$OUT" | tail -3 | tr '\n' ' ')

TRACE_FILE="$TRACE" RC="$RC" TRADES="${TRADES:-}" ERR="$TAIL_ERR" python3 - <<'PY'
import json, os, datetime
rec = {
    "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "slot": "earn/pm-trade",
    "action": "live-pass",
    "exit": int(os.environ["RC"]),
    "trades": int(os.environ["TRADES"]) if os.environ["TRADES"] else None,
    "error": os.environ["ERR"] or None,
}
with open(os.environ["TRACE_FILE"], "a") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
PY
exit "$RC"
