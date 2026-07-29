#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/runtime-paths.sh"
export PYTHONPATH="$JOB_SEARCH_APP_ROOT"
exec "$JOB_SEARCH_PYTHON" -m job_search_loop.discovery \
  --framework-root "$JOB_SEARCH_FRAMEWORK_ROOT" "$@"
