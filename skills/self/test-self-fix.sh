#!/usr/bin/env bash
# test-self-fix.sh — FIND-028/030/031: cover the mechanisms re-patched in rounds 4-6.
# (A) FIND-025 loop-name normalization  (B) FIND-029/030 hang fingerprint  (C) FIND-026/031 real lock acquire/steal.
set -uo pipefail; P=0; F=0; H="$(cd "$(dirname "${BASH_SOURCE[0]}")"&&pwd)"; SF="$H/self-fix.sh"
a(){ echo "$2"|grep -qF "$3"&&{ echo "  ok $1"; P=$((P+1)); }||{ echo "  FAIL $1 want:[$3] got:[$2]"; F=$((F+1)); }; }
eq(){ [ "$2" = "$3" ]&&{ echo "  ok $1"; P=$((P+1)); }||{ echo "  FAIL $1 ($2 vs $3)"; F=$((F+1)); }; }
ne(){ [ "$2" != "$3" ]&&{ echo "  ok $1"; P=$((P+1)); }||{ echo "  FAIL $1 (both $2)"; F=$((F+1)); }; }

echo "(A) loop-name normalization"
S="$(SELF_FIX_DRYRUN=1 bash "$SF" capafy hint 2>&1)"; L="$(SELF_FIX_DRYRUN=1 bash "$SF" capafy-loop hint 2>&1)"
a "short 'capafy' → LOOP=capafy-loop" "$S" 'LOOP=capafy-loop'
a "short → RESULT .self-fix-capafy-loop.result" "$S" '.self-fix-capafy-loop.result'
eq "short==long identical" "$S" "$L"
a "life-manager → life-manager-loop" "$(SELF_FIX_DRYRUN=1 bash "$SF" life-manager h 2>&1)" 'LOOP=life-manager-loop'

echo "(B) FIND-029/030 hang fingerprint — frozen pane (only timer/tokens advance) = SAME hash; real progress = DIFF"
BODY='⏺ Running browser step
  ⎿  page.waitForSelector(".save-btn")'
F1="$(printf '%s\n✢ Deploying… (3m 12s · ↓ 19.4k tokens · esc to interrupt)' "$BODY" | bash "$SF" --fingerprint)"
F2="$(printf '%s\n✢ Deploying… (58m 40s · ↓ 77.8k tokens · esc to interrupt)' "$BODY" | bash "$SF" --fingerprint)"
eq "frozen body, only timer/tokens changed → SAME fingerprint (hang detectable)" "$F1" "$F2"
F3="$(printf '⏺ NEW: found the bug, editing publish_finish.sh now\n✢ Deploying… (59m · esc to interrupt)' | bash "$SF" --fingerprint)"
ne "real new text → DIFFERENT fingerprint (progress)" "$F1" "$F3"

echo "(D) FIND-032 past-ceiling continue-vs-kill decision (sf_should_continue)"
dec(){ bash "$SF" --should-continue "$1" "$2" "$3" >/dev/null 2>&1 && echo CONTINUE || echo KILL; }
a "generating + fingerprint advanced → CONTINUE" "$(dec 1 hashA hashB)" 'CONTINUE'
a "generating + fingerprint FROZEN → KILL (hung)" "$(dec 1 hashA hashA)" 'KILL'
a "not generating (idle/errored) → KILL" "$(dec 0 hashA hashB)" 'KILL'
a "first check (prev=none) generating → CONTINUE" "$(dec 1 hashA none)" 'CONTINUE'

echo "(C) FIND-026/031 real lock acquire/steal via hc_acquire_lock"
source "$H/healthcheck-lib.sh"; now=$(date +%s)
D="$(mktemp -d)"; LK="$D/.lk"
hc_acquire_lock "$LK" "$now" && { echo "  ok acquire when no lock"; P=$((P+1)); } || { echo "  FAIL acquire when free"; F=$((F+1)); }
# now a FRESH lock exists (just made) → a second acquire must REFUSE
hc_acquire_lock "$LK" "$now" && { echo "  FAIL acquired a fresh held lock"; F=$((F+1)); } || { echo "  ok refuse fresh held lock"; P=$((P+1)); }
# simulate a hard-killed run: NON-EMPTY stale lock (owner file, old mtime) → must be STOLEN (FIND-026)
rm -rf "$LK"; mkdir "$LK"; echo 88 > "$LK/owner"; touch -t 202607010000 "$LK"
hc_acquire_lock "$LK" "$now" && { echo "  ok steal NON-EMPTY stale lock (rm -rf recovery)"; P=$((P+1)); } || { echo "  FAIL could not steal non-empty stale lock"; F=$((F+1)); }
rm -rf "$D"

echo "(E) A18 budget preflight — ANICCA_BUDGET_REQUIRED=1 without the scope/pass/daily trio must ABORT before spawn"
D2="$(mktemp -d)"
out="$(HOME="$D2" SELF_FIX_NO_ALERT=1 ANICCA_BUDGET_REQUIRED=1 ANICCA_BUDGET_SCOPE_ID= ANICCA_PASS_TOKEN_BUDGET= ANICCA_LOOP_DAILY_TOKEN_BUDGET= SELF_FIX_DRYRUN=1 bash "$SF" gig hint 2>&1)"; rc=$?
[ "$rc" -ne 0 ] && { echo "  ok incomplete trio → nonzero exit ($rc)"; P=$((P+1)); } || { echo "  FAIL incomplete trio did not abort"; F=$((F+1)); }
a "abort message names the failure class" "$out" 'PREFLIGHT ABORT'
a "abort logged to the loop's self-fix log" "$(cat "$D2/.openclaw/logs/self-fix-gig-loop.log" 2>/dev/null)" 'PREFLIGHT ABORT'
out="$(HOME="$D2" SELF_FIX_NO_ALERT=1 ANICCA_BUDGET_REQUIRED=1 ANICCA_BUDGET_SCOPE_ID=selffix-test ANICCA_PASS_TOKEN_BUDGET=65536 ANICCA_LOOP_DAILY_TOKEN_BUDGET=262144 SELF_FIX_DRYRUN=1 bash "$SF" gig hint 2>&1)"; rc=$?
[ "$rc" -eq 0 ] && { echo "  ok complete trio → preflight passes"; P=$((P+1)); } || { echo "  FAIL complete trio aborted: $out"; F=$((F+1)); }
a "complete trio reaches the dryrun seam" "$out" 'LOOP=gig-loop'
out="$(HOME="$D2" SELF_FIX_NO_ALERT=1 SELF_FIX_DRYRUN=1 bash "$SF" gig hint 2>&1)"; rc=$?
[ "$rc" -eq 0 ] && { echo "  ok REQUIRED unset → budget-less caller unaffected"; P=$((P+1)); } || { echo "  FAIL budget-less caller aborted: $out"; F=$((F+1)); }
rm -rf "$D2"

echo "=== self-fix: $P passed $F failed ==="; [ "$F" = 0 ]&&echo GREEN||exit 1
