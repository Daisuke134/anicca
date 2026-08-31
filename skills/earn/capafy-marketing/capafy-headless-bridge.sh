#!/usr/bin/env bash
set -uo pipefail
umask 077

ROOT="${MR_BOT_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$ROOT" ] || exit 2
STATE_HOME="${MR_BOT_STATE_HOME:-$HOME/.local/state/mr-bot}"
STATE="$STATE_HOME/state/capafy-headless-bridge"
LOG="$STATE/bridge.log"
LOCK="$STATE/lock"
PIDFILE="$STATE/owner.pid"
HEARTBEAT="$STATE/heartbeat"
AQUA_SEEN="$STATE/aqua-seen-at"
TIMES="$STATE/timestamps"
INTERVAL="${CAPAFY_HEADLESS_INTERVAL:-60}"
ONCE="${CAPAFY_HEADLESS_ONCE:-0}"
MAX_TICKS="${CAPAFY_HEADLESS_MAX_TICKS:-0}"
AQUA_GRACE="${CAPAFY_HEADLESS_AQUA_GRACE:-180}"
LOCK_GRACE="${CAPAFY_HEADLESS_LOCK_GRACE:-5}"
case "$INTERVAL" in ''|*[!0-9]*) exit 2 ;; esac
case "$MAX_TICKS" in ''|*[!0-9]*) exit 2 ;; esac
case "$AQUA_GRACE" in ''|*[!0-9]*) exit 2 ;; esac
case "$LOCK_GRACE" in ''|*[!0-9]*) exit 2 ;; esac
[ "$INTERVAL" -gt 0 ] || exit 2

