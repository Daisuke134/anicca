#!/usr/bin/env bash
# Compatibility control for the Reddit loop. The resident agent core is retired; the existing
# launchd daily driver runs one bounded shared-runner pass and owns recurrence.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

RUN_AGENT="$HOME/anicca/skills/earn/marketing-engine/run_agent.sh"
if [ "${AGENT_WIRING_PROBE_ONLY:-0}" = "1" ]; then
  printf '{"task_class":"tool-agent","runner":"%s"}\n' "$RUN_AGENT"
  exit 0
fi

LEGACY_SOCK="/tmp/anicca-reddit-loop-tmux.sock"
LEGACY_SESSION="anicca-reddit-loop"
DAILY_LABEL="ai.anicca.hf-reddit-loop-daily"
DAILY="$HOME/profitable-claude/skills/reddit/reddit-loop-daily.sh"
DAILY_PLIST="$HOME/Library/LaunchAgents/${DAILY_LABEL}.plist"
DOMAIN="gui/$(id -u)"

ensure_daily_loaded() {
  if launchctl print "$DOMAIN/$DAILY_LABEL" >/dev/null 2>&1; then
    return 0
  fi
  if [ ! -f "$DAILY_PLIST" ]; then
    return 1
  fi
  launchctl bootstrap "$DOMAIN" "$DAILY_PLIST" >/dev/null 2>&1 || \
    launchctl load "$DAILY_PLIST" >/dev/null 2>&1 || true
  launchctl print "$DOMAIN/$DAILY_LABEL" >/dev/null 2>&1
}

status() {
  if ensure_daily_loaded; then
    echo "LOADED (bounded daily driver)"
  else
    echo "NOT_LOADED"
  fi
}

case "${1:-}" in
  --status) status; exit 0 ;;
  --restart|'') ;;
  *) echo "usage: reddit-loop-cli.sh [--status|--restart]" >&2; exit 2 ;;
esac

tmux -S "$LEGACY_SOCK" kill-session -t "$LEGACY_SESSION" 2>/dev/null || true
if launchctl print "$DOMAIN/$DAILY_LABEL" >/dev/null 2>&1; then
  launchctl kickstart -k "$DOMAIN/$DAILY_LABEL"
  echo "reddit bounded daily driver kickstarted"
else
  echo "reddit daily launchd is not loaded; running one bounded recovery pass" >&2
  exec bash "$DAILY"
fi
