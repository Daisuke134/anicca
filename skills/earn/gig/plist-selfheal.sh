#!/usr/bin/env bash
# plist-selfheal.sh — reconcile installed ai.anicca.hf-gig-* LaunchAgent plists (A17 recurrence guard).
# Incident 2026-07-30 21:54: ~/Library/LaunchAgents/ai.anicca.hf-gig-auditor.plist was overwritten
# with a 13-byte JSON fragment ({"Minute":45}) — auditor silently unloaded for ~19h; A1 gap detection
# and A2 evidence GC both died with it. This script is the controller/reconcile loop (§0.7 BP:
# kubernetes.io/docs/concepts/architecture/controller/) that converges installed state to repo state:
#   (1) installed plist fails plutil -lint  → restore from repo copy + bootout/bootstrap
#   (2) installed plist valid but label NOT loaded in launchd → bootstrap
# Called by gig-healthcheck.sh every 5min. Testable standalone via env overrides:
#   GIG_LAUNCH_AGENTS_DIR  (default ~/Library/LaunchAgents)
#   GIG_LAUNCHD_REPO_DIR   (default $GIG_DIR/launchd)
#   GIG_LAUNCHD_REGISTRY   (default $LIFE_MANAGER_REPO/config/launchd/agents/gig.json)
#   GIG_PLIST_SKIP_LAUNCHCTL=1  (file reconcile only; for sandboxed failure-injection tests)
#   GIG_PLIST_LOG          (default configured runtime state/logs/gig-core-healthcheck.log)
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/scripts/gig_paths.sh"

AGENTS_DIR="${GIG_LAUNCH_AGENTS_DIR:-$HOME/Library/LaunchAgents}"
REPO_DIR="${GIG_LAUNCHD_REPO_DIR:-$GIG_DIR/launchd}"
REGISTRY="${GIG_LAUNCHD_REGISTRY:-$LIFE_MANAGER_REPO/config/launchd/agents/gig.json}"
LOG="${GIG_PLIST_LOG:-$GIG_LOG_DIR/gig-core-healthcheck.log}"
SKIP_LAUNCHCTL="${GIG_PLIST_SKIP_LAUNCHCTL:-0}"
UID_NUM="$(id -u)"
mkdir -p "$(dirname "$LOG")"

log() { echo "$(date '+%F %T') plist-selfheal: $*" >> "$LOG"; }

if ! python3 -c 'import json, sys; data=json.load(open(sys.argv[1])); sys.exit(0 if isinstance(data.get("agents"), dict) else 1)' \
  "$REGISTRY" >/dev/null 2>&1; then
  log "REGISTRY INVALID $REGISTRY -> no restore/bootstrap"
  exit 1
fi

desired_state() {
  python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["agents"].get(sys.argv[2], {}).get("desired_state", ""))' \
    "$REGISTRY" "$1"
}

# The one exception to the recurrence guard (added 2026-08-07 after this loop was
# restored over an operator's deliberate bootout within five minutes, twice).
# Everything above stays: corruption is still detected, the repo copy is still
# restored, drift is still reported. Only the launchd bootstrap -- the single step
# that puts a job back on the scheduler -- waits while an operator holds the brake.
# The guard's own failure mode (a silently unloaded job) is preserved, because the
# brake is bounded, alarms every 30min while held, and is announced when it lapses.
# shellcheck source=/dev/null
. "$(cd "$(dirname "$0")" && pwd)/scripts/gig_brake.sh"

bootstrap_plist() {
  local installed="$1" label="$2"
  [ "$SKIP_LAUNCHCTL" = "1" ] && return 0
  if gig_brake_is_held; then
    log "operator brake held -> NOT bootstrapping $label ($(gig_brake_describe))"
    return 0
  fi
  launchctl bootout "gui/$UID_NUM/$label" 2>/dev/null
  if launchctl bootstrap "gui/$UID_NUM" "$installed" >> "$LOG" 2>&1; then
    log "bootstrap OK ($label)"
  else
    log "bootstrap FAILED ($label)"
    return 1
  fi
}

status=0
for installed in "$AGENTS_DIR"/ai.anicca.hf-gig-*.plist; do
  [ -e "$installed" ] || continue
  base="$(basename "$installed")"
  label="${base%.plist}"
  repo="$REPO_DIR/$base"

  if [ "$(desired_state "$label")" != "enabled" ]; then
    log "RETIRED $label -> no restore/bootstrap"
    continue
  fi

  # (1) corruption check: installed plist must parse
  if ! plutil -lint -s "$installed" >/dev/null 2>&1; then
    if [ -f "$repo" ] && plutil -lint -s "$repo" >/dev/null 2>&1; then
      log "BROKEN $base ($(stat -f %z "$installed" 2>/dev/null || echo '?') bytes) → restoring from repo"
      cp "$repo" "$installed"
      bootstrap_plist "$installed" "$label" || status=1
    else
      log "BROKEN $base and no valid repo copy — cannot self-heal"
      status=1
    fi
    continue
  fi

  # (2) drift preflight (detection only, no auto-overwrite): valid installed plist that
  # differs from the repo canonical copy — surfaces silent partial overwrites early.
  if [ -f "$repo" ] && ! cmp -s "$installed" "$repo"; then
    log "DRIFT $base differs from repo canonical copy (still valid — inspect manually)"
  fi

  # (3) load check: valid plist whose label is not in launchd → bootstrap
  [ "$SKIP_LAUNCHCTL" = "1" ] && continue
  if ! launchctl print "gui/$UID_NUM/$label" >/dev/null 2>&1; then
    log "NOT LOADED $label → bootstrap"
    bootstrap_plist "$installed" "$label" || status=1
  fi
done
exit "$status"
