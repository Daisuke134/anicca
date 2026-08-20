#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
HOME_DIR=${HOME:?HOME is required}
LABEL=ai.anicca.life-manager-disk-cleanup
TARGET="$HOME_DIR/Library/LaunchAgents/$LABEL.plist"
TEMPLATE="$ROOT/skills/self/disk-cleanup/launchd/$LABEL.plist"

mkdir -p "$HOME_DIR/Library/LaunchAgents" "$HOME_DIR/.openclaw/state"
sed -e "s#__LIFE_MANAGER_ROOT__#$ROOT#g" -e "s#__HOME__#$HOME_DIR#g" "$TEMPLATE" > "$TARGET"
plutil -lint "$TARGET" >/dev/null

DOMAIN="gui/$(id -u)"
launchctl bootout "$DOMAIN/$LABEL" >/dev/null 2>&1 || true
launchctl bootstrap "$DOMAIN" "$TARGET"
launchctl kickstart "$DOMAIN/$LABEL"
printf '%s\n' "$TARGET"
