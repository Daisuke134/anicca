#!/usr/bin/env bash
set -euo pipefail

GIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${PYTHON:-python3}" "$GIG_DIR/scripts/money_loop_onboarding.py" "$@"
