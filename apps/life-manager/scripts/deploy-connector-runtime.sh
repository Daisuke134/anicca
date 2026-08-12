#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
TOKEN_FILE="${LM_CONNECTOR_BRIDGE_TOKEN_FILE:-${HOME}/.local/state/life-manager/connector-host-bridge/token}"
ENV_FILE="${LM_CONNECTOR_ENV_FILE:-${HOME}/.openclaw/.env}"
DOCKER_BIN="${LM_DOCKER_BIN:-docker}"
NODE_BIN="${LM_NODE_BIN:-/opt/homebrew/bin/node}"
IDENTITY_PROFILE="${LM_CONNECTOR_IDENTITY_PROFILE_PATH:-${HOME}/.config/anicca/job-search/profile.json}"
FORM_PROFILE_DIR="${LM_LUMA_FORM_PROFILE_DIR:-${HOME}/.local/state/life-manager/private}"
FORM_PROFILE_FILE="${LM_LUMA_FORM_PROFILE_HOST_PATH:-${FORM_PROFILE_DIR}/connector-luma-form-profile.json}"

if [[ ! -f "$TOKEN_FILE" || "$(stat -f '%Lp' "$TOKEN_FILE")" != "600" || ! -f "$ENV_FILE" ]]; then
  echo "Connector runtime unavailable" >&2
  exit 1
fi

if [[ ! -f "$FORM_PROFILE_FILE" ]]; then
  if [[ ! -f "$IDENTITY_PROFILE" ]]; then
    echo "Connector runtime unavailable" >&2
    exit 1
  fi
  mkdir -p "$FORM_PROFILE_DIR"
  chmod 700 "$FORM_PROFILE_DIR"
  "$NODE_BIN" -e '
const fs = require("node:fs");
const source = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
const phone = String(source && source.candidate && source.candidate.phone || "").trim();
if (!phone || phone.length > 64 || /[\x00-\x1f\x7f]/.test(phone)) process.exit(1);
fs.writeFileSync(process.argv[2], `${JSON.stringify({
  schema_version: 1,
  phone,
  form_answers: {},
  consents: { code_of_conduct_and_media_release: false },
})}\n`, { flag: "wx", mode: 0o600 });
' "$IDENTITY_PROFILE" "$FORM_PROFILE_FILE"
fi
chmod 600 "$FORM_PROFILE_FILE"
"$NODE_BIN" -e '
require(process.argv[1]).readLumaFormProfile({ path: process.argv[2] });
' "$REPO_ROOT/apps/life-manager/lib/luma-form-profile.js" "$FORM_PROFILE_FILE"
export LM_LUMA_FORM_PROFILE_HOST_PATH="$FORM_PROFILE_FILE"

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
if [[ -z "${GEMINI_API_KEY:-}" ]]; then
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
export LM_CONNECTOR_PROFILE_PATH="${LM_CONNECTOR_PROFILE_PATH:-/app/apps/life-manager/config/connector/dais-local.json}"
export LM_CONNECTOR_WORKER_CAPABILITIES="runtime.noop,outbound.event.apply,connector.coverage.refresh"

COMPOSE=(
  "$DOCKER_BIN" compose
  -f "$REPO_ROOT/deploy/local/compose.yaml"
  -f "$REPO_ROOT/deploy/local/compose.connector.yaml"
)
"${COMPOSE[@]}" build worker
"${COMPOSE[@]}" up -d --force-recreate --wait worker

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
