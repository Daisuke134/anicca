#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd -P)"
exec /opt/homebrew/bin/node "$HERE/taskmarket-work.mjs"
