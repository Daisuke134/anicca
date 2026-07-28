#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE="$APP_DIR/launchd/ai.anicca.life-manager-ugig-invoice-observer.plist.template"
TARGET="${HOME}/Library/LaunchAgents/ai.anicca.life-manager-ugig-invoice-observer.plist"
LABEL="ai.anicca.life-manager-ugig-invoice-observer"
DOMAIN="gui/$(id -u)"
TEMP="$(mktemp "${TMPDIR:-/tmp}/life-manager-ugig-invoice-observer.plist.XXXXXX")"

trap 'rm -f "$TEMP"' EXIT
mkdir -p "${HOME}/Library/LaunchAgents" "${HOME}/.openclaw/logs"
sed -e "s|__APP_DIR__|${APP_DIR}|g" -e "s|__HOME__|${HOME}|g" "$TEMPLATE" > "$TEMP"
plutil -lint "$TEMP"
install -m 600 "$TEMP" "$TARGET"

if launchctl print "${DOMAIN}/${LABEL}" >/dev/null 2>&1; then
  launchctl kickstart "${DOMAIN}/${LABEL}"
else
  launchctl bootstrap "$DOMAIN" "$TARGET"
  launchctl kickstart "${DOMAIN}/${LABEL}"
fi
launchctl print "${DOMAIN}/${LABEL}"
