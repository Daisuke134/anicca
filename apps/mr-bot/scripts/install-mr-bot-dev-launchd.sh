#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$HERE/.." && pwd)"
TEMPLATE="$APP_DIR/launchd/ai.anicca.mr-bot-dev.plist.template"
TARGET="$HOME/Library/LaunchAgents/ai.anicca.mr-bot-dev.plist"
DOMAIN="gui/$(id -u)"
LABEL="ai.anicca.mr-bot-dev"
TEMP="$(mktemp "${TMPDIR:-/tmp}/mr-bot-dev.plist.XXXXXX")"
trap 'rm -f "$TEMP"' EXIT

mkdir -p "$HOME/Library/LaunchAgents" "$HOME/.local/state/mr-bot/logs" "$HOME/.local/state/mr-bot/state/mr-bot-dev"
sed "s|__HOME__|$HOME|g" "$TEMPLATE" > "$TEMP"
plutil -lint "$TEMP"
install -m 600 "$TEMP" "$TARGET"
launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$TARGET"
launchctl enable "$DOMAIN/$LABEL"
launchctl print "$DOMAIN/$LABEL"
