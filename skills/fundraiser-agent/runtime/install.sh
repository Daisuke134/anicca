#!/bin/bash
set -euo pipefail
REPO_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
STATE_ROOT="$HOME/.local/state/mr-bot/fundraiser"
LABEL="ai.anicca.fundraiser"
TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"
mkdir -p "$STATE_ROOT" "$HOME/Library/LaunchAgents"
chmod 700 "$STATE_ROOT"
sed -e "s|__REPO_ROOT__|$REPO_ROOT|g" -e "s|__STATE_ROOT__|$STATE_ROOT|g" \
  "$REPO_ROOT/skills/fundraiser-agent/runtime/$LABEL.plist" >"$TARGET"
chmod 600 "$TARGET"
plutil -lint "$TARGET" >/dev/null
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$TARGET"
launchctl enable "gui/$(id -u)/$LABEL"
launchctl kickstart "gui/$(id -u)/$LABEL"
launchctl print "gui/$(id -u)/$LABEL"
