#!/usr/bin/env bash
# VSDD oracle for record-earn.mjs (G1.1). Verifies the founder ledger writer: only a REAL on-chain USDC increase is
# recorded (INV-2), fail-closed otherwise (INV-6), never a shared wallet (INV-1), never the public site (INV-3).
set -uo pipefail
M="/Users/operator/anicca/skills/self/founder-loop/record-earn.mjs"
FW="0x810f6d61f7606deee2657d3083e150a222bc29c5"   # the distinct founder wallet
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }
run(){ # $1=usdc_now $2=baseline $3=wallet $4=ledger  -> sets rc, OUT
  OUT="$(FOUNDER_USDC_NOW="$1" FOUNDER_WALLET="$3" FOUNDER_LEDGER="$4" node "$M" --source x402 --baseline "$2" --cost 0 --wake t 2>&1)"; rc=$?; }

T="$(mktemp -d)"; L="$T/state/earn-ledger.jsonl"

# 1. REAL earning: balance rose 3 -> 5 (delta +2) -> writes, exit 0
run 5 3 "$FW" "$L"
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "verified earn: exit $rc — $OUT"
ok "$([ -f "$L" ] && [ "$(jq -r '.earn_usdc' "$L" | tail -1)" = "2" ] && echo 1 || echo 0)" "verified earn: row earn_usdc=2 written"

# 2. NO increase (delta 0) -> fail-closed, NO write (INV-2/6)
: > "$L"
run 3 3 "$FW" "$L"
ok "$([ $rc -ne 0 ] && [ ! -s "$L" ] && echo 1 || echo 0)" "delta=0: rc=$rc must be !=0 + ledger empty (no fake)"

# 3. NEGATIVE (delta<0) -> fail-closed
run 2 3 "$FW" "$L"
ok "$([ $rc -ne 0 ] && [ ! -s "$L" ] && echo 1 || echo 0)" "delta<0: rc=$rc must be !=0 + ledger empty"

# 4. INV-1: a shared/other instance wallet -> refuse even with a real increase
run 9 3 "0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21" "$L"
ok "$([ $rc -ne 0 ] && echo 1 || echo 0)" "INV-1: shared automaton wallet rejected (rc=$rc)"

# 5. INV-3: refuse a ledger path under the public site / dashboard
run 9 3 "$FW" "/Users/operator/anicca-project/apps/landing/public/earn.jsonl"
ok "$([ $rc -ne 0 ] && echo 1 || echo 0)" "INV-3: refuses to write the public site / dashboard (rc=$rc)"

rm -rf "$T"
[ $fails -eq 0 ] && { echo "PASS — founder record-earn invariants hold (INV-1/2/3/6)"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
