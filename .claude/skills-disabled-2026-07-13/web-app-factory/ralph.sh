#!/bin/bash
# ralph.sh — snarktank/ralph complete copy (web-app-factory version)
# Source: https://github.com/snarktank/ralph/blob/main/ralph.sh
# Slack notify: https://notes.kodekloud.com/docs/GitHub-Actions/Reusable-Workflows-and-Reporting/Slack-Notify-GitHub-Action/page
# Log files: tee to file (same tee pattern as ralph original)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MAX_ITERATIONS="${1:-20}"
SLACK_CHANNEL="C091G3PKHL2"

# Source shared secrets from web-apps/.env (Twelve-Factor App: https://12factor.net/config)
# "env vars are granular controls, each fully orthogonal to other env vars"
if [ -f /Users/anicca/anicca-project/web-apps/.env ]; then
  set -a
  source /Users/anicca/anicca-project/web-apps/.env
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

notify_slack "🏭 web-app-factory ralph.sh 起動: $(basename "$SCRIPT_DIR")"

# Pre-flight Check (Fail Fast Pattern)
# Source: https://enterprisecraftsmanship.com/posts/fail-fast-principle/
# "fetching all the required values and validating them at once on the application start.
#  If any of them is missing or invalid, the process should crash."
REQUIRED_VARS="VERCEL_TOKEN STRIPE_SECRET_KEY POSTIZ_API_KEY POSTIZ_X_INTEGRATION_ID SLACK_WEBHOOK_AGENTS"
MISSING=""
for var in $REQUIRED_VARS; do
  if [ -z "${!var:-}" ]; then
    MISSING="$MISSING $var"
  fi
done
if [ -n "$MISSING" ]; then
  echo "🏭 ❌ Pre-flight FAIL: Missing env vars:$MISSING"
  notify_slack "❌ web-app-factory Pre-flight FAIL: Missing env vars:$MISSING — web-apps/.env を確認してください"
  exit 1
fi
echo "🏭 ✅ Pre-flight PASS: All required env vars present"
notify_slack "🏭 ✅ Pre-flight PASS: 全キー確認済み。ビルド開始"

PREV_PASSES=""

for i in $(seq 1 $MAX_ITERATIONS); do
  echo ""
  echo "🏭 ========================================"
  echo "🏭 Iteration $i / $MAX_ITERATIONS 開始: $(date)"
  echo "🏭 ========================================"

  LOG_FILE="$SCRIPT_DIR/logs/iteration-$i.log"

  OUTPUT=$(claude --dangerously-skip-permissions --print --mcp-config ~/.claude/mcp.json < "$SCRIPT_DIR/CLAUDE.md" 2>&1 | tee "$LOG_FILE") || true

  echo ""
  echo "🏭 Iteration $i 終了: $(date)"

  # Detect newly completed tasks and notify Slack
  if [ -f "$SCRIPT_DIR/prd.json" ]; then
    CURR_PASSES=$(python3 -c "
import json
with open('$SCRIPT_DIR/prd.json') as f: d = json.load(f)
for us in d.get('userStories', d.get('tasks', [])):
    if us.get('passes'): print(us.get('id', '') + ': ' + us.get('title', ''))
" 2>/dev/null || true)

    while IFS= read -r line; do
      if [ -n "$line" ] && ! echo "$PREV_PASSES" | grep -qF "$line"; then
        notify_slack "✅ web-app-factory iteration $i/$MAX_ITERATIONS: $line"
      fi
    done <<< "$CURR_PASSES"

    PREV_PASSES="$CURR_PASSES"
  fi

  if echo "$OUTPUT" | grep -q "<promise>COMPLETE</promise>"; then
    echo "🏭 ✅ COMPLETE 検出。全タスク完了。"
    notify_slack "🎉 web-app-factory 完了！Vercel にデプロイ済み。"
    exit 0
  fi

  echo "🏭 sleep 2..."
  sleep 2
done

echo "🏭 ❌ MAX_ITERATIONS ($MAX_ITERATIONS) に到達。完了せず。"
notify_slack "❌ web-app-factory: MAX_ITERATIONS ($MAX_ITERATIONS) に到達。完了せず。"
exit 1
