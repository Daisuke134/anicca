#!/bin/bash
# runtime/agentmail/launch.sh — launchd wrapper.
# Sources ~/.openclaw/.env so AGENTMAIL_WEBHOOK_SECRET (and friends) reach the
# node process without being written into the plist itself. exec'd by launchd.
set -u
ENV_FILE="${HOME}/.openclaw/.env"
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi
cd "$(dirname "$0")" || exit 1
NODE="${NODE_BIN:-/opt/homebrew/bin/node}"
exec "$NODE" webhook-server.ts
