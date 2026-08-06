#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/runtime-paths.sh"

BOOTSTRAP_PYTHON="$JOB_SEARCH_PYTHON"
BROWSER_USE_RUNTIME_ROOT="${JOB_SEARCH_BROWSER_USE_RUNTIME_ROOT:-$JOB_SEARCH_FRAMEWORK_ROOT/runtimes}"
BROWSER_USE_LOCK="$JOB_SEARCH_APP_ROOT/config/upstreams/browser-use-0.13.7-macos-arm64-py312.lock"
UV_BIN="${JOB_SEARCH_UV:-$(command -v uv 2>/dev/null || true)}"

[[ -x "$UV_BIN" ]] || { print -u2 "browser-use bootstrap: uv is missing"; exit 69; }
export PYTHONPATH="$JOB_SEARCH_APP_ROOT${PYTHONPATH:+:$PYTHONPATH}"
"$BOOTSTRAP_PYTHON" -m job_search_loop.browser_use_runtime \
  --runtime-root "$BROWSER_USE_RUNTIME_ROOT" \
  --lock "$BROWSER_USE_LOCK" \
  --uv "$UV_BIN"
