#!/usr/bin/env bash
# Unit tests for forum-rollout _lib.sh (#338 P15).
set -euo pipefail
DIR="$(cd "$(dirname "$0")/../scripts" && pwd)"
export STATE_DIR="$HOME/.hermes/state/.fr-test-lib.$$"
mkdir -p "$STATE_DIR"; trap 'rm -rf "$STATE_DIR"' EXIT
# shellcheck disable=SC1091
source "$DIR/_lib.sh"
pass=0; fail=0
ok(){ pass=$((pass+1)); echo "  ok: $1"; }
bad(){ fail=$((fail+1)); echo "  FAIL: $1"; }

BLOCK_BODY=$'CONSENSUS: ship it\n\n```rollout\nACTION: architecture-shift\nTARGET: merge-foo-bar\nPAYLOAD: {"reason":"agreed","title":"merge foo+bar"}\n```'
NO_FENCE=$'CONSENSUS: ship it but no block here'
NO_MARKER=$'```rollout\nACTION: edit-skill\nTARGET: daily-report\n```'

blk="$(fr_extract_block "$BLOCK_BODY")" && ok "extract: happy path" || bad "extract: happy path"
fr_extract_block "$NO_FENCE" >/dev/null && bad "extract: no-fence must fail" || ok "extract: no-fence fails"
fr_extract_block "$NO_MARKER" >/dev/null && bad "extract: no-marker must fail" || ok "extract: no-marker fails"

[ "$(fr_field "$blk" ACTION)" = "architecture-shift" ] && ok "field ACTION" || bad "field ACTION ($(fr_field "$blk" ACTION))"
[ "$(fr_field "$blk" TARGET)" = "merge-foo-bar" ] && ok "field TARGET" || bad "field TARGET"
[ "$(fr_payload "$blk" | "$JQ" -r .title)" = "merge foo+bar" ] && ok "payload parse" || bad "payload parse"

s1="$(fr_consensus_sha "CONSENSUS: ship it" "$blk")"
s2="$(fr_consensus_sha "CONSENSUS: ship it" "$blk")"
s3="$(fr_consensus_sha "CONSENSUS: ship it" "different")"
[ "$s1" = "$s2" ] && ok "sha stable" || bad "sha stable"
[ "$s1" != "$s3" ] && ok "sha differs on content" || bad "sha differs"
[ "${#s1}" = "64" ] && ok "sha is 64 hex" || bad "sha len ${#s1}"

fr_hard_no "anicca-wallet" && ok "hard-no: wallet blocked" || bad "hard-no: wallet"
fr_hard_no "eval-loop" && ok "hard-no: eval-loop blocked" || bad "hard-no: eval-loop"
fr_hard_no "forum-rollout" && ok "hard-no: self blocked" || bad "hard-no: self"
fr_hard_no "anicca-constitution-guard" && ok "hard-no: guard blocked" || bad "hard-no: guard"
fr_hard_no "anicca-payout-ubi" && ok "hard-no: payout-ubi blocked" || bad "hard-no: payout-ubi"
fr_hard_no "daily-report" && bad "hard-no: normal skill must pass" || ok "hard-no: normal skill allowed"

av="$(fr_build_argv architecture-shift merge-foo-bar "$(fr_payload "$blk")")"
[ "$(printf '%s' "$av" | "$JQ" -r .type)" = "arch-shift" ] && ok "argv type" || bad "argv type"
[ "$(printf '%s' "$av" | "$JQ" -r .title)" = "merge foo+bar" ] && ok "argv title from payload" || bad "argv title"
av2="$(fr_build_argv edit-skill daily-report '{}')"
[ "$(printf '%s' "$av2" | "$JQ" -r .skill)" = "daily-report" ] && ok "argv edit-skill skill=target" || bad "argv edit-skill"
fr_build_argv bogus x '{}' >/dev/null 2>&1 && bad "argv: unknown action must fail" || ok "argv: unknown action fails"

fr_applied 11 "$s1" && bad "applied: empty=false" || ok "applied: empty false"
fr_log 11 "$s1" architecture-shift merge-foo-bar false 0 dry-run
fr_applied 11 "$s1" && ok "applied: after log=true" || bad "applied: after log"
fr_applied 11 "$s3" && bad "applied: other sha=false" || ok "applied: other sha false"
fr_applied 12 "$s1" && bad "applied: other issue=false" || ok "applied: other issue false"

echo "---"; echo "PASS=$pass FAIL=$fail"; [ "$fail" -eq 0 ]
