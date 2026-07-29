#!/usr/bin/env bash
# test-loop-report.sh — RED (Phase 2a, feature claude-p-loop-verification).
# PROP-LV-001 (Tier1, lr_valid_evidence 4-way split) + PROP-LV-002 (Tier2, AGENTMAIL_API_KEY
# self-resolve, REQ-LV-001/002) + REQ-LV-003 (Tier2, evidence gate exit 1 on empty/bare-none).
# Mirrors this codebase's own convention: a `--<flag>` entrypoint lets a pure predicate be called
# directly without spawning the full script (see self-fix.sh::sf_should_continue --should-continue,
# healthcheck-runtime-loop.sh::hrl_classify --classify).
#
# lr_valid_evidence does NOT exist yet in loop-report.sh -> Tier1 section FAILS (unknown flag).
# The evidence gate / self-resolve do not exist yet either -> Tier2 sections FAIL (script still
# unconditionally NO-OPs on unset AGENTMAIL_API_KEY, still accepts "" / "none" without rejecting).
set -uo pipefail; P=0; F=0
H="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
A="$H/loop-report.sh"

ok(){ echo "  ok $1"; P=$((P+1)); }
fail(){ echo "  FAIL $1"; F=$((F+1)); }

echo "--- Tier1: lr_valid_evidence (PROP-LV-001) ---"
# lr_valid_evidence <evidence_url> -> exit 0 (valid/accept) | exit 1 (invalid/reject)
chk_valid(){
  local name="$1" input="$2" want_rc="$3"
  bash "$A" --valid-evidence "$input" >/dev/null 2>&1
  local got_rc=$?
  [ "$got_rc" = "$want_rc" ] && ok "$name (rc=$got_rc)" || fail "$name want_rc=$want_rc got_rc=$got_rc"
}
chk_valid "empty string -> reject"                  ""                  1
chk_valid "bare 'none' -> reject"                    "none"              1
chk_valid "bare 'NONE' case-insensitive -> reject"   "NONE"              1
chk_valid "'  none  ' whitespace-only -> reject"     "  none  "          1
chk_valid "'none: queue empty' -> accept"            "none: queue empty" 0
chk_valid "'none:x' minimal reason -> accept"        "none:x"            0
chk_valid "real URL -> accept"                       "https://www.instagram.com/reel/ABC123/" 0

echo "--- Tier2: REQ-LV-003 evidence gate (empty/bare-none -> exit 1, REJECTED in log) ---"
LOG="$HOME/.local/state/life-manager/logs/loop-report.log"
gate_case(){
  local name="$1" evidence="$2" want_rc="$3"
  : > "$LOG" 2>/dev/null || mkdir -p "$(dirname "$LOG")"
  env -u AGENTMAIL_API_KEY bash "$A" test-loop "did-summary" success 0 "$evidence" >/dev/null 2>&1
  local got_rc=$?
  [ "$got_rc" = "$want_rc" ] && ok "$name rc (rc=$got_rc)" || fail "$name rc want=$want_rc got=$got_rc"
}
gate_case "empty evidence -> exit 1"      ""                  1
gate_case "bare 'none' -> exit 1"         "none"              1
gate_case "'none: reason' -> NOT exit1"   "none: queue empty" 0
gate_case "real URL -> NOT exit1"         "https://example.com/x" 0

: > "$LOG" 2>/dev/null
env -u AGENTMAIL_API_KEY bash "$A" test-loop "did" success 0 "" >/dev/null 2>&1
grep -q "REJECTED (empty-or-bare-none evidence)" "$LOG" 2>/dev/null && ok "empty evidence logs REJECTED" || fail "empty evidence should log REJECTED"

: > "$LOG" 2>/dev/null
env -u AGENTMAIL_API_KEY bash "$A" test-loop "did" success 0 "none" >/dev/null 2>&1
grep -q "REJECTED (empty-or-bare-none evidence)" "$LOG" 2>/dev/null && ok "bare-none evidence logs REJECTED" || fail "bare-none evidence should log REJECTED"

echo "--- Tier2: REQ-LV-001/002 AGENTMAIL_API_KEY self-resolve ---"
FAKE_HOME_WITH_KEY="$(mktemp -d)"
mkdir -p "$FAKE_HOME_WITH_KEY/.openclaw/logs" "$FAKE_HOME_WITH_KEY/.openclaw"
printf 'AGENTMAIL_API_KEY=test-fake-key-not-real\n' > "$FAKE_HOME_WITH_KEY/.openclaw/.env"
env -u AGENTMAIL_API_KEY HOME="$FAKE_HOME_WITH_KEY" bash "$A" test-loop "did" success 0 "none: reason" >/dev/null 2>&1
FAKE_LOG="$FAKE_HOME_WITH_KEY/.openclaw/logs/loop-report.log"
if [ -f "$FAKE_LOG" ] && ! grep -q "NO-OP (AGENTMAIL_API_KEY unset)" "$FAKE_LOG"; then
  ok "self-resolve: key present in .env -> NOT NO-OP (attempted send)"
else
  fail "self-resolve: key present in .env should NOT log NO-OP, got: $(cat "$FAKE_LOG" 2>/dev/null)"
fi
rm -rf "$FAKE_HOME_WITH_KEY"

FAKE_HOME_NO_KEY="$(mktemp -d)"
mkdir -p "$FAKE_HOME_NO_KEY/.openclaw/logs"
env -u AGENTMAIL_API_KEY HOME="$FAKE_HOME_NO_KEY" bash "$A" test-loop "did" success 0 "none: reason" >/dev/null 2>&1
FAKE_LOG2="$FAKE_HOME_NO_KEY/.openclaw/logs/loop-report.log"
if [ -f "$FAKE_LOG2" ] && grep -q "NO-OP (AGENTMAIL_API_KEY unset)" "$FAKE_LOG2"; then
  ok "no .env / no key -> still NO-OP + exit 0 (fail-closed unchanged, regression guard)"
else
  fail "no .env / no key should still NO-OP: $(cat "$FAKE_LOG2" 2>/dev/null)"
fi
rm -rf "$FAKE_HOME_NO_KEY"

echo "=== test-loop-report: $P passed $F failed ==="; [ "$F" = 0 ] && echo GREEN || exit 1
