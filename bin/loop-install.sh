#!/usr/bin/env bash
# loop-install.sh — swap a launchd job to its generated plist and prove it came back.
#
#   bash bin/loop-install.sh <label> [<label> ...]
#
# Why this is a script and not three commands: bootstrap can fail right after a successful bootout
# ("Bootstrap failed: 5: Input/output error"), and when it does the job is left UNLOADED. Done by
# hand across 221 jobs, that is a silent stop for whichever loop happened to hit it. The swap is
# only finished when launchctl reports the label back, so this retries and then restores the plist
# it replaced rather than leaving a hole.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

AGENTS="$HOME/Library/LaunchAgents"
BACKUP_DIR="${LOOP_INSTALL_BACKUP_DIR:-$HOME/loops/plist-backups}"
DOMAIN="gui/$(id -u)"
LAUNCHCTL_SAFE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/launchctl-safe"
"$LAUNCHCTL_SAFE" preflight >/dev/null || exit $?
mkdir -p "$BACKUP_DIR"

loaded() { "$LAUNCHCTL_SAFE" print "$DOMAIN/$1" >/dev/null 2>&1; }

install_one() {
  local label="$1" plist="$AGENTS/$1.plist"
  [ -f "$plist" ] || { echo "$label: no plist at $plist" >&2; return 1; }
  plutil -lint "$plist" >/dev/null 2>&1 || { echo "$label: plist is not valid" >&2; return 1; }

  local backup="$BACKUP_DIR/$label.$(date +%Y%m%dT%H%M%S).plist"
  cp "$plist" "$backup"

  local was_loaded=no
  loaded "$label" && was_loaded=yes

  "$LAUNCHCTL_SAFE" bootout "$DOMAIN/$label" 2>/dev/null
  for attempt in 1 2 3; do
    "$LAUNCHCTL_SAFE" bootstrap "$DOMAIN" "$plist" 2>/dev/null
    if loaded "$label"; then
      echo "$label: loaded (attempt $attempt, backup $(basename "$backup"))"
      return 0
    fi
    sleep 2
  done

  # Never leave a job that was running before in an unloaded state.
  echo "$label: bootstrap failed 3x" >&2
  if [ "$was_loaded" = yes ]; then
    cp "$backup" "$plist"
    "$LAUNCHCTL_SAFE" bootstrap "$DOMAIN" "$plist" 2>/dev/null
    loaded "$label" && echo "$label: RESTORED the previous plist" >&2 \
      || echo "$label: STILL UNLOADED -- needs a human" >&2
  fi
  return 1
}

rc=0
for label in "$@"; do
  install_one "$label" || rc=1
done
exit "$rc"
