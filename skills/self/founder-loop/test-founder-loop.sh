#!/usr/bin/env bash
LIFE_MANAGER_REPO="${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$LIFE_MANAGER_REPO" ] || { echo "LIFE_MANAGER_REPO could not be resolved" >&2; exit 2; }
export LIFE_MANAGER_REPO
# VSDD oracle for founder-loop.sh (G1.1-B). One no-human wake: STATE-restore → record-earn (the ONLY ledger writer)
# → goal-check on the REAL ledger → atomic STATE.md. Fences INV-H1..6.
set -uo pipefail
H="$LIFE_MANAGER_REPO/skills/self/founder-loop/founder-loop.sh"
FW="0x810f6d61f7606deee2657d3083e150a222bc29c5"
EXT="0x1111111111111111111111111111111111111111"
A3="0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21"
fails=0
ok(){ [ "$1" = 1 ] || { echo "  - FAIL $2"; fails=$((fails+1)); }; }
mkdir_dir(){ local d; d="$(mktemp -d)"; mkdir -p "$d/state"; printf '{"address":"%s"}' "$FW" > "$d/wallet.json"; echo "$d"; }

# ---------- STATIC ----------
src="$(cat "$H")"
ok "$(grep -qE '>>?[[:space:]]*"\$LEDGER"' <<<"$src" && echo 0 || echo 1)" "INV-H2: harness NEVER writes the ledger itself (only record-earn does)"
ok "$(grep -q 'node "\$RECORD"' <<<"$src" && echo 1 || echo 0)" "INV-H2: the harness calls record-earn for earnings"
ok "$(grep -q 'mv "\$TMP"' <<<"$src" && echo 1 || echo 0)" "INV-H3: STATE written atomically (tmp + mv)"
ok "$(grep -q '</dev/null' <<<"$src" && echo 1 || echo 0)" "INV-H4: record-earn run with no stdin (no-human)"
ok "$(grep -qE '^[[:space:]]*read[[:space:]]' <<<"$src" && echo 0 || echo 1)" "INV-H4: no interactive read/prompt"
ok "$(grep -q 'jq -s' <<<"$src" && grep -q 'realised_earn_usdc' <<<"$src" && echo 1 || echo 0)" "INV-H5: realised_earn summed from the REAL ledger, not 'the wake ran'"
H_code="$(sed 's|#.*||' "$H")"   # FIND-903: strip comments so a comment can't false-pass/fail the gate
bad="$(grep 'FOUNDER_LEDGER' <<<"$H_code" | grep -v 'FOUNDER_TEST' || true)"
ok "$([ -z "$bad" ] && echo 1 || echo 0)" "FIND-901: every FOUNDER_LEDGER read is TEST-gated — prod ledger path is env-independent (offending: ${bad:-none})"

# ---------- BEHAVIORAL ----------
# 1. external income → STATE realised_earn=5, status EARNING
T="$(mkdir_dir)"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_CURSOR=100 FOUNDER_BLOCK_NOW=200 FOUNDER_LOGS_JSON="[{\"from\":\"$EXT\",\"value\":5}]" bash "$H" 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && grep -q 'realised_earn_usdc: 5' "$T/STATE.md" 2>/dev/null && grep -q 'status: EARNING' "$T/STATE.md" && echo 1 || echo 0)" "income wake: STATE realised_earn=5, EARNING (rc=$rc — $OUT)"

# 2. self-transfer only → realised_earn=0, status NO (THE GOAL: a self-payment never shows as earning)
T="$(mkdir_dir)"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_CURSOR=100 FOUNDER_BLOCK_NOW=200 FOUNDER_LOGS_JSON="[{\"from\":\"$A3\",\"value\":9}]" bash "$H" 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && grep -q 'realised_earn_usdc: 0' "$T/STATE.md" 2>/dev/null && grep -q 'status: NO' "$T/STATE.md" && echo 1 || echo 0)" "self-transfer wake: realised_earn=0, NO (rc=$rc)"

# 3. first run (no cursor) → record-earn inits, realised_earn=0
T="$(mkdir_dir)"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_BLOCK_NOW=200 bash "$H" 2>&1)"; rc=$?
ok "$([ $rc -eq 0 ] && grep -q 'realised_earn_usdc: 0' "$T/STATE.md" 2>/dev/null && [ "$(cat "$T/state/block-cursor.txt" 2>/dev/null)" = "200" ] && echo 1 || echo 0)" "first-run wake: cursor init, realised_earn=0 (rc=$rc)"

# 4. fail-safe: record-earn ERROR (corrupt cursor) → STATE still written, rc surfaced (!=0)
T="$(mkdir_dir)"; printf 'abc' > "$T/state/block-cursor.txt"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_BLOCK_NOW=200 bash "$H" 2>&1)"; rc=$?
ok "$([ $rc -ne 0 ] && [ -f "$T/STATE.md" ] && ! grep -q 'last_record_rc: 0' "$T/STATE.md" && echo 1 || echo 0)" "fail-safe: record-earn error → STATE still written + rc!=0 surfaced (rc=$rc)"

# 5. INV-H3: no STATE.md.tmp left behind
T="$(mkdir_dir)"
FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_CURSOR=100 FOUNDER_BLOCK_NOW=200 FOUNDER_LOGS_JSON="[{\"from\":\"$EXT\",\"value\":5}]" bash "$H" >/dev/null 2>&1
ok "$([ -z "$(ls "$T"/STATE.md.tmp.* 2>/dev/null)" ] && echo 1 || echo 0)" "INV-H3: no STATE.md.tmp left after the wake (atomic)"

# 6. INV-H1: a 2nd wake reads the prior STATE (prev_realised_earn reflects the 1st wake's value)
T="$(mkdir_dir)"
FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_CURSOR=100 FOUNDER_BLOCK_NOW=200 FOUNDER_LOGS_JSON="[{\"from\":\"$EXT\",\"value\":5}]" bash "$H" >/dev/null 2>&1
FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_BLOCK_NOW=300 bash "$H" >/dev/null 2>&1
ok "$(grep -q 'prev_realised_earn_usdc: 5' "$T/STATE.md" 2>/dev/null && echo 1 || echo 0)" "INV-H1: 2nd wake read prior STATE (prev_realised_earn=5)"

# 7. FIND-903: a corrupt ledger → LEDGER UNREADABLE + rc surfaced (NOT silently realised_earn=0)
T="$(mkdir_dir)"; printf 'not-json\n' > "$T/state/earn-ledger.jsonl"; echo 100 > "$T/state/block-cursor.txt"
OUT="$(FOUNDER_TEST=1 FOUNDER_DIR="$T" FOUNDER_BLOCK_NOW=200 FOUNDER_LOGS_JSON='[]' bash "$H" 2>&1)"; rc=$?
ok "$([ $rc -ne 0 ] && grep -q 'LEDGER UNREADABLE' "$T/STATE.md" 2>/dev/null && echo 1 || echo 0)" "FIND-903: corrupt ledger → UNREADABLE + rc surfaced, not a silent 0 (rc=$rc)"

[ $fails -eq 0 ] && { echo "PASS — founder-loop harness invariants hold (INV-H1 read-state-first · H2 ledger-via-record-earn-only · H3 atomic STATE · H4 no-human · H5 goal-on-real-ledger · H6 fail-safe · FOUNDER_LEDGER TEST-gated · corrupt-ledger fail-safe)"; exit 0; } || { echo "FAIL ($fails)"; exit 1; }
