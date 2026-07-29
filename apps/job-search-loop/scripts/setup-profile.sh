#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/runtime-paths.sh"
export PYTHONPATH="$JOB_SEARCH_APP_ROOT${PYTHONPATH:+:$PYTHONPATH}"
exec "$JOB_SEARCH_PYTHON" -m job_search_loop.profile_setup \
  --output "$JOB_SEARCH_PROFILE" "$@"
