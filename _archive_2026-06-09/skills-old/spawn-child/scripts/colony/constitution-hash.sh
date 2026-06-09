#!/usr/bin/env bash
# Emits SHA-256 of /Users/anicca/anicca-oss/CONSTITUTION.md to stdout (64 hex chars + newline).
# No side effects. Used by both spawn-child.sh (parent) and child-bootstrap.sh (child).
set -euo pipefail
CONSTITUTION="${CONSTITUTION:-/Users/anicca/anicca-oss/CONSTITUTION.md}"
shasum -a 256 "$CONSTITUTION" | awk '{print $1}'
