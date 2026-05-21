#!/bin/bash
# Claude Code Hook: macOS notification banner
# Usage: notify.sh <event_name>

EVENT="${1:-unknown}"

case "$EVENT" in
  Stop)
    osascript -e 'display notification "タスク完了" with title "Claude Code" subtitle "Stop"'
    ;;
  Notification)
    osascript -e 'display notification "通知があります" with title "Claude Code" subtitle "Notification"'
    ;;
  PreCompact)
    osascript -e 'display notification "コンテキスト圧縮します" with title "Claude Code" subtitle "PreCompact"'
    ;;
  SubagentStop)
    osascript -e 'display notification "サブエージェント完了" with title "Claude Code" subtitle "SubagentStop"'
    ;;
esac

exit 0
