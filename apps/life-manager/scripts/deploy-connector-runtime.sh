#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
TOKEN_FILE="${LM_CONNECTOR_BRIDGE_TOKEN_FILE:-${HOME}/.local/state/life-manager/connector-host-bridge/token}"
DOCKER_BIN="${LM_DOCKER_BIN:-docker}"
NODE_BIN="${LM_NODE_BIN:-/opt/homebrew/bin/node}"

if [[ ! -f "$TOKEN_FILE" || "$(stat -f '%Lp' "$TOKEN_FILE")" != "600" ]]; then
  echo "Connector runtime unavailable" >&2
  exit 1
fi

LM_CONNECTOR_BRIDGE_TOKEN="$(tr -d '\r\n' < "$TOKEN_FILE")"
TOKEN_LENGTH="${#LM_CONNECTOR_BRIDGE_TOKEN}"
if ((TOKEN_LENGTH < 32)) || ((TOKEN_LENGTH > 256)) \
  || [[ ! "$LM_CONNECTOR_BRIDGE_TOKEN" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "Connector runtime unavailable" >&2
  exit 1
fi
export LM_CONNECTOR_BRIDGE_TOKEN
export LM_RUNTIME_TENANT_ID="${LM_RUNTIME_TENANT_ID:-dais-local}"
export LM_CONNECTOR_WORKER_CAPABILITIES="runtime.noop,outbound.event.apply,connector.coverage.refresh"

COMPOSE=(
  "$DOCKER_BIN" compose
  -f "$REPO_ROOT/deploy/local/compose.yaml"
  -f "$REPO_ROOT/deploy/local/compose.connector.yaml"
)
"${COMPOSE[@]}" up -d --build --wait worker

HEALTH="$("${COMPOSE[@]}" exec -T worker node -e '
fetch("http://127.0.0.1:8790/health", {signal: AbortSignal.timeout(5000)})
  .then(async (response) => {
    if (!response.ok) process.exit(1);
    process.stdout.write(JSON.stringify(await response.json()));
  })
  .catch(() => process.exit(1));
')"
"$NODE_BIN" -e '
const value = JSON.parse(process.argv[1]);
const required = ["outbound.event.apply", "connector.coverage.refresh"];
if (value.ok !== true || !Array.isArray(value.capabilities) || !required.every((item) => value.capabilities.includes(item))) {
  process.exit(1);
}
' "$HEALTH"

printf 'Connector runtime deployed\n'
