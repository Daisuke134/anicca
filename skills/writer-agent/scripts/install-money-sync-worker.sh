#!/usr/bin/env bash
# Install and immediately start the canonical Writer money-ledger synchronizer.
set -euo pipefail

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKER="$SCRIPT_DIR/money_sync.py"
PYTHON_BIN="$(command -v python3)"
LABEL="ai.anicca.writer-money-sync"
DOMAIN="gui/$(id -u)"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/.openclaw/logs"

if [ "$DRY_RUN" = "1" ]; then
  printf 'DRY-RUN: install %s -> %s (StartInterval=300 RunAtLoad=true kickstart=immediate)\n' \
    "$LABEL" "$WORKER"
  exit 0
fi

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"
TMP_PLIST="$(mktemp "$HOME/Library/LaunchAgents/.$LABEL.XXXXXX")"
trap 'rm -f -- "$TMP_PLIST"' EXIT
cat >"$TMP_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON_BIN</string><string>$WORKER</string>
    <string>--state-dir</string><string>$HOME/.local/state/mr-bot/writer</string>
    <string>--db</string><string>$HOME/.local/state/mr-bot/writer/money.sqlite3</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>StartInterval</key><integer>300</integer>
  <key>RunAtLoad</key><true/>
  <key>ProcessType</key><string>Background</string>
  <key>StandardOutPath</key><string>$LOG_DIR/writer-money-sync.out</string>
  <key>StandardErrorPath</key><string>$LOG_DIR/writer-money-sync.err</string>
</dict>
</plist>
PLIST
plutil -lint "$TMP_PLIST" >/dev/null
mv "$TMP_PLIST" "$PLIST"
trap - EXIT

launchctl bootout "$DOMAIN/$LABEL" >/dev/null 2>&1 || true
launchctl bootstrap "$DOMAIN" "$PLIST"
launchctl enable "$DOMAIN/$LABEL"
launchctl kickstart -k "$DOMAIN/$LABEL"
printf 'installed and kicked %s (%s)\n' "$LABEL" "$PLIST"
