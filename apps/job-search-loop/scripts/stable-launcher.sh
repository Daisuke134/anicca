#!/bin/zsh
set -euo pipefail

LANE="${0:t}"
case "$LANE" in
  browser|daily|inbox|learning) ;;
  *) print -u2 "job-search launcher: invalid lane $LANE"; exit 78 ;;
esac

DATA_ROOT="${JOB_SEARCH_DATA_ROOT:-${XDG_DATA_HOME:-$HOME/.local/share}/anicca/job-search}"
[[ -d "$DATA_ROOT" ]] || { print -u2 "job-search launcher: data root is missing"; exit 78; }
DATA_ROOT="$(cd "$DATA_ROOT" && pwd -P)"
CURRENT="$DATA_ROOT/current"
[[ -L "$CURRENT" ]] || { print -u2 "job-search launcher: current release is not active"; exit 78; }
RELEASE_ROOT="$(cd "$CURRENT" && pwd -P)"
case "$RELEASE_ROOT" in
  "$DATA_ROOT"/releases/*) ;;
  *) print -u2 "job-search launcher: current target escaped releases"; exit 78 ;;
esac
[[ -f "$RELEASE_ROOT/RELEASE.json" ]] || { print -u2 "job-search launcher: release manifest is missing"; exit 78; }
[[ -z "$(find "$RELEASE_ROOT" -perm -u+w -print -quit)" ]] || {
  print -u2 "job-search launcher: release is writable"
  exit 78
}
RUNNER="$RELEASE_ROOT/apps/job-search-loop/scripts/run-$LANE.sh"
[[ -x "$RUNNER" ]] || { print -u2 "job-search launcher: lane runner is missing"; exit 78; }
exec "$RUNNER" "$@"
