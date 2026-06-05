#!/usr/bin/env bash
# anicca-meeting bot launchd entrypoint.
# Hosts SmallWebRTC server on :7861 so Recall.ai-spawned Chrome bots can join
# Google Meet / Zoom / Teams as a normal participant via /prebuilt/.
set -uo pipefail
SKILL="$HOME/anicca-oss-pipecat/skills/anicca-meeting"
LOG="/tmp/anicca-pipecat-meeting.log"
mkdir -p "$(dirname "$LOG")"
[ -f "$HOME/.openclaw/.env" ] && set -a && source "$HOME/.openclaw/.env" && set +a
cd "$SKILL"
echo "=== meeting boot $(date '+%Y-%m-%d %H:%M:%S %Z') ===" >> "$LOG"
exec /opt/homebrew/bin/python3 "$SKILL/server.py" 2>&1 | tee -a "$LOG"
