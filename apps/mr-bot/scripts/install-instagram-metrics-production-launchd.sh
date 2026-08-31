#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE="$APP_DIR/launchd/ai.anicca.mr-bot-instagram-metrics.plist.template"; TARGET="${HOME}/Library/LaunchAgents/ai.anicca.mr-bot-instagram-metrics.plist"
DOMAIN="gui/$(id -u)"; LABEL="ai.anicca.mr-bot-instagram-metrics"; TEMP="$(mktemp "${TMPDIR:-/tmp}/mr-bot-instagram-metrics.plist.XXXXXX")"
trap 'rm -f "$TEMP"' EXIT
if /bin/launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; then echo "$LABEL is already loaded; refusing to stop or restart it" >&2; exit 1; fi
mkdir -p "${HOME}/Library/LaunchAgents" "${HOME}/.local/state/mr-bot/logs"
sed -e "s|__HOME__|${HOME}|g" -e "s|__APP_DIR__|${APP_DIR}|g" "$TEMPLATE" > "$TEMP"
/usr/bin/plutil -lint "$TEMP"; /usr/bin/install -m 600 "$TEMP" "$TARGET"; /bin/launchctl bootstrap "$DOMAIN" "$TARGET"
/bin/launchctl print "$DOMAIN/$LABEL" | /usr/bin/grep -E '^[[:space:]]*(state =|runs =|last exit code =|run interval =)'
