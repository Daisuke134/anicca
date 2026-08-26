#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ARGS="${1:-}"
[ -n "$ARGS" ] || ARGS='{}'
SERVICE="$(jq -er '.service | strings | select(length > 0)' <<<"$ARGS")"
CAPABILITY="$(jq -r '.capability // "" | strings' <<<"$ARGS")"
exec python3 "$ROOT/skills/_shared/resource_resolver.py" resolve \
  --service "$SERVICE" --capability "$CAPABILITY"
