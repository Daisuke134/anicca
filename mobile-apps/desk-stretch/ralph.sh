#!/bin/bash
# ralph.sh — snarktank/ralph complete copy
# Source: https://github.com/snarktank/ralph/blob/main/ralph.sh
# Slack notify: https://notes.kodekloud.com/docs/GitHub-Actions/Reusable-Workflows-and-Reporting/Slack-Notify-GitHub-Action/page
# Log files: tee to file (same tee pattern as ralph original)

set -e  # snarktank/ralph original: no pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MAX_ITERATIONS="${1:-10}"
SLACK_CHANNEL="${SLACK_CHANNEL_ID:-C091G3PKHL2}"

# PATH: kou (Koubou) binary location
export PATH="/Users/anicca/Library/Python/3.9/bin:$PATH"
export ASC_BYPASS_KEYCHAIN=true

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

# ============================================================
# PREFLIGHT CHECK — Fail Fast before burning CC iterations
# Source: CostOps — https://costops.dev/guides/slow-failures-expensive-before-cheap
#   "put fast, cheap checks at the front and gate expensive steps behind them"
# Source: GitLab Fail Fast — https://docs.gitlab.com/ee/ci/testing/fail_fast_testing.html
#   "runs in the .pre stage of a pipeline, before all other stages"
# Source: Anthropic Effective Harnesses — https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
#   "set up the environment with all necessary context that future coding agents will need"
# ============================================================
echo "🔍 PREFLIGHT CHECK 開始..."
PREFLIGHT_FAIL=0

# Check 1: CC token valid
echo -n "  [1/5] CC OAuth token... "
# Try env var first, then keychain
TEST_TOKEN="${CLAUDE_CODE_OAUTH_TOKEN:-}"
if [ -z "$TEST_TOKEN" ]; then
  TEST_TOKEN=$(security find-generic-password -s 'Claude Code-credentials' -w 2>/dev/null \
    | python3 -c "import json,sys; print(json.loads(sys.stdin.read().strip())['claudeAiOauth']['accessToken'])" 2>/dev/null || echo "")
  if [ -n "$TEST_TOKEN" ]; then
    export CLAUDE_CODE_OAUTH_TOKEN="$TEST_TOKEN"
  fi
fi
if [ -z "$TEST_TOKEN" ]; then
  echo "❌ トークンなし"
  PREFLIGHT_FAIL=1
else
  CC_TEST=$(echo "respond PREFLIGHT_OK" | claude -p 2>&1 || echo "FAIL")
  if echo "$CC_TEST" | grep -q "PREFLIGHT_OK"; then
    echo "✅"
  else
    echo "❌ 認証失敗: $CC_TEST"
    PREFLIGHT_FAIL=1
  fi
fi

# Check 2: Required CLIs exist
echo -n "  [2/5] 必須コマンド... "
MISSING_CMDS=""
for cmd in claude asc xcrun xcodebuild jq python3 curl git; do
  if ! command -v "$cmd" &>/dev/null; then
    MISSING_CMDS="$MISSING_CMDS $cmd"
  fi
done
if [ -n "$MISSING_CMDS" ]; then
  echo "❌ 見つからない:$MISSING_CMDS"
  PREFLIGHT_FAIL=1
else
  echo "✅"
fi

# Check 3: prd.json exists and is valid JSON
echo -n "  [3/5] prd.json... "
if [ ! -f "$SCRIPT_DIR/prd.json" ]; then
  echo "❌ ファイルなし"
  PREFLIGHT_FAIL=1
elif ! python3 -c "import json; json.load(open('$SCRIPT_DIR/prd.json'))" 2>/dev/null; then
  echo "❌ JSON不正"
  PREFLIGHT_FAIL=1
