#!/bin/bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$HOME/.anicca/logs" "$HOME/.anicca/state"
exec /usr/bin/env node "$DIR/acquisition-controller.mjs"
