#!/usr/bin/env bash
# Launch one gig pass in a dedicated process group and publish the identity
# contract consumed by emergency-disk-guard.sh. This process stays as the
# supervisor until the worker exits; callers detach this supervisor.
set -uo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
WORKER_SCRIPT="${GIG_WORKER_SCRIPT:-$HOME/profitable-claude/skills/gig-work/gig_pass.sh}"
LEASE_DIR="${GIG_WORKER_LEASE_DIR:-$HOME/.openclaw/state/gig-workers}"
HEARTBEAT_INTERVAL="${GIG_WORKER_HEARTBEAT_INTERVAL:-30}"
READY_FILE="${GIG_WORKER_READY_FILE:-}"
DISK_STOP_FLAG="${GIG_WORKER_DISK_STOP_FLAG:-$HOME/.openclaw/state/disk-writers.stop}"
DISK_PRESSURE_FLAG="${GIG_WORKER_DISK_PRESSURE_FLAG:-$HOME/.openclaw/state/disk-pressure.block}"
MIN_FREE_GB="${GIG_WORKER_MIN_FREE_GB:-5}"
WORKER_PID=""
WORKER_PGID=""
HEARTBEAT_PID=""
LEASE=""
HEARTBEAT=""
WORKER_SNAPSHOT=""
WORKER_SNAPSHOT_DIR="${GIG_WORKER_SNAPSHOT_DIR:-$LEASE_DIR/snapshots}"
WORK_EVENT_PROJECTOR="${GIG_WORK_EVENT_PROJECTOR:-$HOME/profitable-claude/skills/gig-work/scripts/work_event_projector.py}"
WORK_EVENT_PROJECTOR_LOG="${GIG_WORK_EVENT_PROJECTOR_LOG:-$HOME/gig/work-event-projector.log}"
WORKER_REPORTS_ENABLED="${GIG_WORKER_REPORTS_ENABLED:-1}"
# A refused pass is as newsworthy as a finished one, so it rides its own switch --
# but defaults to the same kill switch, so nothing starts reporting by surprise.
PASS_OUTAGE_REPORTS_ENABLED="${GIG_WORKER_PASS_OUTAGE_REPORTS_ENABLED:-$WORKER_REPORTS_ENABLED}"
GIG_DIR="${GIG_WORKER_GIG_DIR:-$HOME/gig}"
# Resolved beside this launcher, so a checkout always reports through its own
# reporter instead of whichever one happens to live under $HOME.
LAUNCHER_DIR=$(cd "$(dirname "$0")" && pwd)
TELEGRAM_REPORT="${GIG_WORKER_TELEGRAM_REPORT:-$LAUNCHER_DIR/telegram_report.py}"
OPENCLAW_BIN="${GIG_WORKER_OPENCLAW:-/opt/homebrew/bin/openclaw}"
PASS_GATE_REASON=""
PASS_GATE_DETAIL=""
PASS_GATE_RECOVERY_REPORTED=0
# The operator brake is a separate gate from every disk condition below it: it is
# raised by a person or agent, and only that owner (or the expiry they set) clears
# it. See scripts/gig_brake.sh for why borrowing disk-writers.stop did not work.
# shellcheck source=/dev/null
. "$LAUNCHER_DIR/gig_brake.sh"

case "$HEARTBEAT_INTERVAL" in
  ''|*[!0-9]*) echo "gig-worker-launcher: invalid heartbeat interval" >&2; exit 2 ;;
esac
[ "$HEARTBEAT_INTERVAL" -gt 0 ] || { echo "gig-worker-launcher: heartbeat interval must be positive" >&2; exit 2; }
case "$MIN_FREE_GB" in
  ''|*[!0-9]*) echo "gig-worker-launcher: invalid minimum free GB" >&2; exit 2 ;;
esac
[ "$MIN_FREE_GB" -gt 0 ] || { echo "gig-worker-launcher: minimum free GB must be positive" >&2; exit 2; }
[ -f "$WORKER_SCRIPT" ] || { echo "gig-worker-launcher: worker not found: $WORKER_SCRIPT" >&2; exit 2; }

normalize_ps() { awk '{$1=$1; if (NF) print}'; }

free_gb() {
  if [ -n "${GIG_WORKER_TEST_FREE_GB:-}" ]; then
    printf '%s\n' "$GIG_WORKER_TEST_FREE_GB"
  else
    df -g /System/Volumes/Data 2>/dev/null | awk 'NR == 2 { print $4 }'
  fi
}

