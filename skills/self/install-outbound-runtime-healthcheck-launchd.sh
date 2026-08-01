#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
TEMPLATE="$REPO_ROOT/skills/self/launchd/ai.anicca.outbound-runtime-healthcheck.plist"
TARGET="$HOME/Library/LaunchAgents/ai.anicca.outbound-runtime-healthcheck.plist"
LIFE_MANAGER_HOME="$HOME/.local/state/life-manager"
TEMP="$(mktemp "${TMPDIR:-/tmp}/outbound-runtime-healthcheck.plist.XXXXXX")"
trap 'rm -f "$TEMP"' EXIT
sed -e "s|__REPO_ROOT__|$REPO_ROOT|g" -e "s|__LIFE_MANAGER_HOME__|$LIFE_MANAGER_HOME|g" "$TEMPLATE" > "$TEMP"
/usr/bin/plutil -lint "$TEMP" >/dev/null
if [ "${1:-}" = "--render" ]; then /bin/cat "$TEMP"; exit 0; fi
mkdir -p "$HOME/Library/LaunchAgents" "$LIFE_MANAGER_HOME/logs"
/bin/cp "$TEMP" "$TARGET"
launchctl bootout "gui/$(id -u)/ai.anicca.outbound-runtime-healthcheck" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$TARGET"
launchctl kickstart "gui/$(id -u)/ai.anicca.outbound-runtime-healthcheck"
