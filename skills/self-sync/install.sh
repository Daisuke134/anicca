#!/usr/bin/env bash
set -eu

LABEL=ai.anicca.agents-skills-sync
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$PLIST_DIR/$LABEL.plist"
LOG_PATH="$HOME/.openclaw/logs/agents-skills-sync.log"

mkdir -p "$PLIST_DIR" "$(dirname -- "$LOG_PATH")"

escaped_script=$(printf '%s' "$SCRIPT_DIR/sync.sh" \
  | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g' -e 's/"/\&quot;/g' -e "s/'/\&apos;/g")
escaped_log=$(printf '%s' "$LOG_PATH" \
  | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g' -e 's/"/\&quot;/g' -e "s/'/\&apos;/g")

umask 022
{
  printf '%s\n' '<?xml version="1.0" encoding="UTF-8"?>'
  printf '%s\n' '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">'
  printf '%s\n' '<plist version="1.0">' '<dict>'
  printf '%s\n' '  <key>Label</key>' "  <string>$LABEL</string>"
  printf '%s\n' '  <key>ProgramArguments</key>' '  <array>'
  printf '%s\n' '    <string>/bin/bash</string>' "    <string>$escaped_script</string>" '  </array>'
  printf '%s\n' '  <key>StartInterval</key>' '  <integer>1800</integer>'
  printf '%s\n' '  <key>StandardOutPath</key>' "  <string>$escaped_log</string>"
  printf '%s\n' '  <key>StandardErrorPath</key>' "  <string>$escaped_log</string>"
  printf '%s\n' '</dict>' '</plist>'
} >"$PLIST_PATH"

chmod 755 "$SCRIPT_DIR/sync.sh"
printf 'Generated %s\n' "$PLIST_PATH"
printf 'launchctl was not run. Bootstrap is assigned to Fable.\n'
