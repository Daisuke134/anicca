#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
HOME_DIR=${HOME:?HOME is required}
PYTHON_BIN=$(command -v python3 || true)
if [ -z "$PYTHON_BIN" ] || [ ! -x "$PYTHON_BIN" ]; then
  printf '%s\n' "python3 is required" >&2
  exit 1
fi
LABEL=ai.anicca.mr-bot-disk-cleanup
TARGET="$HOME_DIR/Library/LaunchAgents/$LABEL.plist"
TEMPLATE="$ROOT/skills/self/disk-cleanup/launchd/$LABEL.plist"
LAUNCHCTL_SAFE="$ROOT/bin/launchctl-safe"

"$LAUNCHCTL_SAFE" preflight >/dev/null || exit $?

mkdir -p "$HOME_DIR/Library/LaunchAgents" "$HOME_DIR/.openclaw/state"
sed -e "s#__MR_BOT_ROOT__#$ROOT#g" -e "s#__HOME__#$HOME_DIR#g" -e "s#__PYTHON__#$PYTHON_BIN#g" "$TEMPLATE" > "$TARGET"
plutil -lint "$TARGET" >/dev/null

DOMAIN="gui/$(id -u)"
"$LAUNCHCTL_SAFE" bootout "$DOMAIN/$LABEL" >/dev/null 2>&1 || true
"$LAUNCHCTL_SAFE" bootstrap "$DOMAIN" "$TARGET"
"$LAUNCHCTL_SAFE" kickstart "$DOMAIN/$LABEL"
printf '%s\n' "$TARGET"
