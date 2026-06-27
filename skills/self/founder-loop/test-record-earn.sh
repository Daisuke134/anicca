#!/usr/bin/env bash
# VSDD oracle for record-earn.mjs (G1.1, post-adversary sprint-1). Fences every fabrication path the adversary found:
# seam test-gated (FIND-001), prod ignores the seam, baseline self-advances (no double-count), wallet=canonical only
# (INV-1/FIND-003), ledger must resolve inside the founder dir incl. runtime/dashboard bypass (INV-3/FIND-004),
# fail-closed everywhere (INV-6), missing-wallet handled (FIND-006).
set -uo pipefail
M="/Users/anicca/anicca/skills/self/founder-loop/record-earn.mjs"
FW="0x810f6d61f7606deee2657d3083e150a222bc29c5"
DEAD="0x$(openssl rand -hex 20 2>/dev/null)"   # a FRESH random addr = guaranteed ~0 USDC for the prod-mode seam test
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }
mkdir_dir(){ local d; d="$(mktemp -d)"; mkdir -p "$d/state"; printf '{"address":"%s"}' "$1" > "$d/wallet.json"; echo "$d"; }

# 1. (test) REAL earn 3->5 => delta +2 written, exit 0
T="$(mkdir_dir "$FW")"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_USDC_BASELINE=3 FOUNDER_USDC_NOW=5 node "$M" --source x402 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && echo 1 || echo 0)" "verified earn: exit $rc — $OUT"
ok "$([ "$(jq -r '.earn_usdc' "$T/state/earn-ledger.jsonl" 2>/dev/null | tail -1)" = "2" ] && echo 1 || echo 0)" "earn_usdc=2 written"

# 2/3. (test) delta 0 / <0 => fail-closed, no write
for nb in "3 3" "3 2"; do set -- $nb
  T="$(mkdir_dir "$FW")"
  OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_USDC_BASELINE=$1 FOUNDER_USDC_NOW=$2 node "$M" 2>&1)"; rc=$?
  ok "$([ $rc -ne 0 ] && [ ! -s "$T/state/earn-ledger.jsonl" ] && echo 1 || echo 0)" "delta($1->$2)<=0: rc=$rc !=0 + no write"
done

# 4. (test) INV-1: a shared wallet override is rejected even with a real increase
T="$(mkdir_dir "$FW")"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_WALLET=0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21 FOUNDER_USDC_BASELINE=3 FOUNDER_USDC_NOW=9 node "$M" 2>&1)"; rc=$?
ok "$([ $rc -ne 0 ] && echo 1 || echo 0)" "INV-1: shared automaton wallet rejected (rc=$rc)"

# 5. (test) INV-3: ledger pointed at the dashboard render source (outside FOUNDER_DIR) is rejected
T="$(mkdir_dir "$FW")"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_LEDGER=/Users/anicca/anicca/runtime/dashboard/earn.jsonl FOUNDER_USDC_BASELINE=3 FOUNDER_USDC_NOW=9 node "$M" 2>&1)"; rc=$?
ok "$([ $rc -ne 0 ] && echo 1 || echo 0)" "INV-3: runtime/dashboard ledger path rejected (rc=$rc)"

# 6. ★FIND-001★ PROD mode (FOUNDER_TEST unset): the FOUNDER_USDC_NOW seam is IGNORED → real RPC for a ~0 addr → fail-closed
T="$(mkdir_dir "$DEAD")"
OUT="$(FOUNDER_DIR="$T" FOUNDER_USDC_NOW=999999 node "$M" 2>&1)"; rc=$?
ok "$([ $rc -ne 0 ] && echo 1 || echo 0)" "PROD: seam ignored, ~0 addr → fail-closed (rc=$rc — $OUT)"
ok "$(grep -q 999999 <<<"$OUT" && echo 0 || echo 1)" "PROD: the fake seam value 999999 never became an earning"

# 7. baseline self-advance (no double-count): file baseline 0->5 then a 2nd run at 5 => delta 0 fail-closed
T="$(mkdir_dir "$FW")"
FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_USDC_NOW=5 node "$M" >/dev/null 2>&1; r1=$?
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_USDC_NOW=5 node "$M" 2>&1)"; r2=$?
ok "$([ $r1 -eq 0 ] && [ $r2 -ne 0 ] && [ "$(cat "$T/state/usdc-baseline.txt")" = "5" ] && echo 1 || echo 0)" "baseline advanced 0→5, re-run at 5 fail-closed (no double-count): r1=$r1 r2=$r2"

# 8. (test) missing wallet.json + no override => fail-closed
T="$(mktemp -d)"; mkdir -p "$T/state"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_USDC_BASELINE=3 FOUNDER_USDC_NOW=9 node "$M" 2>&1)"; rc=$?
ok "$([ $rc -ne 0 ] && echo 1 || echo 0)" "missing wallet.json → fail-closed (rc=$rc)"

[ $fails -eq 0 ] && { echo "PASS — founder record-earn invariants hold (INV-1/2/3/6, seam test-gated, prod un-fakeable)"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
