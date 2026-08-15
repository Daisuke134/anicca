#!/usr/bin/env bash
# gig_gates.sh — "is the gig loop able to run right now, and if not, why?"
#
# WHY: on 2026-08-07 an operator believed the loop was stopped because of the flag
# they had written. It was actually running. Later they believed it was stopped
# because they had killed it; it was actually unloaded-and-rebootstrapped. Both
# times the belief was about ONE gate, and the loop's real state was decided by a
# different one. So this reads EVERY gate that can block a pass -- not just the
# operator brake this file ships with -- and prints them all, blocking or not.
#
#   bash skills/earn/gig/scripts/gig_gates.sh
#
# Exit 0 = the loop can run. Exit 1 = at least one BLOCKING gate.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
source "$SCRIPT_DIR/gig_paths.sh"
# shellcheck source=/dev/null
. "$SCRIPT_DIR/gig_brake.sh"

AGENTS_DIR="${GIG_LAUNCH_AGENTS_DIR:-$HOME/Library/LaunchAgents}"
UID_NUM="$(id -u)"
BLOCKING=0

row() { # row STATUS GATE DETAIL
  [ "$1" = "BLOCKING" ] && BLOCKING=$(( BLOCKING + 1 ))
  printf '%-9s %-26s %s\n' "$1" "$2" "$3"
}

echo "=== gig loop gates @ $(date '+%F %T') ==="

# 1. Operator brake (this file's own gate).
gig_brake_read
case "$GIG_BRAKE_STATE" in
  held)    row BLOCKING "operator brake" "HELD $(gig_brake_describe) [$GIG_BRAKE_FILE]" ;;
  expired) row ok       "operator brake" "expired, no longer blocking (record kept at $GIG_BRAKE_FILE)" ;;
  *)       row ok       "operator brake" "absent ($GIG_BRAKE_FILE)" ;;
esac

# 2. disk-writers.stop -- owned by disk-sentinel.sh, cleared by IT at >=6GB free.
DISK_STOP="${GIG_WORKER_DISK_STOP_FLAG:-$GIG_HOST_STATE_DIR/disk-writers.stop}"
if [ -f "$DISK_STOP" ]; then
  row BLOCKING "disk-writers.stop" "present (owner: disk-sentinel.sh; it clears this, not you) $(head -1 "$DISK_STOP" 2>/dev/null)"
else
  row ok "disk-writers.stop" "absent"
fi

# 3. Measured free space vs the launcher's own minimum.
MIN_FREE_GB="${GIG_WORKER_MIN_FREE_GB:-5}"
FREE_GB="$(df -g /System/Volumes/Data 2>/dev/null | awk 'NR == 2 { print $4 }')"
case "$FREE_GB" in
  ''|*[!0-9]*) row BLOCKING "free disk" "measurement unavailable" ;;
  *) if [ "$FREE_GB" -lt "$MIN_FREE_GB" ]; then
       row BLOCKING "free disk" "${FREE_GB}GB < ${MIN_FREE_GB}GB minimum"
     else
       row ok "free disk" "${FREE_GB}GB (minimum ${MIN_FREE_GB}GB)"
     fi ;;
esac

# 4. disk-pressure.block -- advisory only; the launcher logs and continues.
PRESSURE="${GIG_WORKER_DISK_PRESSURE_FLAG:-$GIG_HOST_STATE_DIR/disk-pressure.block}"
if [ -f "$PRESSURE" ]; then
  row warn "disk-pressure.block" "present but ADVISORY (launcher continues)"
else
  row ok "disk-pressure.block" "absent"
fi

# 5/6. Every installed hf-gig LaunchAgent: valid? loaded? which tree does it run?
for installed in "$AGENTS_DIR"/ai.anicca.hf-gig-*.plist; do
  [ -e "$installed" ] || continue
  base="$(basename "$installed" .plist)"
  label="$(plutil -extract Label raw -o - "$installed" 2>/dev/null || true)"
  if ! plutil -lint -s "$installed" >/dev/null 2>&1; then
    row BLOCKING "plist $base" "CORRUPT (plist-selfheal will restore it from repo)"
    continue
  fi
  # Which checkout actually executes -- the pass runs from a worktree, the rest
  # from the main tree, and mistaking one for the other has cost hours before.
  # plutil's json escapes every slash, so unescape before matching. Reported for
  # every job, not just the pass: the pass runs from a worktree and the rest from
  # the main tree, and mistaking one for the other has cost hours before.
  tree="$(plutil -extract ProgramArguments json -o - "$installed" 2>/dev/null \
    | tr -d '\\' | tr ',' '\n' \
    | grep -Eo '/(Users|home)/[^"]*/skills/earn/gig' | head -1)"
  tree="${tree:-?}"
  case "$tree" in
    */.worktrees/*) tree="worktree:$(echo "$tree" | sed 's#.*/.worktrees/##; s#/skills/earn/gig##')" ;;
    ?) : ;;
    *) tree="main-tree" ;;
  esac
  if launchctl print "gui/$UID_NUM/$label" >/dev/null 2>&1; then
    state="$(launchctl print "gui/$UID_NUM/$label" 2>/dev/null | sed -n 's/.*state = //p' | head -1)"
    row ok "launchd $base" "loaded, state=${state:-unknown}, runs from ${tree}"
  else
    if [ "$base" = "ai.anicca.hf-gig-pass" ]; then
      row BLOCKING "launchd $base" "NOT LOADED -- nothing will schedule a pass (would run from ${tree})"
    else
      row warn "launchd $base" "NOT LOADED (would run from ${tree})"
    fi
  fi
