#!/usr/bin/env bash
# VSDD oracle for record-earn.mjs (G1.1, post-adversary sprint-2). Fences every fabrication path:
#  STATIC: every override seam (dir/wallet/ledger/now/baseline/rpc) is gated behind FOUNDER_TEST (FIND-001/008) so prod
#          trusts nothing from the caller; baseline is written atomically (FIND-009).
#  BEHAVIORAL: first run INITIALIZES the baseline and records NOTHING (FIND-007); a corrupt baseline fails closed
#          (FIND-009); only a REAL increase is recorded; no double-count; INV-1/3/6 hold.
set -uo pipefail
M="/Users/anicca/anicca/skills/self/founder-loop/record-earn.mjs"
FW="0x810f6d61f7606deee2657d3083e150a222bc29c5"
A3="0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }
mkdir_dir(){ local d; d="$(mktemp -d)"; mkdir -p "$d/state"; printf '{"address":"%s"}' "$1" > "$d/wallet.json"; echo "$d"; }

# ---------- STATIC: every seam is TEST-gated (prod un-fakeable, FIND-001/008) ----------
src="$(cat "$M")"
for seam in FOUNDER_DIR FOUNDER_WALLET FOUNDER_LEDGER FOUNDER_USDC_NOW FOUNDER_USDC_BASELINE BASE_RPC_URL; do
  bad="$(grep -n "process\.env\.$seam" <<<"$src" | grep -v "TEST" || true)"
  ok "$([ -z "$bad" ] && echo 1 || echo 0)" "STATIC: $seam read is TEST-gated (offending: ${bad:-none})"
done
ok "$(grep -q "renameSync" <<<"$src" && echo 1 || echo 0)" "STATIC: baseline written atomically (renameSync) — FIND-009"
ok "$(grep -q 'startsWith(path.resolve(FOUNDER_DIR)' <<<"$src" && echo 1 || echo 0)" "STATIC: ledger anchored INSIDE founder dir — INV-3/FIND-004"

# ---------- BEHAVIORAL (all in FOUNDER_TEST=1 with a temp dir) ----------
# 1. FIRST run => INIT baseline to current, record NOTHING (FIND-007)
T="$(mkdir_dir "$FW")"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_USDC_NOW=5 node "$M" 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && [ ! -s "$T/state/earn-ledger.jsonl" ] && [ "$(cat "$T/state/usdc-baseline.txt" 2>/dev/null)" = "5" ] && echo 1 || echo 0)" "first run: baseline init=5, NO earning recorded (rc=$rc — $OUT)"

# 2. REAL earn once a baseline exists: 3 -> 5 = +2
T="$(mkdir_dir "$FW")"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_USDC_BASELINE=3 FOUNDER_USDC_NOW=5 node "$M" --source x402 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && [ "$(jq -r '.earn_usdc' "$T/state/earn-ledger.jsonl" 2>/dev/null | tail -1)" = "2" ] && echo 1 || echo 0)" "verified earn +2 written (rc=$rc)"

# 3/4. delta 0 / <0 => fail-closed, no write
for nb in "3 3" "3 2"; do set -- $nb
  T="$(mkdir_dir "$FW")"
  OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_USDC_BASELINE=$1 FOUNDER_USDC_NOW=$2 node "$M" 2>&1)"; rc=$?
  ok "$([ $rc -ne 0 ] && [ ! -s "$T/state/earn-ledger.jsonl" ] && echo 1 || echo 0)" "delta($1->$2)<=0: rc=$rc !=0 + no write"
done

# 5. INV-1: shared wallet override rejected even with a real increase
T="$(mkdir_dir "$FW")"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_WALLET="$A3" FOUNDER_USDC_BASELINE=3 FOUNDER_USDC_NOW=9 node "$M" 2>&1)"; rc=$?
ok "$([ $rc -ne 0 ] && echo 1 || echo 0)" "INV-1: shared automaton wallet rejected (rc=$rc)"

# 6. INV-3: ledger at the dashboard render source rejected
T="$(mkdir_dir "$FW")"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_LEDGER=/Users/anicca/anicca/runtime/dashboard/earn.jsonl FOUNDER_USDC_BASELINE=3 FOUNDER_USDC_NOW=9 node "$M" 2>&1)"; rc=$?
ok "$([ $rc -ne 0 ] && echo 1 || echo 0)" "INV-3: runtime/dashboard ledger path rejected (rc=$rc)"

# 7. corrupt baseline file => fail-closed, never coerced to 0 (FIND-009)
T="$(mkdir_dir "$FW")"; printf 'abc-corrupt' > "$T/state/usdc-baseline.txt"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_USDC_NOW=5 node "$M" 2>&1)"; rc=$?
ok "$([ $rc -ne 0 ] && [ ! -s "$T/state/earn-ledger.jsonl" ] && echo 1 || echo 0)" "corrupt baseline → fail-closed (rc=$rc)"

# 8. no double-count: init(5) → re-run at 5 fail-closed → 7 records +2, baseline=7
T="$(mkdir_dir "$FW")"
FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_USDC_NOW=5 node "$M" >/dev/null 2>&1; ri=$?
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_USDC_NOW=5 node "$M" 2>&1)"; r0=$?
FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_USDC_NOW=7 node "$M" >/dev/null 2>&1; r2=$?
ok "$([ $ri -eq 0 ] && [ $r0 -ne 0 ] && [ "$(jq -r '.earn_usdc' "$T/state/earn-ledger.jsonl" 2>/dev/null | tail -1)" = "2" ] && [ "$(cat "$T/state/usdc-baseline.txt")" = "7" ] && echo 1 || echo 0)" "no double-count: init5→(5 fail)→(7=+2), baseline=7 (ri=$ri r0=$r0 r2=$r2)"

# 9. missing wallet.json => fail-closed
T="$(mktemp -d)"; mkdir -p "$T/state"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_USDC_BASELINE=3 FOUNDER_USDC_NOW=9 node "$M" 2>&1)"; rc=$?
ok "$([ $rc -ne 0 ] && echo 1 || echo 0)" "missing wallet.json → fail-closed (rc=$rc)"

[ $fails -eq 0 ] && { echo "PASS — founder record-earn invariants hold (static seam-gating + first-run-init + corrupt-baseline + no-double-count + INV-1/3/6)"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
