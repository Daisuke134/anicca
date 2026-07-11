#!/usr/bin/env bash
# test-reality-verify-spawn.sh — VCSDD Phase 2a (RED) / PROP-008.
# Mirrors skills/self/test-self-fix.sh's DRYRUN-seam test pattern: exercise the pure
# path-derivation logic of reality-verify-spawn.sh WITHOUT spawning any process.
# Spec: .vcsdd/features/reality-verifier/specs/behavioral-spec.md REQ-008.
set -uo pipefail; P=0; F=0
H="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RV="$H/../reality-verify-spawn.sh"

a(){ echo "$2" | grep -qF "$3" && { echo "  ok $1"; P=$((P+1)); } || { echo "  FAIL $1 want:[$3] got:[$2]"; F=$((F+1)); }; }
eq(){ [ "$2" = "$3" ] && { echo "  ok $1"; P=$((P+1)); } || { echo "  FAIL $1 ($2 vs $3)"; F=$((F+1)); }; }

echo "(A) missing arguments -> non-zero exit, nothing spawned"
bash "$RV" >/dev/null 2>&1; rc=$?
[ "$rc" != "0" ] && { echo "  ok no-args -> non-zero exit ($rc)"; P=$((P+1)); } || { echo "  FAIL no-args should be non-zero exit"; F=$((F+1)); }

bash "$RV" onlyloop >/dev/null 2>&1; rc=$?
[ "$rc" != "0" ] && { echo "  ok missing artifact path -> non-zero exit ($rc)"; P=$((P+1)); } || { echo "  FAIL missing-artifact-path should be non-zero exit"; F=$((F+1)); }

echo "(B) REALITY_VERIFY_DRYRUN=1 -> deterministic path derivation, no process spawned"
S="$(REALITY_VERIFY_DRYRUN=1 bash "$RV" capafy /tmp/some-report.json 2>&1)"
L="$(REALITY_VERIFY_DRYRUN=1 bash "$RV" capafy-loop /tmp/some-report.json 2>&1)"
a "short 'capafy' -> LOOP=capafy-loop" "$S" 'LOOP=capafy-loop'
a "dryrun output references RESULT path" "$S" 'RESULT='
eq "short==long identical (loop-name normalization parity)" "$S" "$L"

echo "(C) dryrun never spawns a tmux session"
SESS_BEFORE="$(tmux list-sessions 2>/dev/null | wc -l | tr -d ' ')"
REALITY_VERIFY_DRYRUN=1 bash "$RV" test-dryrun-noop /tmp/x.json >/dev/null 2>&1
SESS_AFTER="$(tmux list-sessions 2>/dev/null | wc -l | tr -d ' ')"
eq "tmux session count unchanged after dryrun call" "$SESS_BEFORE" "$SESS_AFTER"

echo "=== test-reality-verify-spawn: $P passed $F failed ==="; [ "$F" = 0 ] && echo GREEN || exit 1
