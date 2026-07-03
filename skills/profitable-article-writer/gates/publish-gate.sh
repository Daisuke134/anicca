#!/usr/bin/env bash
# gates/publish-gate.sh — fail-closed publish wiring (REQ-5, REQ-7, REQ-14; PROP-5).
#
# Contract: publish is called IF AND ONLY IF gates/v0.sh AND gates/v05.sh BOTH return PASS. A FAIL from
# EITHER gate means publish is NEVER called (fail-closed).
#
# This gate is SINGLE-ROUND: it wires exactly one V0+V0.5 check to exactly one publish attempt. The
# multi-round ceiling (REQ-14: <=3 fix+re-gate rounds, then ABORT + record the failure) is owned by
# run.sh, which calls gates/v0.sh and gates/v05.sh directly per round and only calls this gate once a
# round has BOTH-PASSed (Mode B) — so this file never needs to know about round counting.
#
# INTERFACE:
#   arg1:    path to the draft artifact
#   env in:  ARTICLE_DIR (state dir)
#   env in:  ARTICLE_TEST_FORCE_V0 / ARTICLE_TEST_FORCE_V05 (test-injection: PASS|FAIL, single round)
#   writes:  $ARTICLE_DIR/state/PUBLISHED  sentinel — created ONLY on a successful publish call
#   exit:    0 = published; 1 = not published (fail-closed); NEVER a partial state
set -uo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRAFT="${1:-}"
ARTICLE_DIR="${ARTICLE_DIR:-}"

if [ -z "$ARTICLE_DIR" ]; then
  echo "publish-gate: ARTICLE_DIR is required" >&2
  exit 1
fi

mkdir -p "$ARTICLE_DIR/state"

v0_out="$(bash "$SELF_DIR/v0.sh" "$DRAFT" 2>&1)"; v0_rc=$?
v05_out="$(bash "$SELF_DIR/v05.sh" "$DRAFT" 2>&1)"; v05_rc=$?

echo "$v0_out"
echo "$v05_out"

if [ $v0_rc -ne 0 ] || [ $v05_rc -ne 0 ]; then
  echo "PUBLISH_GATE: FAIL (v0_rc=$v0_rc v05_rc=$v05_rc) — publish NEVER called"
  exit 1
fi

# BOTH-PASS: this is the ONLY path that publishes (fail-closed). Real per-rail publish (note/Substack/X/
# Zenn/dev.to) is the Sprint 2 live-integration seam; here the deterministic, verifiable side-effect is
# the atomic publish sentinel that downstream distribution/verify steps key off of.
tmp="$(mktemp "$ARTICLE_DIR/state/.PUBLISHED.XXXXXX")"
printf 'draft: %s\npublished_at: %s\n' "$DRAFT" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$tmp"
mv "$tmp" "$ARTICLE_DIR/state/PUBLISHED"
echo "PUBLISH_GATE: PASS — published"
exit 0
