#!/usr/bin/env bash
# VSDD oracle for record-earn.mjs (G1.1-A2, external-inflow model). THE GOAL: an earning is ONLY external USDC credited
# to the founder wallet (from ∉ my wallets), summed by block cursor — a self-transfer can NEVER fabricate an earning.
# Plus all sprint-1..5 anti-fake invariants (seam-gating, wallet pin, ledger realpath, env-independent prod root,
# fail-closed, atomic cursor advance).
set -uo pipefail
M="/Users/anicca/anicca/skills/self/founder-loop/record-earn.mjs"
FW="0x810f6d61f7606deee2657d3083e150a222bc29c5"
A3="0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21"   # automaton = MY wallet (internal)
EXT="0x1111111111111111111111111111111111111111" # external payer
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }
mkdir_dir(){ local d; d="$(mktemp -d)"; mkdir -p "$d/state"; printf '{"address":"%s"}' "$1" > "$d/wallet.json"; echo "$d"; }

# ---------- STATIC ----------
src="$(cat "$M")"
for seam in FOUNDER_DIR FOUNDER_WALLET FOUNDER_LEDGER FOUNDER_CURSOR FOUNDER_BLOCK_NOW FOUNDER_LOGS_JSON BASE_RPC_URL HOME; do
  bad="$(grep -n "process\.env\.$seam" <<<"$src" | grep -v "TEST" || true)"
  ok "$([ -z "$bad" ] && echo 1 || echo 0)" "STATIC: $seam read is TEST-gated (${bad:-none})"
done
ok "$(grep -q "renameSync" <<<"$src" && echo 1 || echo 0)" "STATIC: cursor written atomically (renameSync)"
ok "$(grep -q 'realpathSync(FOUNDER_DIR)' <<<"$src" && echo 1 || echo 0)" "STATIC: ledger realpath symlink-deref — INV-3"
ok "$(grep -qF ': "/Users/anicca/.anicca-founder"' <<<"$src" && echo 1 || echo 0)" "STATIC: prod root is an env-independent literal — FIND-401"
ok "$(grep -q 'MY_WALLETS' <<<"$src" && echo 1 || echo 0)" "STATIC: external-payer check (MY_WALLETS) present — INV-7"

# ---------- BEHAVIORAL ----------
# 1. first run (no cursor) → init cursor, record nothing
T="$(mkdir_dir "$FW")"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_BLOCK_NOW=200 node "$M" 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && [ ! -s "$T/state/earn-ledger.jsonl" ] && [ "$(cat "$T/state/block-cursor.txt" 2>/dev/null)" = "200" ] && echo 1 || echo 0)" "first run: cursor init=200, NO row (rc=$rc — $OUT)"

# 2. EXTERNAL payment → recorded; cursor advances (no re-scan = no double-count)
T="$(mkdir_dir "$FW")"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_CURSOR=100 FOUNDER_BLOCK_NOW=200 FOUNDER_LOGS_JSON="[{\"from\":\"$EXT\",\"value\":5}]" node "$M" 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && [ "$(jq -r '.earn_usdc' "$T/state/earn-ledger.jsonl" 2>/dev/null | tail -1)" = "5" ] && [ "$(cat "$T/state/block-cursor.txt")" = "200" ] && echo 1 || echo 0)" "external +5 recorded, cursor→200 (rc=$rc)"

# 3. ★THE GOAL★ self-transfer only → ZERO earning, no row
T="$(mkdir_dir "$FW")"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_CURSOR=100 FOUNDER_BLOCK_NOW=200 FOUNDER_LOGS_JSON="[{\"from\":\"$A3\",\"value\":9}]" node "$M" 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && [ ! -s "$T/state/earn-ledger.jsonl" ] && echo 1 || echo 0)" "self-transfer ONLY: no earning (a self-payment can't fake income) — INV-7 (rc=$rc)"

# 4. MIXED → only external counted
T="$(mkdir_dir "$FW")"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_CURSOR=100 FOUNDER_BLOCK_NOW=200 FOUNDER_LOGS_JSON="[{\"from\":\"$EXT\",\"value\":5},{\"from\":\"$A3\",\"value\":3},{\"from\":\"$FW\",\"value\":2}]" node "$M" 2>&1)"; rc=$?
ok "$([ "$(jq -r '.earn_usdc' "$T/state/earn-ledger.jsonl" 2>/dev/null | tail -1)" = "5" ] && echo 1 || echo 0)" "mixed: only external 5 counted (self 3+2 ignored)"

