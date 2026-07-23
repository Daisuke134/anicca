#!/usr/bin/env bash
# cdp_daily_driver_guard.sh — deterministic health-check + auto-recover for the SHARED CloakBrowser
# daily-driver (CDP :9222). Root-caused 2026-07-13: after many hours of continuous automation (gig
# core B1/B2 passes + hourly reality-verifier + other loops), the daily-driver's tabs/renderer
# processes accumulate (observed: 100+ chromium helper processes, several pinned at 20-98% CPU) until
# the root Chromium process is so starved it stops even ACCEPTING new TCP connections on its own
# LISTEN socket (confirmed: `lsof -iTCP:9222 -sTCP:LISTEN` shows it bound, but `curl`/raw `nc` connects
# time out at the TCP handshake — not an HTTP-level error, a kernel-accept-queue-never-drained one).
# Every downstream reality-verify round then fails with evidence_captured=0 (CDP unreachable), which
# is indistinguishable from a stale/wrong claim unless you look at the raw judge output — so gig
# claims "look unconfirmed" for an infra reason, not a grounding-discipline reason.
#
# This is deterministic infra bookkeeping (process health + restart), not judgment — no site/DOM
# decision is made here (mirrors cdp_lock.sh's existing precedent for infra-only bash in this dir).
#
# Usage: source this file, then call: cdp_guard_ensure_healthy [probe_timeout_secs] [relaunch_wait_secs]
#   Returns 0 if the daily-driver answers /json/version by the time it returns (healthy, or
#   successfully recovered). Returns 1 only if a relaunch was attempted and it STILL doesn't answer
#   (caller should treat this round as a genuine defer/fail, not retry-loop forever).
set -uo pipefail

CDP_PORT="${CDP_DAILY_DRIVER_PORT:-9222}"
CDP_PROFILE="${CDP_DAILY_DRIVER_PROFILE:-$HOME/.cloak/profiles/daily-driver}"
CDP_GUARD_LOCK="${CDP_GUARD_LOCK:-$HOME/gig/.cdp-guard.lock}"
CDP_GUARD_LOG="${CDP_GUARD_LOG:-$HOME/.openclaw/logs/cdp-daily-driver-guard.log}"
CDP_GUARD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CDP_OWNER_LABEL="${CDP_OWNER_LABEL:-ai.anicca.cdp-daily-driver-owner}"
mkdir -p "$(dirname "$CDP_GUARD_LOG")" 2>/dev/null || true

_cdp_guard_log() { echo "$(date '+%F %T') cdp_guard: $*" >> "$CDP_GUARD_LOG"; }

# Probe /json/version with a hard timeout. Uses python3 (no curl dependency assumption at CDP layer —
# curl itself hangs the same way on a starved accept queue, so a short --max-time is what actually
# distinguishes "healthy" from "starved" here).
_cdp_guard_probe() {
  local timeout="${1:-6}"
  python3 - "$CDP_PORT" "$timeout" <<'PYEOF' 2>/dev/null
import http.client, sys
port, timeout = int(sys.argv[1]), float(sys.argv[2])
for host in ("127.0.0.1", "::1"):
    conn = None
    try:
        conn = http.client.HTTPConnection(host, port, timeout=timeout)
        conn.request("GET", "/json/version")
        response = conn.getresponse()
        response.read(1)
        if response.status == 200:
            sys.exit(0)
    except Exception:
        pass
    finally:
        if conn is not None:
            conn.close()
sys.exit(1)
PYEOF
}

# Find the root chromium process bound to CDP_PORT with the daily-driver profile (never hardcode a
# PID — re-discover it fresh each call, since a prior relaunch changes it).
_cdp_guard_find_pid() {
  ps -ax -o pid=,ppid=,command= 2>/dev/null \
    | awk -v port="--remote-debugging-port=$CDP_PORT" -v profile="--user-data-dir=$CDP_PROFILE" -v type="--type=" \
      'index($0,port) && index($0,profile) && index($0,type)==0 {print $1; exit}'
}

# Chromium leaves these profile-level singleton symlinks behind when its root process dies
# uncleanly. A later launch then exits immediately with "existing browser session" even though no
# process owns this profile. Call this only after the matching profile process and helpers are gone.
_cdp_guard_clear_stale_profile_artifacts() {
  local live_pid
  live_pid="$(_cdp_guard_find_pid)"
  if [ -n "$live_pid" ] && kill -0 "$live_pid" 2>/dev/null; then
    _cdp_guard_log "refusing singleton cleanup: daily-driver profile still owned by pid=$live_pid"
    return 1
  fi
  rm -f "$CDP_PROFILE/SingletonLock" "$CDP_PROFILE/SingletonSocket" "$CDP_PROFILE/SingletonCookie"
  _cdp_guard_log "cleared stale Chromium singleton artifacts for profile=$CDP_PROFILE"
}

