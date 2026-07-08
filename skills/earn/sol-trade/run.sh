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

# IDENTITY-MATCH GUARD (money-safety): the franklin-trading CLI hardcodes its wallet to ~/.blockrun,
# so ANY instance running this slot would trade Franklin's wallet. Only the instance that OWNS
# ~/.blockrun (Franklin) may proceed; every other instance (automaton) HALTs before touching the CLI.
WADDR="$SKILL_DIR/../../../runtime/wallet-address-solana.mjs"
OWN_WALLET=$(node "$WADDR" 2>/dev/null)
CLI_WALLET=$(ANICCA_HOME="$HOME/.blockrun" node "$WADDR" 2>/dev/null)
if [ -z "$OWN_WALLET" ] || [ -z "$CLI_WALLET" ] || [ "$OWN_WALLET" != "$CLI_WALLET" ]; then
  echo "{\"ts\":\"$(now)\",\"slot\":\"earn/sol-trade\",\"action\":\"skip\",\"reason\":\"identity-mismatch (own=${OWN_WALLET:-none} cli=${CLI_WALLET:-none}); only Franklin(.blockrun) may run this slot\"}" >> "$TRACE"
  exit 0
fi

# cumulative-loss guard (fail-closed) — same one-line idiom as economy/gig/run.sh:62 / earn/run.sh
LEDGER="${EARN_LEDGER:-$STATE_DIR/earn-ledger.jsonl}"
if ! node "$SKILL_DIR/../../_shared/lib/earn-guard.mjs" check "$OWN_WALLET" "sol-trade" "$LEDGER" 2>/dev/null; then
  echo "{\"ts\":\"$(now)\",\"slot\":\"earn/sol-trade\",\"action\":\"skip\",\"reason\":\"earn-guard: cumulative net breach -- HALT (fail-closed)\"}" >> "$TRACE"
  exit 0
fi

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
you can afford to lose; keep enough SOL for gas. 4) You are running fully unsupervised on a timer — nobody \
reads this session or replies to it, so NEVER end your turn with a question, a menu of choices, or 'let me \
know if you want me to...'. If you catch yourself about to offer options, that means you already have \
enough information to decide right now — so decide. Execute a REAL swap only if the edge clears the fee \
hurdle; otherwise WAIT and say why in one line. Every pass ends in exactly one of those two states — a \
filled trade or a one-line WAIT reason — never an open question. Keep a note for next session. Mind model \
spend — your fuel is the same wallet."

OUT=$(timeout 600 franklin-trading start --trust -m "$FT_MODEL" --max-spend "$MAX_SPEND" -p "$PROMPT" 2>&1); RC=$?
echo "$OUT" | tail -30

# P&L RECORD (REQ-002): if this pass did a REAL Jupiter swap, extract its signature and record the
# on-chain USDC delta (win OR loss) so isProfitable / self-eval finally see Franklin's OWN realized
# results (until now sol-trade never wrote to earn-ledger, so profitable was permanently false).
# Fail-soft: never brick the pass. ANSI codes stripped before parsing (defensive).
SIG=$(printf '%s' "$OUT" | sed "s/$(printf '\033')\[[0-9;]*m//g" | grep -oiE 'signature:[[:space:]]*[1-9A-HJ-NP-Za-km-z]{60,100}' | head -1 | grep -oE '[1-9A-HJ-NP-Za-km-z]{60,100}' | head -1)
if [ -n "$SIG" ]; then
  REC=$(env -i PATH="$PATH" HOME="$HOME" SOLANA_RPC_URL="${SOLANA_RPC_URL:-}" SIG="$SIG" WALLET="$OWN_WALLET" EARN_LEDGER="$LEDGER" WAKE_ID="${WAKE_ID:-$(date -u +%s)}" node "$SKILL_DIR/lib/record-swap.mjs" 2>/dev/null || true)
  echo "[sol-trade] record-swap -> ${REC:-noop}"
fi

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

# Signed telemetry POST (#25 TELEM) — fail-safe: never affects the trade pass's own exit code above.
timeout 20 node "$SKILL_DIR/../../../runtime/dashboard/telemetry-post-franklin.mjs" >> "$STATE_DIR/telemetry-post.log" 2>&1 || true

exit "$RC"
