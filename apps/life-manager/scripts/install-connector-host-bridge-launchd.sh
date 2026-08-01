#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE="$APP_DIR/launchd/ai.anicca.life-manager-connector-host-bridge.plist.template"
LABEL="ai.anicca.life-manager-connector-host-bridge"
TARGET="${HOME}/Library/LaunchAgents/${LABEL}.plist"
STATE_DIR="${HOME}/.local/state/life-manager/connector-host-bridge"
TOKEN_FILE="$STATE_DIR/token"
DOMAIN="gui/$(id -u)"
TEMP="$(mktemp "${TMPDIR:-/tmp}/life-manager-connector-host-bridge.plist.XXXXXX")"
trap 'rm -f "$TEMP"' EXIT

mkdir -p "${HOME}/Library/LaunchAgents" "${HOME}/.anicca/logs" "$STATE_DIR"
chmod 700 "$STATE_DIR"
if [[ ! -f "$TOKEN_FILE" ]]; then
  umask 077
  /usr/bin/openssl rand -hex 32 > "$TOKEN_FILE"
fi
chmod 600 "$TOKEN_FILE"

sed \
  -e "s|__HOME__|${HOME}|g" \
  -e "s|__APP_DIR__|${APP_DIR}|g" \
  "$TEMPLATE" > "$TEMP"
/usr/bin/plutil -lint "$TEMP" >/dev/null
/usr/bin/install -m 600 "$TEMP" "$TARGET"

if [[ "${LM_CONNECTOR_BRIDGE_RENDER_ONLY:-0}" == "1" ]]; then
  printf 'Connector host bridge launchd rendered\n'
  exit 0
fi

/bin/launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
/bin/launchctl bootstrap "$DOMAIN" "$TARGET"
/bin/launchctl enable "$DOMAIN/$LABEL"
/bin/launchctl kickstart -k "$DOMAIN/$LABEL"
/bin/launchctl print "$DOMAIN/$LABEL" \
  | /usr/bin/grep -E '^[[:space:]]*(state =|last exit code =|pid =)' || true
