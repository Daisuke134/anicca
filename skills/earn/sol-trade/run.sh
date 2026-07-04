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
FT_MODEL="${SOL_TRADE_MODEL:-openai/gpt-5-mini}"   # cheapest WORKING tool-caller (~pennies/session), don't bleed the bankroll (FIX-C)

now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

if [ -f "$SKILL_DIR/KILL" ]; then
  echo "{\"ts\":\"$(now)\",\"slot\":\"earn/sol-trade\",\"action\":\"skip\",\"reason\":\"kill-switch\"}" >> "$TRACE"
  exit 0
fi

command -v franklin-trading >/dev/null || { echo "franklin-trading CLI missing" >&2; exit 1; }

# BASELINE STRATEGY (battle-tested seed — the AI starts here, then self-improves; #34/H8).
# Franklin's perp tools are PAPER, but JupiterSwap is a REAL on-chain Solana DEX swap — so REAL earning =
# disciplined spot round-trips: buy a token you have a clear TradingSignal edge on, take profit, swap back
# to USDC. The discipline (below) is the seed; the AI tunes it from its own P&L.
PROMPT="You are live with a REAL Solana wallet (this is your entire bankroll). First call your wallet/\
portfolio tool to see your exact USDC + SOL. BASELINE STRATEGY (start here, improve from your own results): \
1) A round-trip Jupiter swap costs ~0.4%+ in fees+slippage — so ONLY trade when TradingSignal gives a CLEAR \
bullish or bearish verdict with real conviction on a liquid token (SOL, major); if the signal is neutral/\
weak, DO NOT trade this session (holding USDC beats paying fees on noise). 2) When you do trade: size small, \
define your take-profit and stop BEFORE swapping, and swap back to USDC to realise. 3) Never swap more than \
you can afford to lose; keep enough SOL for gas. Execute a REAL swap only if the edge clears the fee hurdle; \
otherwise wait and say why. Keep a note for next session. Mind model spend — your fuel is the same wallet."

OUT=$(timeout 600 franklin-trading start --trust -m "$FT_MODEL" --max-spend "$MAX_SPEND" -p "$PROMPT" 2>&1); RC=$?
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
