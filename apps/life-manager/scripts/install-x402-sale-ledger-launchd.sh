#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE="$APP_DIR/launchd/ai.anicca.life-manager-x402-ledger.plist.template"
TARGET="${HOME}/Library/LaunchAgents/ai.anicca.life-manager-x402-ledger.plist"
DOMAIN="gui/$(id -u)"
LABEL="ai.anicca.life-manager-x402-ledger"
TEMP="$(mktemp "${TMPDIR:-/tmp}/life-manager-x402-ledger.plist.XXXXXX")"
trap 'rm -f "$TEMP"' EXIT

mkdir -p "${HOME}/Library/LaunchAgents" "${HOME}/.anicca/logs"
sed -e "s|__HOME__|${HOME}|g" -e "s|__APP_DIR__|${APP_DIR}|g" "$TEMPLATE" > "$TEMP"
/usr/bin/plutil -lint "$TEMP"
/usr/bin/install -m 600 "$TEMP" "$TARGET"
/bin/launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
/bin/launchctl bootstrap "$DOMAIN" "$TARGET"
/bin/launchctl enable "$DOMAIN/$LABEL"
/bin/launchctl print "$DOMAIN/$LABEL" \
  | /usr/bin/grep -E '^[[:space:]]*(state =|last exit code =|run interval =)'
