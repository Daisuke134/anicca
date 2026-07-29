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

_promote_tab_lookup() { # _promote_tab_lookup <port> -> tab id or empty
  local port="$1"
  curl -sS --max-time 5 "http://localhost:$port/json/list" 2>/dev/null | "$PY" -c "import json,sys
try: d=json.load(sys.stdin)
except Exception: d=[]
print(next((t['id'] for t in d if t.get('type')=='page' and 'promote.fun' in (t.get('url') or '')),''))" 2>/dev/null
}

find_promote_tab() { # find_promote_tab <port> -> prints tab id (empty if truly unavailable)
  local port="$1" tid
  tid="$(_promote_tab_lookup "$port")"
  [ -n "$tid" ] && { echo "$tid"; return 0; }
  # No tab found. Root cause proven 2026-07-06: the dedicated CDP browser on this port is a
  # bare `nohup` process with no supervisor (unlike the tmux-supervised core loop) -- a
  # resource-exhaustion incident (or any crash) silently kills it and nothing restarts it, so
  # the same "no-promote-tab" blocker recurs every wake until an agent manually relaunches it.
  # Relaunch here instead (idempotent: launch_promote_browser.py no-ops if the port is already
  # bound) and retry once after it boots + restores the persisted login session.
  if ! curl -sS --max-time 3 "http://localhost:$port/json/version" >/dev/null 2>&1; then
    nohup $LIFE_MANAGER_REPO/skills/_shared/venv-cloak/bin/python3 \
      "$HOME/.claude/skills/promote-fun-login/scripts/launch_promote_browser.py" \
      >/tmp/promote-browser.log 2>&1 &
    disown
    sleep 6
  fi
  _promote_tab_lookup "$port"
}
