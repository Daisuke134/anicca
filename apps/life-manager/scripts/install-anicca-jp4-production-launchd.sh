#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"; LABEL="ai.anicca.life-manager-anicca-jp4"; DOMAIN="gui/$(id -u)"
TEMPLATE="$APP_DIR/launchd/$LABEL.plist.template"; TARGET="${HOME}/Library/LaunchAgents/$LABEL.plist"; TEMP="$(mktemp "${TMPDIR:-/tmp}/life-manager-anicca-jp4.plist.XXXXXX")"; trap 'rm -f "$TEMP"' EXIT
if /bin/launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; then echo "$LABEL is already loaded; refusing to stop or restart it" >&2; exit 1; fi
mkdir -p "${HOME}/Library/LaunchAgents" "${HOME}/.local/state/life-manager/logs"
sed -e "s|__HOME__|${HOME}|g" -e "s|__APP_DIR__|${APP_DIR}|g" "$TEMPLATE" > "$TEMP"
/usr/bin/plutil -lint "$TEMP"; /usr/bin/install -m 600 "$TEMP" "$TARGET"; /bin/launchctl bootstrap "$DOMAIN" "$TARGET"
/bin/launchctl print "$DOMAIN/$LABEL" | /usr/bin/grep -E '^[[:space:]]*(state =|last exit code =|event triggers =|Hour|Minute)'
