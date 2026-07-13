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

echo "(D) REQ-005: new-argument threading with defaults (claim-type/required-count/claimed-urls), backward compatible"
D1="$(REALITY_VERIFY_DRYRUN=1 bash "$RV" capafy /tmp/some-report.json 2>&1)"
a "old-style 3-arg call defaults CLAIM_TYPE=none (backward compatible)" "$D1" 'CLAIM_TYPE=none'
a "old-style 3-arg call defaults REQUIRED_COUNT=1" "$D1" 'REQUIRED_COUNT=1'
D2="$(REALITY_VERIFY_DRYRUN=1 bash "$RV" capafy https://example.com/posts/1 claim public-artifact 2>&1)"
a "explicit claim-type threads through" "$D2" 'CLAIM_TYPE=public-artifact'
a "URL-shaped artifact defaults into CLAIMED_URLS when none given" "$D2" 'CLAIMED_URLS=https://example.com/posts/1'
D3="$(REALITY_VERIFY_DRYRUN=1 bash "$RV" capafy not-a-url claim garbage-claim-type 2>&1)"
a "unrecognized claim-type -> generic 'none' handling" "$D3" 'CLAIM_TYPE=none'

echo "(E) REQ-005 edge case: public-artifact claim-type with no URL anywhere -> refuse to spawn (non-zero, no PASS_ID generated)"
bash "$RV" capafy not-a-url claim public-artifact >/dev/null 2>&1; rc=$?
[ "$rc" != "0" ] && { echo "  ok refuses to spawn -> non-zero exit ($rc)"; P=$((P+1)); } || { echo "  FAIL should refuse to spawn"; F=$((F+1)); }

echo "(F) PROP-042/FIND-N/Q: passId is generated INTERNALLY, CSPRNG-shaped, and external injection is never honored"
PID_A="$(REALITY_VERIFY_PASSID_DEBUG=1 bash "$RV" capafy /tmp/some-report.json 2>&1)"
PID_B="$(REALITY_VERIFY_PASSID_DEBUG=1 bash "$RV" capafy /tmp/some-report.json 2>&1)"
a "PASSID_DEBUG output has the PASS_ID= shape" "$PID_A" 'PASS_ID=realityverify-'
[ "$PID_A" != "$PID_B" ] && { echo "  ok two calls generate DIFFERENT passIds (CSPRNG, not deterministic)"; P=$((P+1)); } || { echo "  FAIL passId must differ across calls"; F=$((F+1)); }
# Channel 1: env var named PASS_ID
PID_ENV="$(PASS_ID=attacker-chosen-passid REALITY_VERIFY_PASSID_DEBUG=1 bash "$RV" capafy /tmp/some-report.json 2>&1)"
a "env var PASS_ID=attacker-chosen-passid is NEVER honored" "$PID_ENV" 'PASS_ID=realityverify-'
case "$PID_ENV" in *attacker-chosen-passid*) echo "  FAIL env-injected passId leaked into output"; F=$((F+1));; *) echo "  ok env-injected value absent from output"; P=$((P+1));; esac
# Channel 2: a stray extra positional argument in the (removed) old pass-id slot
PID_ARG="$(REALITY_VERIFY_PASSID_DEBUG=1 bash "$RV" capafy /tmp/some-report.json claim public-artifact 1 "" "" "" "attacker-chosen-positional" 2>&1)"
case "$PID_ARG" in *attacker-chosen-positional*) echo "  FAIL positional-arg-injected passId leaked into output"; F=$((F+1));; *) echo "  ok positional-arg-injected value absent from output"; P=$((P+1));; esac
# grep-level proof: no code path reads an externally-supplied value into PASS_ID
NAIVE_ASSIGN=$(grep -nE 'PASS_ID=("\$1"|"\$2"|"\$3"|"\$4"|"\$5"|"\$6"|"\$7"|"\$8"|"\$9"|"\$PASS_ID"|"\$\{PASS_ID)' "$RV" || true)
[ -z "$NAIVE_ASSIGN" ] && { echo "  ok no code path assigns an external value directly into PASS_ID"; P=$((P+1)); } || { echo "  FAIL found external->PASS_ID assignment: $NAIVE_ASSIGN"; F=$((F+1)); }

echo "(G) REQ-010/018 routing: FAIL and self-fix.sh are wired; the CANNOT_VERIFY human-review-queue path is a DISTINCT branch"
a "script literally invokes self-fix.sh" "$(cat "$RV")" 'self-fix.sh'
a "script routes on escalateSelfFix (shared with the CANNOT_VERIFY streak decision, REQ-018)" "$(cat "$RV")" 'ESCALATE'
a "script threads reality-enforce-cli.mjs (the ONE shared enforceVerdict caller)" "$(cat "$RV")" 'reality-enforce-cli.mjs'

echo "=== test-reality-verify-spawn: $P passed $F failed ==="; [ "$F" = 0 ] && echo GREEN || exit 1