disk_preflight() {
  local available
  PASS_GATE_REASON=""
  PASS_GATE_DETAIL=""
  if [ -f "$DISK_STOP_FLAG" ]; then
    echo "gig-worker-launcher: disk preflight blocked: stop flag present: $DISK_STOP_FLAG" >&2
    PASS_GATE_REASON="stop_flag"
    PASS_GATE_DETAIL="$DISK_STOP_FLAG"
    return 78
  fi
  available=$(free_gb)
  case "$available" in
    ''|*[!0-9]*)
      echo "gig-worker-launcher: disk preflight blocked: free-space measurement unavailable" >&2
      PASS_GATE_REASON="measurement_unavailable"
      return 78
      ;;
  esac
  if [ "$available" -lt "$MIN_FREE_GB" ]; then
    echo "gig-worker-launcher: disk preflight blocked: free_gb=$available minimum_gb=$MIN_FREE_GB" >&2
    PASS_GATE_REASON="low_space"
    PASS_GATE_DETAIL="$available"
    return 78
  fi
  # The emergency guard's pressure flag is advisory and can outlive the cleanup
  # that raised it. Once this launcher's explicit minimum-space gate passes, do
  # not turn that stale advisory into a daily-cadence outage. Keep the hard stop
  # flag and measured low-space rejection fail-closed.
  if [ -f "$DISK_PRESSURE_FLAG" ]; then
    echo "gig-worker-launcher: disk pressure advisory present; continuing with free_gb=$available minimum_gb=$MIN_FREE_GB" >&2
  fi
}

# Silent death is the mirror of silent success. A pass that refuses to start used
# to leave one line per hour in a launchd log and nothing else; on 2026-07-30 that
# ran for ten hours before anyone could have known. Reporting is best-effort by
# construction: it never blocks the gate and never changes this launcher's exit.
report_pass_gate() {
  [ "$PASS_OUTAGE_REPORTS_ENABLED" = "1" ] || return 0
  [ -f "$TELEGRAM_REPORT" ] || return 0
  case "$1" in
    blocked)
      /opt/homebrew/bin/python3 "$TELEGRAM_REPORT" pass-blocked \
        --reason "$PASS_GATE_REASON" --detail "$PASS_GATE_DETAIL" \
        --gig-dir "$GIG_DIR" --telegram-database "$GIG_DIR/telegram-outbox.sqlite3" \
        --openclaw "$OPENCLAW_BIN" >> "$GIG_DIR/pass-outage-report.log" 2>&1 || true
      ;;
    recovered)
      /opt/homebrew/bin/python3 "$TELEGRAM_REPORT" pass-recovered \
        --gig-dir "$GIG_DIR" --telegram-database "$GIG_DIR/telegram-outbox.sqlite3" \
        --openclaw "$OPENCLAW_BIN" >> "$GIG_DIR/pass-outage-report.log" 2>&1 || true
      ;;
  esac
  return 0
}

# Every refusal path reports before it exits; the first clean gate closes an open
# outage. The preflight runs twice per launch -- a block found by either one is
# real and worth reporting, but recovery is announced once per launch.
preflight_gate() {
  local rc
  # Ordered first on purpose: an operator holding the brake outranks every
  # measured condition, and the reason they typed is what must reach Telegram.
  if gig_brake_is_held; then
    gig_brake_refuse "gig-pass launcher"
    echo "gig-worker-launcher: blocked by operator brake: $(gig_brake_describe)" >&2
    PASS_GATE_REASON="operator_brake"
    PASS_GATE_DETAIL="$(gig_brake_describe)"
    report_pass_gate blocked
    exit 78
  fi
  disk_preflight
  rc=$?
  if [ "$rc" -ne 0 ]; then
    report_pass_gate blocked
    exit "$rc"
  fi
  if [ "$PASS_GATE_RECOVERY_REPORTED" = "0" ]; then
    PASS_GATE_RECOVERY_REPORTED=1
    report_pass_gate recovered
  fi
}

preflight_gate
mkdir -p "$LEASE_DIR" || exit 2

cleanup_files() {
  [ -n "$HEARTBEAT_PID" ] && kill "$HEARTBEAT_PID" 2>/dev/null || true
  [ -n "$HEARTBEAT_PID" ] && wait "$HEARTBEAT_PID" 2>/dev/null || true
  [ -n "$LEASE" ] && rm -f "$LEASE"
  [ -n "$HEARTBEAT" ] && rm -f "$HEARTBEAT"
  [ -n "$WORKER_SNAPSHOT" ] && rm -f "$WORKER_SNAPSHOT"
}

shutdown() {
  trap - EXIT INT TERM HUP
  if [ -n "$WORKER_PGID" ] && [ -n "$(ps -axo pgid= 2>/dev/null | normalize_ps | grep -x "$WORKER_PGID" || true)" ]; then
    /bin/kill -TERM "-$WORKER_PGID" 2>/dev/null || true
    sleep 1
    /bin/kill -KILL "-$WORKER_PGID" 2>/dev/null || true
  fi
  [ -n "$WORKER_PID" ] && wait "$WORKER_PID" 2>/dev/null || true
  cleanup_files
  exit 143
}

trap cleanup_files EXIT
trap shutdown INT TERM HUP

