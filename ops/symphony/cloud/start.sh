#!/bin/sh
set -eu
umask 077

: "${LM_RELEASE_SHA:?}"
: "${LM_SYMPHONY_API_BASE_URL:?}"
: "${LM_SYMPHONY_BRIDGE_SECRET:?}"
: "${GITHUB_TOKEN:?}"
: "${CODEX_AUTH_JSON:?}"

export CODEX_HOME=/data/codex
export SYMPHONY_WORKSPACE_ROOT=/data/workspaces
export GH_TOKEN="$GITHUB_TOKEN"
mkdir -p "$CODEX_HOME" "$SYMPHONY_WORKSPACE_ROOT" /data/logs /app
printf '%s' "$CODEX_AUTH_JSON" > "$CODEX_HOME/auth.json"

base="https://raw.githubusercontent.com/Daisuke134/life-manager/$LM_RELEASE_SHA"
curl -fsSL "$base/apps/life-manager/scripts/money-printer-symphony-bridge.js" -o /app/bridge.js
curl -fsSL "$base/ops/symphony/WORKFLOW.money-printer.md" -o /app/WORKFLOW.md

(while :; do node /app/bridge.js || true; sleep 5; done) &
exec symphony /app/WORKFLOW.md --logs-root /data/logs
