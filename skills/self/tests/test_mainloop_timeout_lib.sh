#!/usr/bin/env bash
# test_mainloop_timeout_lib.sh — proves resolve_mainloop_timeout_sec() (mainloop-timeout-lib.sh)
# never regresses to the old 3600s ceiling that killed 3 of the last 6 claude-p-mainloop fires
# (exit status=124, see MAINLOOP-LOG.md / claude-p-mainloop.out.log 2026-07-10/11) and never
# exceeds the plist's 21600s StartInterval (no racing the next scheduled fire).
set -uo pipefail; P=0; F=0
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/mainloop-timeout-lib.sh"

chk() {
  local name="$1" want="$2" got="$3"
  if [ "$got" = "$want" ]; then
    echo "  ok $name ($got)"; P=$((P+1))
  else
    echo "  FAIL $name want=$want got=$got"; F=$((F+1))
  fi
}

is_gt_3600() { [ "$1" -gt 3600 ] && echo TRUE || echo FALSE; }
is_lt_21600() { [ "$1" -lt 21600 ] && echo TRUE || echo FALSE; }

unset CLAUDE_P_MAINLOOP_TIMEOUT_SEC
DEFAULT_VAL="$(resolve_mainloop_timeout_sec)"
chk "default is above old 3600s ceiling" TRUE "$(is_gt_3600 "$DEFAULT_VAL")"
chk "default stays below 21600s StartInterval (buffer for next fire)" TRUE "$(is_lt_21600 "$DEFAULT_VAL")"

export CLAUDE_P_MAINLOOP_TIMEOUT_SEC=7200
chk "valid env override is honored exactly" 7200 "$(resolve_mainloop_timeout_sec)"

export CLAUDE_P_MAINLOOP_TIMEOUT_SEC="not-a-number"
chk "non-numeric override falls back above old ceiling" TRUE "$(is_gt_3600 "$(resolve_mainloop_timeout_sec)")"

export CLAUDE_P_MAINLOOP_TIMEOUT_SEC="0"
chk "zero override falls back above old ceiling" TRUE "$(is_gt_3600 "$(resolve_mainloop_timeout_sec)")"

export CLAUDE_P_MAINLOOP_TIMEOUT_SEC="-100"
chk "negative override falls back above old ceiling" TRUE "$(is_gt_3600 "$(resolve_mainloop_timeout_sec)")"

export CLAUDE_P_MAINLOOP_TIMEOUT_SEC="3600.5"
chk "non-integer decimal override falls back above old ceiling" TRUE "$(is_gt_3600 "$(resolve_mainloop_timeout_sec)")"

unset CLAUDE_P_MAINLOOP_TIMEOUT_SEC

echo "PASS=$P FAIL=$F"
[ "$F" -eq 0 ]