# Darwin has no setsid(1). setpgid(0,0) before exec gives the worker a dedicated
# process group while preserving the exact argv observed by the guard.
preflight_gate
mkdir -p "$WORKER_SNAPSHOT_DIR" || exit 2
WORKER_SNAPSHOT=$(mktemp "$WORKER_SNAPSHOT_DIR/gig_pass.sh.XXXXXX") || exit 2
cp -- "$WORKER_SCRIPT" "$WORKER_SNAPSHOT" || exit 2
chmod 0700 "$WORKER_SNAPSHOT" || exit 2
GIG_WORKER_LEASE_ACTIVE=1 python3 -c 'import os,sys; os.setpgid(0,0); os.execv("/bin/bash", ["/bin/bash", sys.argv[1]])' "$WORKER_SNAPSHOT" &
WORKER_PID=$!

start_token=""
canonical_argv=""
for _ in $(seq 1 100); do
  WORKER_PGID=$(ps -p "$WORKER_PID" -o pgid= 2>/dev/null | normalize_ps)
  start_token=$(ps -p "$WORKER_PID" -o lstart= 2>/dev/null | normalize_ps)
  canonical_argv=$(ps -p "$WORKER_PID" -o command= 2>/dev/null | normalize_ps)
  if [ "$WORKER_PGID" = "$WORKER_PID" ] && [ -n "$start_token" ] && [ -n "$canonical_argv" ]; then
    break
  fi
  sleep 0.05
done
if [ "$WORKER_PGID" != "$WORKER_PID" ] || [ -z "$start_token" ] || [ -z "$canonical_argv" ]; then
  echo "gig-worker-launcher: failed to establish dedicated worker identity" >&2
  shutdown
fi

LEASE="$LEASE_DIR/$WORKER_PID.lease"
HEARTBEAT="$LEASE_DIR/$WORKER_PID.heartbeat"
lease_tmp="$LEASE.$$.$RANDOM.tmp"
umask 077
printf 'pid=%s\nstart_token=%s\npgid=%s\ncanonical_argv=%s\n' \
  "$WORKER_PID" "$start_token" "$WORKER_PGID" "$canonical_argv" > "$lease_tmp" || shutdown
mv "$lease_tmp" "$LEASE" || shutdown
touch "$HEARTBEAT" || shutdown

if [ -n "$READY_FILE" ]; then
  ready_tmp="$READY_FILE.$$.$RANDOM.tmp"
  mkdir -p "${READY_FILE%/*}" 2>/dev/null || true
  printf '%s\n' "$WORKER_PID" > "$ready_tmp" && mv "$ready_tmp" "$READY_FILE"
fi

heartbeat_loop() {
  trap - EXIT INT TERM HUP
  while kill -0 "$WORKER_PID" 2>/dev/null; do
    touch "$HEARTBEAT" 2>/dev/null || exit 1
    sleep "$HEARTBEAT_INTERVAL"
  done
}
heartbeat_loop &
HEARTBEAT_PID=$!

wait "$WORKER_PID"
worker_rc=$?
# Project business ground truth before reporting. This is append-only and
# idempotent; a reporting-side failure never changes the pass's business result.
if [ -f "$WORK_EVENT_PROJECTOR" ]; then
  /opt/homebrew/bin/python3 "$WORK_EVENT_PROJECTOR" --gig-dir "$HOME/gig" \
    >> "$WORK_EVENT_PROJECTOR_LOG" 2>&1 || true
fi
if [ "$WORKER_REPORTS_ENABLED" = "1" ]; then
  # Per-pass Telegram report: every finished pass (success or fail) reports once.
  # Deduped by pass_id inside the durable outbox; never blocks the exit path.
  /opt/homebrew/bin/python3 "$HOME/profitable-claude/skills/gig-work/scripts/telegram_report.py" pass \
    >> "$HOME/.openclaw/logs/gig-pass-report.out.log" 2>&1 || true
  # Retry application/delivery instant reports after the pass. The per-event state and
  # outbox keys make this a no-op when the in-pass publish already received an ACK.
  /opt/homebrew/bin/python3 "$HOME/profitable-claude/skills/gig-work/scripts/telegram_report.py" instant-work-events \
    >> "$HOME/gig/instant-work-event-report.log" 2>&1 || true
  # Contract, payment, incident, and recovery use the same WorkEvent snapshot for
  # Telegram and the agent feed. Historical rows are baselined once, not backfilled.
  /opt/homebrew/bin/python3 "$HOME/profitable-claude/skills/gig-work/scripts/telegram_report.py" work-events \
    >> "$HOME/gig/work-event-report.log" 2>&1 || true
  # Silence alarm: a lane that keeps running while its ledger gains nothing gets one
  # Telegram warning per barren streak. Rides the same per-pass choke point.
  /opt/homebrew/bin/python3 "$HOME/profitable-claude/skills/gig-work/scripts/telegram_report.py" lane-barren \
    >> "$HOME/gig/.lane-health.err.log" 2>&1 || true
fi
cleanup_files
trap - EXIT INT TERM HUP
exit "$worker_rc"
