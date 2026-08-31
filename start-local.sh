#!/usr/bin/env bash
# anicca local launcher (repo root) — starts the self-pay compute proxy and then
# the anicca loop. Usage (from the repo root):
#
#   ./start-local.sh node runtime/loop/index.mjs
#
# Delegates to runtime/compute-proxy/start-local.sh, preserving your current
# working directory so the loop path (runtime/loop/index.mjs) resolves correctly.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$HERE/runtime/compute-proxy/start-local.sh" "$@"