# Relaunch through a managed persistent-context owner. A raw headed Chromium process can answer the
# initial probe and then exit when its creating job ends; the launchd-owned Python process keeps the
# Playwright context and browser alive across verifier/auditor process exits.
_cdp_guard_relaunch() {
  local cloak_python keepalive_script
  cloak_python="$HOME/.openclaw/skills/_shared/venv-cloak/bin/python3"
  keepalive_script="$CDP_GUARD_DIR/cdp_daily_driver_keepalive.py"
  if [ ! -x "$cloak_python" ] || [ ! -f "$keepalive_script" ]; then
    _cdp_guard_log "relaunch FAILED: CloakBrowser runtime or persistent owner script missing"
    return 1
  fi
  mkdir -p "$CDP_PROFILE" 2>/dev/null || true
  launchctl remove "$CDP_OWNER_LABEL" 2>/dev/null || true
  if ! launchctl submit -l "$CDP_OWNER_LABEL" -o "$CDP_GUARD_LOG" -e "$CDP_GUARD_LOG" -- \
    "$cloak_python" "$keepalive_script" --profile "$CDP_PROFILE" --port "$CDP_PORT"; then
    _cdp_guard_log "relaunch FAILED: launchctl could not submit $CDP_OWNER_LABEL"
    return 1
  fi
  _cdp_guard_log "relaunched daily-driver persistent context owner via launchctl label=$CDP_OWNER_LABEL"
}

# macOS ships bash 3.2 (no `trap ... RETURN` support — it silently errors "undefined signal: RETURN"
# and the trap never fires, which would leak CDP_GUARD_LOCK forever on every non-fallthrough return).
# So the locked recovery body is a separate function and the public entry point below always rmdir's
# the lock itself after calling it, on every path, instead of relying on a return trap.
_cdp_guard_recover_locked() {
  local probe_timeout="$1" relaunch_wait="$2"

  # re-probe once more now that we hold the lock (another caller may have JUST fixed it)
  if _cdp_guard_probe "$probe_timeout"; then
    _cdp_guard_log "recovered before we acted"
    return 0
  fi

  local pid; pid="$(_cdp_guard_find_pid)"
  if [ -n "$pid" ]; then
    _cdp_guard_log "killing starved daily-driver root pid=$pid (profile=$CDP_PROFILE) — cookies/session persist to disk, login survives restart"
    kill -TERM "$pid" 2>/dev/null || true
    local killed_wait=0
    while [ "$killed_wait" -lt 15 ] && kill -0 "$pid" 2>/dev/null; do sleep 1; killed_wait=$((killed_wait + 1)); done
    kill -0 "$pid" 2>/dev/null && kill -KILL "$pid" 2>/dev/null || true
  else
    _cdp_guard_log "no root chromium pid found bound to :$CDP_PORT + profile=$CDP_PROFILE — may already be dead; proceeding to relaunch"
  fi
  # reap any orphaned helper processes left behind under the same profile (renderer/gpu/utility
  # children reparented to launchd after SIGKILL of the root, which otherwise keep the fds/CPU pinned)
  pkill -9 -f "user-data-dir=$CDP_PROFILE" 2>/dev/null || true
  sleep 2

  _cdp_guard_clear_stale_profile_artifacts || return 1
  _cdp_guard_relaunch || return 1

  local waited=0
  while [ "$waited" -lt "$relaunch_wait" ]; do
    _cdp_guard_probe "$probe_timeout" && { _cdp_guard_log "RECOVERED: :$CDP_PORT healthy after relaunch (${waited}s)"; return 0; }
    sleep 3; waited=$((waited + 3))
  done
  _cdp_guard_log "relaunch did not become healthy within ${relaunch_wait}s"
  return 1
}

cdp_guard_ensure_healthy() {
  local probe_timeout="${1:-6}" relaunch_wait="${2:-45}"

  if _cdp_guard_probe "$probe_timeout"; then
    return 0   # healthy — cheap no-op path, the common case
  fi
  _cdp_guard_log "UNHEALTHY: :$CDP_PORT did not answer /json/version within ${probe_timeout}s"

  # advisory lock so concurrent callers (gig verifier + core + other loops sharing :9222) don't
  # each independently kill+relaunch at once
  mkdir -p "$(dirname "$CDP_GUARD_LOCK")" 2>/dev/null || true
  if ! mkdir "$CDP_GUARD_LOCK" 2>/dev/null; then
    _cdp_guard_log "another caller is already recovering — waiting up to ${relaunch_wait}s"
    local waited=0
    while [ "$waited" -lt "$relaunch_wait" ]; do
      sleep 3; waited=$((waited + 3))
      _cdp_guard_probe "$probe_timeout" && { _cdp_guard_log "recovered by other caller"; return 0; }
    done
    return 1
  fi

  local rc
  _cdp_guard_recover_locked "$probe_timeout" "$relaunch_wait"; rc=$?
  rmdir "$CDP_GUARD_LOCK" 2>/dev/null || true
  return "$rc"
}