now() { printf '%s\n' "${CAPAFY_HEADLESS_NOW:-$(date +%s)}"; }
log() { mkdir -p "$STATE"; chmod 700 "$STATE"; printf '%s %s\n' "$(date '+%F %T')" "$*" >>"$LOG"; chmod 600 "$LOG"; }
release_lock() {
  local lock="$1" owner
  owner="$(cat "$lock/owner.pid" 2>/dev/null || true)"
  [ "$owner" = "$$" ] || return 0
  rm -f "$lock/owner.pid" 2>/dev/null || true
  rmdir "$lock" 2>/dev/null || true
}
run_child() {
  local name="$1" cmd="$2" stamp lock rc
  stamp="$TIMES/$name"; lock="$STATE/job-$name.lock"
  if ! acquire_lock "$lock"; then log "$name busy skip"; return 0; fi
  log "$name start"
  if [ "$name" = "goal" ]; then CAPAFY_HEADLESS_BRIDGE=1 CAPAFY_REPORT_KIND=hourly bash "$cmd" >>"$LOG" 2>&1; rc=$?; elif [ "$name" = "marketing" ]; then CAPAFY_HEADLESS_BRIDGE=1 bash "$cmd" >>"$LOG" 2>&1; rc=$?; else bash "$cmd" >>"$LOG" 2>&1; rc=$?; fi
  if [ "$rc" -eq 0 ]; then printf '%s\n' "$(now)" >"$stamp"; log "$name success"; else log "$name failure rc=$rc"; fi
  release_lock "$lock"
  return 0
}
acquire_lock() {
  local lock="$1" owner mtime age now_s
  if mkdir "$lock" 2>/dev/null; then printf '%s\n' "$$" >"$lock/owner.pid"; return 0; fi
  owner="$(cat "$lock/owner.pid" 2>/dev/null || true)"
  case "$owner" in ''|*[!0-9]*) owner="" ;; esac
  if [ -z "$owner" ]; then
    mtime="$(stat -f %m "$lock" 2>/dev/null || stat -c %Y "$lock" 2>/dev/null || echo 0)"
    now_s="$(date +%s)"
    case "$mtime" in ''|*[!0-9]*) return 1 ;; esac
    age=$((now_s - mtime)); [ "$age" -lt "$LOCK_GRACE" ] && return 1
  fi
  if [ -z "$owner" ] || ! kill -0 "$owner" 2>/dev/null; then
    rm -f "$lock/owner.pid" 2>/dev/null || true
    rmdir "$lock" 2>/dev/null || true
    if mkdir "$lock" 2>/dev/null; then printf '%s\n' "$$" >"$lock/owner.pid"; return 0; fi
  fi
  return 1
}
due() {
  local stamp="$1" interval="$2" t current
  t="$(cat "$stamp" 2>/dev/null || true)"
  case "$t" in ''|*[!0-9]*) return 0 ;; esac
  current="$(now)"
  case "$current" in ''|*[!0-9]*) return 0 ;; esac
  [ $((current - t)) -ge "$interval" ]
}
aqua_restored() {
  if [ -n "${CAPAFY_HEADLESS_AQUA_PROBE:-}" ]; then "$CAPAFY_HEADLESS_AQUA_PROBE"; return $?; fi
  local safe="${CAPAFY_LAUNCHCTL_SAFE:-$ROOT/bin/launchctl-safe}" domain="${CAPAFY_LAUNCHCTL_DOMAIN:-gui/$(id -u)}" label
  for label in ai.anicca.capafy-goal-monitor ai.anicca.capafy-goal-monitor-hourly ai.anicca.capafy-goal-monitor-daily-close ai.anicca.capafy-loop-daily ai.anicca.capafy-loop-healthcheck ai.anicca.capafy-outcome-monitor ai.anicca.capafy-ig-account-manager ai.anicca.capafy-ig-marketing-daily; do
    "$safe" print "$domain/$label" >/dev/null 2>&1 || return 1
  done
  return 0
}
host_aqua_present() {
  if [ -n "${CAPAFY_HEADLESS_HOST_AQUA_PROBE:-}" ]; then "$CAPAFY_HEADLESS_HOST_AQUA_PROBE"; return $?; fi
  local dock=0 system=0 uid name current_uid="$(id -u)" ps_output="${CAPAFY_HEADLESS_PS_OUTPUT:-}"
  if [ -z "$ps_output" ]; then ps_output="$(/bin/ps -axo uid=,ucomm= 2>/dev/null || true)"; fi
  while read -r uid name; do
    [ "$uid" = "$current_uid" ] || continue
    [ "$name" = "Dock" ] && dock=1
    [ "$name" = "SystemUIServer" ] && system=1
  done <<EOF
$ps_output
EOF
  [ "$dock" -eq 1 ] && [ "$system" -eq 1 ]
}
host_aqua_handoff() {
  local seen="" current="" age
  if ! host_aqua_present; then rm -f "$AQUA_SEEN" 2>/dev/null || true; return 1; fi
  current="$(now)"; seen="$(cat "$AQUA_SEEN" 2>/dev/null || true)"
  case "$seen" in ''|*[!0-9]*) printf '%s\n' "$current" >"$AQUA_SEEN"; chmod 600 "$AQUA_SEEN"; return 0 ;; esac
  case "$current" in ''|*[!0-9]*) return 0 ;; esac
  age=$((current - seen)); [ "$age" -ge "$AQUA_GRACE" ] && return 2
  return 0
}
run_once() {
  mkdir -p "$TIMES"
  run_child outcome "$ROOT/skills/earn/capafy-marketing/capafy-outcome-monitor.sh"
  due "$TIMES/loop" 3600 && run_child loop "$ROOT/skills/self/capafy-loop/capafy-loop-daily.sh"
  due "$TIMES/goal" 3600 && run_child goal "$ROOT/skills/earn/capafy-marketing/capafy-goal-monitor.sh"
  due "$TIMES/marketing" 3600 && run_child marketing "$ROOT/skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh"
}
run_loop() {
  mkdir -p "$STATE" "$TIMES"; chmod 700 "$STATE" "$TIMES"
  if ! acquire_lock "$LOCK"; then log "bridge busy skip"; return 0; fi
  trap 'release_lock "$LOCK"; if [ "$(cat "$PIDFILE" 2>/dev/null || true)" = "$$" ]; then rm -f "$PIDFILE"; fi' EXIT
  printf '%s\n' "$$" >"$PIDFILE"; printf '%s\n' "$(now)" >"$HEARTBEAT"
  chmod 600 "$PIDFILE" "$HEARTBEAT"
  local ticks=0 host_rc=0
  while :; do
    printf '%s\n' "$(now)" >"$HEARTBEAT"
    if aqua_restored; then log "Aqua restored; bridge exiting"; return 0; fi
    host_rc=0; host_aqua_handoff || host_rc=$?
    if [ "$host_rc" -eq 0 ]; then
      log "Aqua host handoff grace; skipping children"
      [ "$ONCE" = "1" ] && return 0
      sleep "$INTERVAL"
      continue
    elif [ "$host_rc" -eq 2 ]; then
      log "Aqua host handoff persistent; bridge exiting"
      return 0
    fi
    run_once
    ticks=$((ticks + 1))
    if aqua_restored; then log "Aqua restored; bridge exiting"; return 0; fi
    if [ "$MAX_TICKS" -gt 0 ] && [ "$ticks" -ge "$MAX_TICKS" ]; then return 0; fi
    if [ "$ONCE" = "1" ]; then return 0; fi
    sleep "$INTERVAL"
  done
}
start_bridge() {
  mkdir -p "$STATE"
  if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE" 2>/dev/null)" 2>/dev/null; then printf 'already_running pid=%s heartbeat=%s\n' "$(cat "$PIDFILE")" "$(cat "$HEARTBEAT" 2>/dev/null || echo 0)"; return 0; fi
  local start_lock="$STATE/start.lock"
  acquire_lock "$start_lock" || { echo "start busy"; return 0; }
  rm -f "$HEARTBEAT" 2>/dev/null || true
  nohup "$0" run >>"$LOG" 2>&1 < /dev/null &
  local pid=$!; printf '%s\n' "$pid" >"$PIDFILE"
  local ready=0
  for _ in $(seq 1 50); do
    if kill -0 "$pid" 2>/dev/null && [ -s "$HEARTBEAT" ]; then ready=1; break; fi
    sleep 0.1
  done
  [ "$ready" -eq 1 ] || { release_lock "$start_lock"; return 1; }
  release_lock "$start_lock"
  printf 'started pid=%s heartbeat=%s\n' "$pid" "$(cat "$HEARTBEAT" 2>/dev/null || echo 0)"
}
case "${1:-run}" in
  run) run_loop ;;
  start) start_bridge ;;
  *) echo "usage: $0 [run|start]" >&2; exit 2 ;;
esac
