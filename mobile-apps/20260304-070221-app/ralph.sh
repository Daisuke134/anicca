#!/bin/bash
# ralph.sh — snarktank/ralph complete copy
# Source: https://github.com/snarktank/ralph/blob/main/ralph.sh
# Slack notify: https://notes.kodekloud.com/docs/GitHub-Actions/Reusable-Workflows-and-Reporting/Slack-Notify-GitHub-Action/page
# Log files: tee to file (same tee pattern as ralph original)

set -e  # snarktank/ralph original: no pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MAX_ITERATIONS="${1:-10}"
SLACK_CHANNEL="C091G3PKHL2"

# Source secrets from .env (Twelve-Factor App: https://12factor.net/config)
if [ -f ~/.config/mobileapp-builder/.env ]; then
  set -a
  source ~/.config/mobileapp-builder/.env
  set +a
fi

mkdir -p "$SCRIPT_DIR/logs"

echo "🏭 ralph.sh 起動: MAX_ITERATIONS=$MAX_ITERATIONS"
echo "🏭 作業ディレクトリ: $SCRIPT_DIR"

notify_slack() {
  # Source: https://api.slack.com/messaging/webhooks
  # "Incoming Webhooks are a simple way to post messages from apps into Slack"
  if [ -n "${SLACK_WEBHOOK_AGENTS:-}" ]; then
    curl -s -X POST "$SLACK_WEBHOOK_AGENTS" -H 'Content-type: application/json' -d "{\"text\":\"$1\"}" 2>/dev/null || true
  fi
}

notify_slack "🏭 ralph.sh 起動: $(basename "$SCRIPT_DIR")"

PREV_PASSES=""

for i in $(seq 1 $MAX_ITERATIONS); do
  echo ""
  echo "🏭 ========================================"
  echo "🏭 Iteration $i / $MAX_ITERATIONS 開始: $(date)"
  echo "🏭 ========================================"

  LOG_FILE="$SCRIPT_DIR/logs/iteration-$i.log"

  # Stream-json for real-time output (Source: aihero.dev)
  tmpfile=$(mktemp)
  stream_text='if .type == "assistant" then (.message.content[]? | select(.type == "text") | .text) // "" elif .type == "result" then .result // "" else "" end'
  claude --dangerously-skip-permissions --verbose --print --output-format stream-json --mcp-config ~/.claude/mcp.json < "$SCRIPT_DIR/CLAUDE.md" 2>&1 | grep --line-buffered '^{' | tee "$tmpfile" | tee -a "$LOG_FILE" | jq --unbuffered -rj "$stream_text" || true
  OUTPUT=$(cat "$tmpfile")
  rm -f "$tmpfile"

  echo ""
  echo "🏭 Iteration $i 終了: $(date)"

  # Detect newly completed US and notify Slack
  if [ -f "$SCRIPT_DIR/prd.json" ]; then
    CURR_PASSES=$(python3 -c "
import json
with open('$SCRIPT_DIR/prd.json') as f: d = json.load(f)
for us in d['userStories']:
    if us['passes']: print(us['id'] + ': ' + us['title'])
" 2>/dev/null || true)

    while IFS= read -r line; do
      if [ -n "$line" ] && ! echo "$PREV_PASSES" | grep -qF "$line"; then
        notify_slack "✅ $line"
      fi
    done <<< "$CURR_PASSES"

    PREV_PASSES="$CURR_PASSES"
  fi

  if echo "$OUTPUT" | grep -q "<promise>COMPLETE</promise>"; then
    echo "🏭 ✅ COMPLETE 検出。全 US 完了。"
    notify_slack "🎉 全 US 完了！App Store に提出しました。"
    exit 0
  fi

  # validate.sh — external quality gate (Source: SonarQube pattern)
  if [ -f "$SCRIPT_DIR/validate.sh" ]; then
    echo "🔍 validate.sh 実行中..."
    "$SCRIPT_DIR/validate.sh" || {
      echo "🔴 validate.sh FAILED"
      notify_slack "🔴 validate.sh FAILED at iteration $i"
    }
  fi

  # Check for WAITING_FOR_HUMAN in progress.txt → Slack notify
  if [ -f "$SCRIPT_DIR/progress.txt" ]; then
    WAITING=$(grep -A10 "WAITING_FOR_HUMAN" "$SCRIPT_DIR/progress.txt" | tail -10)
    if [ -n "$WAITING" ]; then
      notify_slack "⏸️ 人間の操作が必要です:\n$WAITING"
    fi
  fi

  echo "🏭 sleep 2..."
  sleep 2
done

echo "🏭 ❌ MAX_ITERATIONS ($MAX_ITERATIONS) に到達。完了せず。"
notify_slack "❌ MAX_ITERATIONS ($MAX_ITERATIONS) に到達。完了せず。"
exit 1
