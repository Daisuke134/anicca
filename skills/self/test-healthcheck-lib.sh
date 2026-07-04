#!/usr/bin/env bash
# test-healthcheck-lib.sh — FIND-014: prove the stuck-asking detector fires ONLY on idle input-await prompts and
# NEVER on active generation ("esc to interrupt") or healthy idle. Mirrors the exact predicate in healthcheck-lib.sh.
set -uo pipefail; P=0; F=0
# FIND-021: source the REAL predicate from the lib (no duplication → cannot drift).
source "$(cd "$(dirname "${BASH_SOURCE[0]}")"&&pwd)/healthcheck-lib.sh"
chk(){ local name="$1" want="$2" pane="$3"; if hc_is_stuck_pane "$pane"; then got=FIRE; else got=OK; fi
  [ "$got" = "$want" ] && { echo "  ok $name ($got)"; P=$((P+1)); } || { echo "  FAIL $name want=$want got=$got"; F=$((F+1)); }; }

# idle interactive picker (asking a human) → FIRE (restart)
chk "idle picker menu" FIRE '  1. Option A
  2. Option B
Enter to select · ↑/↓ to navigate · Esc to cancel
❯'
# active generation that happens to show a menu-ish word BUT esc-to-interrupt present → must NOT fire
chk "active generation (esc to interrupt)" OK '✻ Brewed for 3m · esc to interrupt
Enter to select something later'
# healthy idle after a pass (just prompt) → NOT fire
chk "healthy idle prompt" OK '⏺ done. touched last-pass.
❯'
# free-text await → FIRE
chk "free-text await" FIRE 'Type something. or use @ to mention
❯'
# confirm dialog → FIRE
chk "confirm dialog" FIRE 'Do you want to proceed?
  1. Yes
  2. No'
# active searching, no prompt → NOT fire
chk "active searching" OK '✢ Searching… (7m · ↓ 19k tokens · esc to interrupt)'

echo "=== healthcheck-lib stall-detect: $P passed $F failed ==="; [ "$F" = 0 ]&&echo GREEN||exit 1
