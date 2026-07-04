#!/usr/bin/env bash
# test-self-fix.sh — FIND-028: cover the two mechanisms re-patched in rounds 4-5.
# (A) FIND-025 loop-name normalization: 'capafy' and 'capafy-loop' MUST resolve to ONE session + ONE marker.
# (B) FIND-026 stale-lock recovery: a NON-EMPTY stale lock (owner file present) MUST be removable by the steal path
#     (rm -rf), where the old rmdir would have failed → permanent self-heal death.
set -uo pipefail; P=0; F=0; H="$(cd "$(dirname "${BASH_SOURCE[0]}")"&&pwd)"; SF="$H/self-fix.sh"
a(){ echo "$2"|grep -qF "$3"&&{ echo "  ok $1"; P=$((P+1)); }||{ echo "  FAIL $1 want:[$3] got:[$2]"; F=$((F+1)); }; }

echo "(A) normalization — short vs long form converge"
S="$(SELF_FIX_DRYRUN=1 bash "$SF" capafy hint 2>&1)"
L="$(SELF_FIX_DRYRUN=1 bash "$SF" capafy-loop hint 2>&1)"
a "short 'capafy' → LOOP=capafy-loop" "$S" 'LOOP=capafy-loop'
a "short 'capafy' → SESSION=anicca-selffix-capafy-loop" "$S" 'SESSION=anicca-selffix-capafy-loop'
a "short 'capafy' → RESULT=.self-fix-capafy-loop.result" "$S" '.self-fix-capafy-loop.result'
a "long 'capafy-loop' identical SESSION" "$L" 'SESSION=anicca-selffix-capafy-loop'
[ "$S" = "$L" ] && { echo "  ok short==long fully identical"; P=$((P+1)); } || { echo "  FAIL short!=long"; F=$((F+1)); }
a "life-manager short → life-manager-loop" "$(SELF_FIX_DRYRUN=1 bash "$SF" life-manager h 2>&1)" 'LOOP=life-manager-loop'

echo "(B) stale-lock recovery — non-empty lock must be steal-able (rm -rf, not rmdir)"
LOCK="$(mktemp -d)/.lk"; mkdir "$LOCK"; echo 99999 > "$LOCK/owner"   # simulate a hard-killed run's non-empty lock
rmdir "$LOCK" 2>/dev/null && { echo "  FAIL test premise: rmdir removed a non-empty dir?!"; F=$((F+1)); } || { echo "  ok premise: rmdir CANNOT remove non-empty lock (the old bug)"; P=$((P+1)); }
rm -rf "$LOCK" 2>/dev/null; [ ! -d "$LOCK" ] && { echo "  ok rm -rf removes non-empty stale lock (the fix)"; P=$((P+1)); } || { echo "  FAIL rm -rf left lock"; F=$((F+1)); }
grep -q 'rm -rf "$LOCK_DIR" 2>/dev/null||true' "$H/healthcheck-lib.sh" && { echo "  ok healthcheck-lib steal path uses rm -rf"; P=$((P+1)); } || { echo "  FAIL steal path not rm -rf"; F=$((F+1)); }

echo "=== self-fix: $P passed $F failed ==="; [ "$F" = 0 ]&&echo GREEN||exit 1
