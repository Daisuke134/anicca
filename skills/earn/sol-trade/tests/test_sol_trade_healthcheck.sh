#!/usr/bin/env bash
# test_sol_trade_healthcheck.sh — end-to-end wiring proof for sol-trade-healthcheck.sh: BARREN trace
# -> self-fix escalated (SELF_FIX_DRYRUN=1 seam, no real tmux/claude spawn, no real state touched);
# healthy trace -> no escalation; and a second BARREN check within the escalation window does not
# spam a second self-fix call. All state/log/trace paths are overridden to an isolated tmpdir so this
# test never reads or writes real external runtime state (read-only-on-live-state rule).
set -uo pipefail; P=0; F=0
H="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"          # skills/earn/sol-trade/tests
SKILL_DIR="$(cd "$H/.." && pwd)"                            # skills/earn/sol-trade
HC="$SKILL_DIR/sol-trade-healthcheck.sh"
SELF_DIR="$(cd "$SKILL_DIR/../../self" && pwd)"

a(){ echo "$2" | grep -qF "$3" && { echo "  ok $1"; P=$((P+1)); } || { echo "  FAIL $1 want:[$3] got:[$2]"; F=$((F+1)); }; }
na(){ echo "$2" | grep -qF "$3" && { echo "  FAIL $1 (unexpectedly found:[$3])"; F=$((F+1)); } || { echo "  ok $1"; P=$((P+1)); }; }

REASON="identity-mismatch (own=none cli=none); only Franklin(.blockrun) may run this slot"

mk_barren_trace(){
  local out="$1" n="${2:-20}"
  : > "$out"
  for i in $(seq 1 "$n"); do
    printf '{"ts":"2026-07-08T%02d:00:00Z","slot":"earn/sol-trade","action":"skip","reason":"%s"}\n' "$((i % 24))" "$REASON" >> "$out"
  done
}
mk_healthy_trace(){
  local out="$1"
  : > "$out"
  for i in $(seq 1 15); do
    printf '{"ts":"2026-07-08T%02d:00:00Z","slot":"earn/sol-trade","action":"skip","reason":"%s"}\n' "$((i % 24))" "$REASON" >> "$out"
  done
  printf '{"ts":"2026-07-10T14:04:39Z","slot":"earn/sol-trade","action":"live-pass","exit":0,"note":"WAIT — neutral"}\n' >> "$out"
}

echo "(A) BARREN trace -> self-fix escalated (dry-run: no real spawn)"
D="$(mktemp -d)"; TRACE="$D/sol-trade.trace.jsonl"; mk_barren_trace "$TRACE" 20
OUT="$(SOL_TRADE_HC_TRACE="$TRACE" SOL_TRADE_HC_STATE_DIR="$D/state" SOL_TRADE_HC_LOG="$D/hc.log" \
       SOL_TRADE_HC_SELF_DIR="$SELF_DIR" SELF_FIX_DRYRUN=1 bash "$HC" 2>&1; cat "$D/hc.log" 2>/dev/null)"
a "log shows BARREN detected" "$OUT" "BARREN: last 20 trace lines are all skip/'$REASON'"
a "self-fix.sh dry-run fired for the sol-trade loop" "$OUT" "LOOP=sol-trade-loop"
a "escalation marker file was written" "$(ls -a "$D/state" 2>/dev/null)" ".sol-trade-earning-health-escalated"

echo "(B) healthy trace (skips then a real live-pass) -> NOT escalated"
D2="$(mktemp -d)"; TRACE2="$D2/sol-trade.trace.jsonl"; mk_healthy_trace "$TRACE2"
OUT2="$(SOL_TRADE_HC_TRACE="$TRACE2" SOL_TRADE_HC_STATE_DIR="$D2/state" SOL_TRADE_HC_LOG="$D2/hc.log" \
        SOL_TRADE_HC_SELF_DIR="$SELF_DIR" SELF_FIX_DRYRUN=1 bash "$HC" 2>&1; cat "$D2/hc.log" 2>/dev/null)"
a "log shows OK (not barren)" "$OUT2" "OK (last 20 trace entries"
na "self-fix was NOT invoked" "$OUT2" "LOOP=sol-trade-loop"
na "no escalation marker written" "$(ls -a "$D2/state" 2>/dev/null)" ".sol-trade-earning-health-escalated"

echo "(C) BARREN again within the escalation window -> does NOT spam a second self-fix call"
OUT3="$(SOL_TRADE_HC_TRACE="$TRACE" SOL_TRADE_HC_STATE_DIR="$D/state" SOL_TRADE_HC_LOG="$D/hc2.log" \
        SOL_TRADE_HC_SELF_DIR="$SELF_DIR" SOL_TRADE_HC_ESCALATE_EVERY_HRS=24 SELF_FIX_DRYRUN=1 bash "$HC" 2>&1; cat "$D/hc2.log" 2>/dev/null)"
a "second run within window logs 'already escalated'" "$OUT3" "already escalated"
na "second run did NOT re-invoke self-fix" "$OUT3" "LOOP=sol-trade-loop"

echo "(D) no trace file present -> no-op, never crashes"
D3="$(mktemp -d)"
OUT4="$(SOL_TRADE_HC_TRACE="$D3/missing.jsonl" SOL_TRADE_HC_STATE_DIR="$D3/state" SOL_TRADE_HC_LOG="$D3/hc.log" \
        SOL_TRADE_HC_SELF_DIR="$SELF_DIR" bash "$HC" 2>&1; echo "rc=$?"; cat "$D3/hc.log" 2>/dev/null)"
a "no-trace path logs and exits cleanly" "$OUT4" "nothing to check"

rm -rf "$D" "$D2" "$D3"
echo "=== sol-trade-healthcheck: $P passed $F failed ==="; [ "$F" = 0 ] && echo GREEN || exit 1
