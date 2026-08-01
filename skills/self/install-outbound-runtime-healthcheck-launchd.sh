#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
TEMPLATE="$REPO_ROOT/skills/self/launchd/ai.anicca.outbound-runtime-healthcheck.plist"
TARGET="$HOME/Library/LaunchAgents/ai.anicca.outbound-runtime-healthcheck.plist"
LIFE_MANAGER_HOME="$HOME/.local/state/life-manager"
RENDER=0
TELEGRAM_TARGET=""
WORKER_CONTAINER="life-manager-local-worker-1"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --render) RENDER=1; shift ;;
    --telegram-target) TELEGRAM_TARGET="${2:-}"; shift 2 ;;
    --worker-container) WORKER_CONTAINER="${2:-}"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$TELEGRAM_TARGET" ] || { echo "--telegram-target is required" >&2; exit 2; }
[[ "$TELEGRAM_TARGET" =~ ^[-@A-Za-z0-9_]+$ ]] || { echo "--telegram-target is invalid" >&2; exit 2; }
[[ "$WORKER_CONTAINER" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$ ]] || { echo "--worker-container is invalid" >&2; exit 2; }
TEMP="$(mktemp "${TMPDIR:-/tmp}/outbound-runtime-healthcheck.plist.XXXXXX")"
trap 'rm -f "$TEMP"' EXIT
sed -e "s|__REPO_ROOT__|$REPO_ROOT|g" \
  -e "s|__LIFE_MANAGER_HOME__|$LIFE_MANAGER_HOME|g" \
  -e "s|__TELEGRAM_TARGET__|$TELEGRAM_TARGET|g" \
  -e "s|__WORKER_CONTAINER__|$WORKER_CONTAINER|g" "$TEMPLATE" > "$TEMP"
/usr/bin/plutil -lint "$TEMP" >/dev/null
if [ "$RENDER" -eq 1 ]; then /bin/cat "$TEMP"; exit 0; fi
mkdir -p "$HOME/Library/LaunchAgents" "$LIFE_MANAGER_HOME/logs"
/bin/cp "$TEMP" "$TARGET"
launchctl bootout "gui/$(id -u)/ai.anicca.outbound-runtime-healthcheck" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$TARGET"
launchctl kickstart "gui/$(id -u)/ai.anicca.outbound-runtime-healthcheck"
