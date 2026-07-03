#!/bin/bash
# sol-trade run.sh — THIN HARNESS. THIS FILE DECIDES NOTHING. (spec §0.25)
# The base agent (BlockRunAI/Franklin-Trading, `franklin-trading` CLI) does its OWN
# research / sizing / execution and pays for its OWN model calls via x402 from its
# OWN Solana wallet (8Fpqd…). Wrapper = kill-switch → one real pass → trace line.
set -u
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
STATE_DIR="$SKILL_DIR/../state"; mkdir -p "$STATE_DIR"
TRACE="$STATE_DIR/sol-trade.trace.jsonl"
MAX_SPEND="${SOL_TRADE_MAX_SPEND:-0.25}"   # money-safety: per-pass LLM spend cap (USD)

now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

if [ -f "$SKILL_DIR/KILL" ]; then
  echo "{\"ts\":\"$(now)\",\"slot\":\"earn/sol-trade\",\"action\":\"skip\",\"reason\":\"kill-switch\"}" >> "$TRACE"
  exit 0
fi

command -v franklin-trading >/dev/null || { echo "franklin-trading CLI missing" >&2; exit 1; }

PROMPT="You are live. Check your own wallet balance first. This is your entire bankroll. \
Decide for yourself how to grow it by trading — your own research, your own sizing, your own \
risk management. Take whatever real action you judge best right now, or explicitly decide to \
wait and say why. Keep a note of what you did for your next session. Mind your model spend: \
your fuel comes from the same wallet."

OUT=$(timeout 600 franklin-trading start --trust --max-spend "$MAX_SPEND" -p "$PROMPT" 2>&1); RC=$?
echo "$OUT" | tail -30

TRACE_FILE="$TRACE" RC="$RC" OUTTAIL="$(echo "$OUT" | tail -5 | tr '\n' ' ')" python3 - <<'PY'
import json, os, datetime
rec = {
    "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "slot": "earn/sol-trade",
    "action": "live-pass",
    "exit": int(os.environ["RC"]),
    "note": os.environ["OUTTAIL"][:400],
}
with open(os.environ["TRACE_FILE"], "a") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
PY
exit "$RC"
