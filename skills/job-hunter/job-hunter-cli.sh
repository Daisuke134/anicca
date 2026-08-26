#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
APP_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd -P)/apps/job-search-loop"

usage() {
  printf 'usage: %s {daily|inbox|learning|mercor|healthcheck|install} [args ...]\n' "$0" >&2
}

[[ "$#" -gt 0 ]] || { usage; exit 64; }
LANE="$1"
shift
case "$LANE" in
  daily)       TARGET="$APP_ROOT/scripts/run-daily.sh" ;;
  inbox)       TARGET="$APP_ROOT/scripts/run-inbox.sh" ;;
  learning)    TARGET="$APP_ROOT/scripts/run-learning.sh" ;;
  mercor)      TARGET="$APP_ROOT/scripts/run-mercor.sh" ;;
  healthcheck) TARGET="$APP_ROOT/scripts/healthcheck.sh" ;;
  install)     TARGET="$APP_ROOT/scripts/install-launchd.sh" ;;
  *) usage; exit 64 ;;
esac

[[ -x "$TARGET" ]] || {
  printf 'job-hunter: canonical runner missing: %s\n' "$TARGET" >&2
  exit 78
}
exec "$TARGET" "$@"
