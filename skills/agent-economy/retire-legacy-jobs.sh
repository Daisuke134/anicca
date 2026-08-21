#!/usr/bin/env bash
set -euo pipefail

if [ "${AGENT_ECONOMY_RETIRE_LEGACY:-0}" != "1" ]; then
  echo "agent-economy: legacy retirement disabled; set AGENT_ECONOMY_RETIRE_LEGACY=1 after preflight" >&2
  exit 2
fi

REPO="${LIFE_MANAGER_REPO:-$(cd "$(dirname "$0")/../.." && pwd -P)}"
SAFE="$REPO/bin/launchctl-safe"
[ -x "$SAFE" ] || { echo "agent-economy: launchctl-safe missing at $SAFE" >&2; exit 2; }
"$SAFE" preflight >/dev/null
DOMAIN="gui/$(id -u)"

for label in \
  ai.anicca.citizen-refill \
  ai.anicca.x402-acquisition-controller \
  ai.anicca.x402-experiment-franklin1; do
  "$SAFE" bootout "$DOMAIN/$label" 2>/dev/null || true
  if "$SAFE" print "$DOMAIN/$label" >/dev/null 2>&1; then
    echo "agent-economy: legacy label remains loaded: $label" >&2
    exit 1
  fi
done

echo "agent-economy: retired legacy job labels"
