#!/bin/bash
# Install the outbound engine's two launchd agents.
#
#   ai.anicca.life-manager-outbound          07:30 local (JST on this box) — the daily pass
#   ai.anicca.life-manager-outbound-verify   09:00 local (JST on this box) — the independent
#                                            re-check that alone may award a green day
#
# StartCalendarInterval is evaluated in the machine's LOCAL time zone; this host runs JST, so 7:30
# here is 07:30 JST. Mirrors install-financial-report-launchd.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DOMAIN="gui/$(id -u)"

# Scratch state root: LM_DATA_DIR when set, else the XDG-style default the other Life Manager
# launchd installers already create. The legacy runtime root is rejected repo-wide.
LM_DATA_DIR="${LM_DATA_DIR:-${HOME}/.local/state/life-manager}"

mkdir -p "${HOME}/Library/LaunchAgents" "${HOME}/.anicca/logs" "${LM_DATA_DIR}/outbound"

install_agent() {
  local label="$1"
  local template="$APP_DIR/launchd/${label}.plist.template"
  local target="${HOME}/Library/LaunchAgents/${label}.plist"
  local temp
  temp="$(mktemp "${TMPDIR:-/tmp}/${label}.plist.XXXXXX")"
  # shellcheck disable=SC2064
  trap "rm -f '$temp'" RETURN

  [[ -f "$template" ]] || { echo "missing template: $template" >&2; exit 2; }
  sed \
    -e "s|__HOME__|${HOME}|g" \
    -e "s|__APP_DIR__|${APP_DIR}|g" \
    "$template" > "$temp"
  /usr/bin/plutil -lint "$temp"
  /usr/bin/install -m 600 "$temp" "$target"
  /bin/launchctl bootout "$DOMAIN/$label" 2>/dev/null || true
  /bin/launchctl bootstrap "$DOMAIN" "$target"
  /bin/launchctl enable "$DOMAIN/$label"
  /bin/launchctl print "$DOMAIN/$label" \
    | /usr/bin/grep -E '^[[:space:]]*(state =|last exit code =|run interval =)' || true
}

install_agent ai.anicca.life-manager-outbound
install_agent ai.anicca.life-manager-outbound-verify

echo "outbound agents installed. heartbeat: ${LM_DATA_DIR}/.outbound-last-pass"