done

# 7. CDP browser lock -- a held lock defers, it does not fail.
CDP_LOCK="${CDP_LOCK_DIR:-$HOME/gig/.cdp-9222.lock}"
if [ -d "$CDP_LOCK" ]; then
  row warn "cdp browser lock" "held by $(cat "$CDP_LOCK/meta" 2>/dev/null || echo unknown) (new work defers, exit 75)"
else
  row ok "cdp browser lock" "free"
fi

# 8. tmux core supervisor.
if tmux -S /tmp/anicca-gig-tmux.sock has-session -t anicca-gig-core 2>/dev/null; then
  HB="$HOME/gig/.gig-core-heartbeat"
  AGE=$(( ( $(date +%s) - $(stat -f %m "$HB" 2>/dev/null || echo 0) ) / 60 ))
  row ok "gig-core tmux" "ALIVE, heartbeat ${AGE}min old (healthcheck restarts at >=5min)"
else
  row warn "gig-core tmux" "DEAD (healthcheck restarts it within 5min unless the brake is held)"
fi

# 9. Healthcheck restart backoff -- 5 restarts/60min and self-heal stops.
RESTART_LOG="$HOME/gig/.restart-log"
if [ -f "$RESTART_LOG" ]; then
  NOW=$(date +%s); C=0
  while IFS= read -r ts; do
    case "$ts" in ''|*[!0-9]*) continue ;; esac
    [ $(( NOW - ts )) -le 3600 ] && C=$(( C + 1 ))
  done < "$RESTART_LOG"
  if [ "$C" -ge 5 ]; then
    row BLOCKING "healthcheck backoff" "$C restarts in 60min -- self-heal suspended"
  else
    row ok "healthcheck backoff" "$C/5 restarts in the last 60min"
  fi
else
  row ok "healthcheck backoff" "0/5 restarts in the last 60min"
fi

# 10. Loop registry allocation -- gig-cli.sh exits if this loop is paused.
REGISTRY="${CEO_STATE_DIR:-$LIFE_MANAGER_REPO}/config/loop-registry.json"
if [ -f "$REGISTRY" ]; then
  STATUS="$(/opt/homebrew/bin/python3 -c '
import json,sys
try:
    d=json.load(open(sys.argv[1]))
except Exception:
    print("unreadable"); raise SystemExit
loops=d.get("loops",d)
g=loops.get("gig",{}) if isinstance(loops,dict) else {}
print((g.get("allocation") or {}).get("status") or g.get("status") or "unset")
' "$REGISTRY" 2>/dev/null || echo unreadable)"
  if [ "$STATUS" = "paused" ]; then
    row BLOCKING "loop registry (gig)" "allocation.status=paused -- gig-cli.sh refuses to start the core"
  else
    row ok "loop registry (gig)" "allocation.status=$STATUS"
  fi
else
  row warn "loop registry (gig)" "not found at $REGISTRY (registry-enforce fails OPEN)"
fi

# 11. KYC switch -- gig-cli.sh will not start the core without it.
if grep -qs '^GIG_KYC_CONFIRMED=1' "$GIG_ENV_FILE"; then
  row ok "GIG_KYC_CONFIRMED" "=1"
else
  row BLOCKING "GIG_KYC_CONFIRMED" "not 1 in the configured environment file -- gig-cli.sh will not start the core"
fi

echo
if [ "$BLOCKING" -eq 0 ]; then
  echo "VERDICT: the gig loop CAN run (0 blocking gates)."
  exit 0
fi
echo "VERDICT: the gig loop CANNOT run -- $BLOCKING blocking gate(s) above."
exit 1
