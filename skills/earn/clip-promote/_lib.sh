#!/usr/bin/env bash
# _lib.sh — sourceable slot helpers for earn/clip-promote (so run.sh AND the unit tests share the
# EXACT same emit / watchdog / fail-closed logic). Pure shell; no side effects on source.
# Expects $PY to be set by the caller (falls back to python3).
: "${PY:=python3}"

# ── portable timeout (FIND-302): GNU `timeout` or coreutils `gtimeout`; else a pure SIGTERM fallback. ──
TIMEOUT_BIN="$(command -v timeout || command -v gtimeout || true)"

run_step() { # run_step <deadline_s> <cmd...> ; returns 124 on timeout (mirrors coreutils)
  local d="$1"; shift
  if [ -n "$TIMEOUT_BIN" ]; then
    "$TIMEOUT_BIN" "$d" "$@"; return $?
  fi
  ( "$@" ) & local pid=$!
  ( sleep "$d"; kill -TERM "$pid" 2>/dev/null; sleep 2; kill -KILL "$pid" 2>/dev/null ) & local wd=$!
  if wait "$pid" 2>/dev/null; then kill -TERM "$wd" 2>/dev/null; return 0; fi
  local rc=$?; kill -TERM "$wd" 2>/dev/null
  [ "$rc" -ge 128 ] && return 124 || return "$rc"
}

emit() { # emit <did> [earned_usdc] [cost_usdc] — the ONE structured slot line
  "$PY" - "$1" "${2:-0}" "${3:-0}" <<'PYE'
import json,sys
print(json.dumps({"slot":"earn/clip-promote","did":sys.argv[1],
                  "earned_usdc":float(sys.argv[2]),"cost_usdc":float(sys.argv[3])}))
PYE
}

# fail-closed guard on a step's exit code: 124 ⇒ blocked:human (no hang, no human wait) + exit 0;
# any other non-zero ⇒ narrate <msg> + exit 0. exit 0 on a profitable/zero wake is the slot contract.
blocked_or() { # blocked_or <step-name> <rc> <narrate-msg-on-nonzero>
  local step="$1" rc="$2" msg="$3"
  if [ "$rc" -eq 124 ]; then emit "blocked:human:$step"; exit 0; fi
  if [ "$rc" -ne 0 ]; then emit "$msg"; exit 0; fi
}
