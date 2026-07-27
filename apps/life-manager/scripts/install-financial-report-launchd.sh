#!/bin/bash
set -euo pipefail

TENANT_UID="${1:-}"
if [[ ! "$TENANT_UID" =~ ^[A-Za-z0-9_-]{1,128}$ ]]; then
  echo "usage: install-financial-report-launchd.sh <tenant-uid>" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE="$APP_DIR/launchd/ai.anicca.life-manager-financial-report.plist.template"
TARGET="${HOME}/Library/LaunchAgents/ai.anicca.life-manager-financial-report.plist"
DOMAIN="gui/$(id -u)"
LABEL="ai.anicca.life-manager-financial-report"
TEMP="$(mktemp "${TMPDIR:-/tmp}/life-manager-financial-report.plist.XXXXXX")"
trap 'rm -f "$TEMP"' EXIT

mkdir -p "${HOME}/Library/LaunchAgents" "${HOME}/.anicca/logs"
sed \
  -e "s|__HOME__|${HOME}|g" \
  -e "s|__APP_DIR__|${APP_DIR}|g" \
  -e "s|__TENANT_UID__|${TENANT_UID}|g" \
  "$TEMPLATE" > "$TEMP"
/usr/bin/plutil -lint "$TEMP"
/usr/bin/install -m 600 "$TEMP" "$TARGET"
/bin/launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
/bin/launchctl bootstrap "$DOMAIN" "$TARGET"
/bin/launchctl enable "$DOMAIN/$LABEL"
/bin/launchctl print "$DOMAIN/$LABEL" \
  | /usr/bin/grep -E '^[[:space:]]*(state =|last exit code =|run interval =)'