else
  REMAINING=$(python3 -c "
import json
with open('$SCRIPT_DIR/prd.json') as f: d = json.load(f)
print(sum(1 for us in d['userStories'] if not us['passes']))
" 2>/dev/null)
  if [ "$REMAINING" = "0" ]; then
    echo "✅ 全US完了済み — 実行不要"
    exit 0
  else
    echo "✅ 残り${REMAINING}個のUS"
  fi
fi

# Check 4: ASC API access
echo -n "  [4/5] ASC API接続... "
ASC_TEST=$(asc apps list --limit 1 --output json 2>&1 || echo "ASC_FAIL")
if echo "$ASC_TEST" | grep -q "ASC_FAIL\|error\|Error\|NOT_AUTHORIZED"; then
  echo "⚠️ スキップ（ASC接続エラー — 後で再試行）"
else
  echo "✅"
fi

# Check 5: Disk space
echo -n "  [5/5] ディスク空き... "
DISK_PCT=$(df -h / | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$DISK_PCT" -gt 90 ]; then
  echo "❌ ${DISK_PCT}% 使用（90%超過）"
  PREFLIGHT_FAIL=1
else
  echo "✅ ${DISK_PCT}%"
fi

if [ "$PREFLIGHT_FAIL" -eq 1 ]; then
  echo ""
  echo "🔴 PREFLIGHT FAILED — ralph.sh を開始しない"
  notify_slack "🔴 PREFLIGHT FAILED: $(basename "$SCRIPT_DIR") — CCトークンまたは必須コマンドが無効。手動確認必要。"
  exit 1
fi

echo "🟢 PREFLIGHT OK — 全チェック通過"
echo ""

PREV_PASSES=""

for i in $(seq 1 $MAX_ITERATIONS); do
  # Token refresh: read fresh token from Keychain before each iteration
  # Source: https://github.com/AndyMik90/Auto-Claude/issues/1518
  # "Claude CLI terminal works for days because it has internal token refresh logic"
  # "claude -p" pipe mode does NOT refresh — must read fresh token each iteration
  FRESH_TOKEN=$(security find-generic-password -s 'Claude Code-credentials' -w 2>/dev/null \
    | python3 -c "import json,sys; print(json.loads(sys.stdin.read().strip())['claudeAiOauth']['accessToken'])" 2>/dev/null || echo "")
  if [ -n "$FRESH_TOKEN" ]; then
    export CLAUDE_CODE_OAUTH_TOKEN="$FRESH_TOKEN"
  fi

  # WAITING_FOR_HUMAN: don't burn iterations while waiting for human input
  # Source: https://github.com/snarktank/ralph — "pause until resolved"
  WAIT_COUNT=0
  while [ -f "$SCRIPT_DIR/progress.txt" ] && grep -q "WAITING_FOR_HUMAN" "$SCRIPT_DIR/progress.txt"; do
    echo "🏭 ⏸️ WAITING_FOR_HUMAN 検出。人間の入力待ち... (${WAIT_COUNT}回目)"
    WAIT_COUNT=$((WAIT_COUNT + 1))
    if [ $WAIT_COUNT -ge 120 ]; then  # 1時間（30秒×120）
      echo "🏭 ❌ WAITING_FOR_HUMAN タイムアウト（1時間）"
      notify_slack "❌ WAITING_FOR_HUMAN タイムアウト（1時間）。手動対応必要。"
      break 2
    fi
    sleep 30
  done

  echo ""
  echo "🏭 ========================================"
  echo "🏭 Iteration $i / $MAX_ITERATIONS 開始: $(date)"
  echo "🏭 ========================================"

  LOG_FILE="$SCRIPT_DIR/logs/iteration-$i.log"

  # 1 US enforcement: イテレーション前の passes snapshot を取得
  BEFORE_PASSES=""
  if [ -f "$SCRIPT_DIR/prd.json" ]; then
    BEFORE_PASSES=$(python3 -c "
import json
with open('$SCRIPT_DIR/prd.json') as f: d = json.load(f)
for us in d['userStories']:
    if us['passes']: print(us['id'])
" 2>/dev/null || true)
  fi

  # Stream-json for real-time output (Source: aihero.dev)
  tmpfile=$(mktemp)
  stream_text='if .type == "assistant" then (.message.content[]? | select(.type == "text") | .text) // "" elif .type == "result" then .result // "" else "" end'
  claude --dangerously-skip-permissions --verbose --print --output-format stream-json --mcp-config ~/.claude/mcp.json < "$SCRIPT_DIR/CLAUDE.md" 2>&1 | grep --line-buffered '^{' | tee "$tmpfile" | tee -a "$LOG_FILE" | jq --unbuffered -rj "$stream_text" || true
  OUTPUT=$(cat "$tmpfile")
  rm -f "$tmpfile"

  # Detect "Out of extra usage" and break immediately
  if echo "$OUTPUT" | grep -qi "out of extra usage\|out of.*usage\|usage.*exceeded"; then
    echo "🏭 ⚠️ CC usage 超過検出。残りイテレーションをスキップ。"
    notify_slack "⚠️ CC usage 超過。イテレーション $i で停止。"
    break
  fi

  echo ""
  echo "🏭 Iteration $i 終了: $(date)"

  # 1 US enforcement: イテレーション後に新しく passes:true になった US を数える
  if [ -f "$SCRIPT_DIR/prd.json" ]; then
    AFTER_PASSES=$(python3 -c "
import json
with open('$SCRIPT_DIR/prd.json') as f: d = json.load(f)
for us in d['userStories']:
    if us['passes']: print(us['id'])
" 2>/dev/null || true)
    # 差分を取って新しく完了した US を数える
    NEW_PASSES=""
    while IFS= read -r us_id; do
      if [ -n "$us_id" ] && ! echo "$BEFORE_PASSES" | grep -qF "$us_id"; then
        NEW_PASSES="$NEW_PASSES $us_id"
      fi
    done <<< "$AFTER_PASSES"
    NEW_COUNT=$(echo "$NEW_PASSES" | xargs | wc -w | tr -d ' ')
    if [ "$NEW_COUNT" -gt 1 ]; then
      echo "🔴 1 US enforcement 違反: $NEW_COUNT US が1イテレーションで完了 ($NEW_PASSES)"
      notify_slack "🔴 1 US enforcement 違反: ${NEW_COUNT} US が1イテレーションで完了。最後の1つ以外をリセット。"
      # 最初に完了した1つだけ残して、残りをリセット
      KEEP_FIRST=$(echo "$NEW_PASSES" | xargs | awk '{print $1}')
      python3 -c "
import json
with open('$SCRIPT_DIR/prd.json') as f: prd = json.load(f)
new_passes = '$NEW_PASSES'.split()
keep = '$KEEP_FIRST'
for us in prd['userStories']:
    if us['id'] in new_passes and us['id'] != keep:
        us['passes'] = False
        us['notes'] = us.get('notes','') + ' [reset: 1 US per iteration rule]'
        print(f'🔄 {us[\"id\"]} reset to passes:false (1 US rule)')
with open('$SCRIPT_DIR/prd.json','w') as f: json.dump(prd, f, indent=2, ensure_ascii=False)
" 2>/dev/null || true
    fi
  fi

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
  # Auto-reset: validate.sh FAIL → passes:true を passes:false にリセット
  if [ -f "$SCRIPT_DIR/validate.sh" ]; then
    echo "🔍 validate.sh 実行中..."
    "$SCRIPT_DIR/validate.sh" || {
      echo "🔴 validate.sh FAILED — auto-resetting passes:true → false"
      notify_slack "🔴 validate.sh FAILED at iteration $i — auto-reset実行"
      # Auto-reset: validate.sh が FAIL した US の passes を false に戻す
      if [ -f "$SCRIPT_DIR/prd.json" ]; then
        python3 -c "
import json, subprocess, re
with open('$SCRIPT_DIR/prd.json') as f: prd = json.load(f)
result = subprocess.run(['$SCRIPT_DIR/validate.sh'], capture_output=True, text=True)
output = result.stdout + result.stderr
# FAIL した US を検出してリセット
for us in prd['userStories']:
    if us['passes'] and us['id'] in output:
        us['passes'] = False
        us['notes'] = us.get('notes','') + ' [auto-reset by ralph.sh]'
        print(f'🔄 {us[\"id\"]} reset to passes:false')
with open('$SCRIPT_DIR/prd.json','w') as f: json.dump(prd, f, indent=2, ensure_ascii=False)
" 2>/dev/null || true
      fi
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
