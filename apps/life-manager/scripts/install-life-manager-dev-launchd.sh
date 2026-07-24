#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$HERE/.." && pwd)"
TEMPLATE="$APP_DIR/launchd/ai.anicca.life-manager-dev.plist.template"
TARGET="$HOME/Library/LaunchAgents/ai.anicca.life-manager-dev.plist"
DOMAIN="gui/$(id -u)"
LABEL="ai.anicca.life-manager-dev"
TEMP="$(mktemp "${TMPDIR:-/tmp}/life-manager-dev.plist.XXXXXX")"
trap 'rm -f "$TEMP"' EXIT

mkdir -p "$HOME/Library/LaunchAgents" "$HOME/.openclaw/logs" "$HOME/.openclaw/state/life-manager-dev"
sed "s|__HOME__|$HOME|g" "$TEMPLATE" > "$TEMP"
plutil -lint "$TEMP"
install -m 600 "$TEMP" "$TARGET"
launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$TARGET"
launchctl enable "$DOMAIN/$LABEL"
launchctl print "$DOMAIN/$LABEL"