# 5. corrupt cursor → fail-closed
T="$(mkdir_dir "$FW")"; printf 'abc' > "$T/state/block-cursor.txt"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_BLOCK_NOW=200 node "$M" 2>&1)"; rc=$?
ok "$([ $rc -ne 0 ] && [ ! -s "$T/state/earn-ledger.jsonl" ] && echo 1 || echo 0)" "corrupt cursor → fail-closed (rc=$rc)"

# 6. INV-1 shared wallet rejected
T="$(mkdir_dir "$FW")"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_WALLET="$A3" FOUNDER_CURSOR=100 FOUNDER_BLOCK_NOW=200 FOUNDER_LOGS_JSON="[{\"from\":\"$EXT\",\"value\":9}]" node "$M" 2>&1)"; rc=$?
ok "$([ $rc -ne 0 ] && echo 1 || echo 0)" "INV-1: shared automaton wallet rejected (rc=$rc)"

# 7. INV-1 pin: non-shared, non-expected wallet rejected
T="$(mkdir_dir "$FW")"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_WALLET="$EXT" FOUNDER_CURSOR=100 FOUNDER_BLOCK_NOW=200 FOUNDER_LOGS_JSON="[]" node "$M" 2>&1)"; rc=$?
ok "$([ $rc -ne 0 ] && echo 1 || echo 0)" "INV-1 pin: non-expected wallet rejected (rc=$rc)"

# 8. INV-3 dashboard render path rejected
T="$(mkdir_dir "$FW")"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_LEDGER=/Users/anicca/anicca/runtime/dashboard/earn.jsonl FOUNDER_CURSOR=100 FOUNDER_BLOCK_NOW=200 FOUNDER_LOGS_JSON="[{\"from\":\"$EXT\",\"value\":9}]" node "$M" 2>&1)"; rc=$?
ok "$([ $rc -ne 0 ] && echo 1 || echo 0)" "INV-3: runtime/dashboard ledger rejected (rc=$rc)"

# 9. INV-3 symlink escape rejected
T="$(mkdir_dir "$FW")"; EVIL="$(mktemp -d)"; rm -rf "$T/state"; ln -s "$EVIL" "$T/state"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_CURSOR=100 FOUNDER_BLOCK_NOW=200 FOUNDER_LOGS_JSON="[{\"from\":\"$EXT\",\"value\":9}]" node "$M" 2>&1)"; rc=$?
ok "$([ $rc -ne 0 ] && [ ! -s "$EVIL/earn-ledger.jsonl" ] && echo 1 || echo 0)" "INV-3: symlinked state/ escaping founder dir rejected (rc=$rc)"

# 10. missing wallet.json → fail-closed
T="$(mktemp -d)"; mkdir -p "$T/state"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_BLOCK_NOW=200 node "$M" 2>&1)"; rc=$?
ok "$([ $rc -ne 0 ] && echo 1 || echo 0)" "missing wallet.json → fail-closed (rc=$rc)"

# 11. block height backwards → fail-closed
T="$(mkdir_dir "$FW")"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_CURSOR=300 FOUNDER_BLOCK_NOW=200 FOUNDER_LOGS_JSON="[]" node "$M" 2>&1)"; rc=$?
ok "$([ $rc -ne 0 ] && echo 1 || echo 0)" "block backwards (now<cursor) → fail-closed (rc=$rc)"

# 12. PROD HOME-poison ignored (env-independent root) — assert ONLY planted dir stays empty (FIND-401/501)
PLANT="$(mktemp -d)"; mkdir -p "$PLANT/.anicca-founder/state"
printf '{"address":"%s"}' "$FW" > "$PLANT/.anicca-founder/wallet.json"; echo 100 > "$PLANT/.anicca-founder/state/block-cursor.txt"
HOME="$PLANT" node "$M" >/dev/null 2>&1
ok "$([ ! -s "$PLANT/.anicca-founder/state/earn-ledger.jsonl" ] && echo 1 || echo 0)" "PROD: HOME-poisoned planted dir NOT used as root — FIND-401"

[ $fails -eq 0 ] && { echo "PASS — founder record-earn (external-inflow model): external-only earnings (self-transfer=0, INV-7) + seam-gating + wallet-pin + ledger-realpath + env-independent root + corrupt/backwards fail-closed + atomic cursor"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
