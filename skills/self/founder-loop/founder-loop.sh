#!/usr/bin/env bash
# founder-loop.sh — ONE no-human wake of the founder MONEY LOOP (GLVS / HARD 0.40).
# Restore STATE → run the verified recorder (record-earn = the ONLY writer of the ledger, with all anti-fake gates,
# INV-1..7) → check THE GOAL on the REAL ledger → write STATE.md atomically → report. A cadence (/loop, cron, launchd)
# wraps this. The harness NEVER appends an earn row itself (INV-H2) and NEVER prompts a human (INV-H4).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECORD="$HERE/record-earn.mjs"

# prod root is env-independent; tests relocate via FOUNDER_TEST + FOUNDER_DIR (mirrors record-earn's FIND-401 fix).
if [ "${FOUNDER_TEST:-}" = "1" ] && [ -n "${FOUNDER_DIR:-}" ]; then DIR="$FOUNDER_DIR"; else DIR="/Users/operator/.anicca-founder"; fi
STATE_MD="$DIR/STATE.md"
LEDGER="${FOUNDER_LEDGER:-$DIR/state/earn-ledger.jsonl}"
mkdir -p "$DIR/state"

# INV-H1: read prior STATE (the durable spine) BEFORE acting.
PREV_EARN=0
[ -f "$STATE_MD" ] && PREV_EARN="$(grep -E '^realised_earn_usdc:' "$STATE_MD" 2>/dev/null | awk '{print $2}' | tail -1)"
PREV_EARN="${PREV_EARN:-0}"

# INV-H2 + INV-H4: ONLY record-earn writes the ledger (its gates decide if a REAL external earn is recorded). No stdin.
node "$RECORD" --source x402 --wake "$(date +%s)" </dev/null >>"$DIR/state/wake.log" 2>&1; RC=$?

# INV-H5: goal-check on the REAL ledger — realised earn = SUM of earn_usdc, NEVER "the wake ran".
TOTAL=0
[ -f "$LEDGER" ] && TOTAL="$(jq -s 'map(.earn_usdc // 0) | add // 0' "$LEDGER" 2>/dev/null || echo 0)"
case "$TOTAL" in ''|*[!0-9.]*) TOTAL=0;; esac
if awk "BEGIN{exit !($TOTAL>0)}" 2>/dev/null; then STATUS="EARNING — real external USDC received; keep growing"; else STATUS="NO realised external earn yet — bottleneck is DEMAND/LISTING/PRICING, not code"; fi

# INV-H3: write STATE.md atomically (tmp + mv).
TMP="$STATE_MD.tmp.$$"
{
  echo "# Founder money loop — STATE (GLVS, no-human)"
  echo "goal: real EXTERNAL USDC to founder 0x810f6d61f7606deee2657d3083e150a222bc29c5 — Done ONLY on a verifiable on-chain receipt, NEVER 'the wake ran'"
  echo "last_wake_utc: $(date -u +%FT%TZ)"
  echo "realised_earn_usdc: $TOTAL"
  echo "prev_realised_earn_usdc: $PREV_EARN"
  echo "last_record_rc: $RC"
  echo "status: $STATUS"
  echo "next: G1.2 — host serve.mjs (X402_PAYTO=0x810f) + LIST on x402scan/Bazaar → a REAL external buyer pays → record-earn writes the first real row"
} > "$TMP" && mv "$TMP" "$STATE_MD"

echo "founder-loop wake: realised_earn_usdc=$TOTAL record_rc=$RC state=$STATE_MD"
# INV-H6: surface the recorder's rc to the cadence (a persistent RPC-fail / corrupt-cursor should alert), AFTER STATE is durably written.
exit "$RC"
