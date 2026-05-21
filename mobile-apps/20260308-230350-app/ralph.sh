#!/bin/bash
# ralph.sh — snarktank/ralph complete copy
# Source: https://github.com/snarktank/ralph/blob/main/ralph.sh
# Slack notify: https://notes.kodekloud.com/docs/GitHub-Actions/Reusable-Workflows-and-Reporting/Slack-Notify-GitHub-Action/page
# Log files: tee to file (same tee pattern as ralph original)

set -e  # snarktank/ralph original: no pipefail

# ERR trap: log exact line number on silent failure
# Source: https://xygeni.io/blog/set-e-in-bash-why-your-script-fails-without-warning/
trap 'echo "🔴 ERROR on line $LINENO (exit $?)" >&2; curl -s -X POST "${SLACK_WEBHOOK_AGENTS:-}" -H "Content-type: application/json" -d "{\"text\":\"🔴 ralph.sh line $LINENO で異常終了 (exit $?)\"}" 2>/dev/null || true' ERR

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MAX_ITERATIONS="${1:-50}"
SLACK_CHANNEL="${SLACK_CHANNEL_ID:-C091G3PKHL2}"

# PATH: kou (Koubou) binary location
export PATH="/Users/anicca/Library/Python/3.9/bin:$PATH"
export ASC_BYPASS_KEYCHAIN=true
export ASC_WEB_SESSION_CACHE_BACKEND=file

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
# Fix #6: .env only — Keychain tokens deleted 2026-03-07
TEST_TOKEN="${CLAUDE_CODE_OAUTH_TOKEN:-}"
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

# Check 6: iris session（ASC web 操作の前提 — file backend で keychain 回避）
echo -n "  [6/6] iris session... "
IRIS_STATUS=$(asc web auth status --apple-id "$APPLE_ID" 2>&1 || echo "IRIS_FAIL")
if echo "$IRIS_STATUS" | grep -q 'authenticated.*true'; then
  echo "✅"
else
  echo "⚠️ iris expired — 2FA 必要"
  notify_slack "⏸️ iris session expired。iPhoneに届く6桁コードを送ってください。"

  WAIT_COUNT=0
  while [ $WAIT_COUNT -lt 960 ]; do
    LATEST_MSG=$(/opt/homebrew/bin/openclaw message read --channel slack --target "$SLACK_CHANNEL" --limit 1 --json 2>/dev/null | jq -r '.payload.messages[0].text // empty' 2>/dev/null || true)
    TWO_FA_CODE=$(echo "$LATEST_MSG" | grep -oE '[0-9]{6}' | head -1)

    if [ -n "$TWO_FA_CODE" ]; then
      echo "  🔑 2FA コード検出: $TWO_FA_CODE"
      ASC_WEB_PASSWORD="$APPLE_ID_PASSWORD" asc web auth login \
        --apple-id "$APPLE_ID" --two-factor-code "$TWO_FA_CODE" 2>&1

      IRIS_RECHECK=$(asc web auth status --apple-id "$APPLE_ID" 2>&1 || echo "FAIL")
      if echo "$IRIS_RECHECK" | grep -q 'authenticated.*true'; then
        echo "  ✅ iris session restored"
        break
      fi
    fi
    sleep 30
    WAIT_COUNT=$((WAIT_COUNT + 1))
  done

  if [ $WAIT_COUNT -ge 960 ]; then
    echo "❌ iris session タイムアウト（8時間）"
    notify_slack "❌ iris session タイムアウト（8時間）。手動対応必要。"
    exit 2
  fi
fi

echo "🟢 PREFLIGHT OK — 全チェック通過"

# Fix #7: Sync template references + validate.sh to app dir every run.
# Prevents stale recipes from causing failures (desk-stretch post-mortem).
TEMPLATE_DIR="/Users/anicca/anicca-project/.claude/skills/mobileapp-builder"
if [ -d "$TEMPLATE_DIR/references" ] && [ "$SCRIPT_DIR" != "$TEMPLATE_DIR" ]; then
  echo "🔄 テンプレート同期: references/ + validate.sh"
  rsync -a --update "$TEMPLATE_DIR/references/" "$SCRIPT_DIR/references/"
  cp "$TEMPLATE_DIR/validate.sh" "$SCRIPT_DIR/validate.sh"
  chmod +x "$SCRIPT_DIR/validate.sh"
fi

echo ""

PREV_PASSES=""
FAIL_COUNT=0
LAST_FAILED_US=""

for i in $(seq 1 $MAX_ITERATIONS); do
  # Fix #6: Token refresh — .env only (Keychain tokens deleted 2026-03-07).
  # Re-source .env each iteration in case token was manually updated.
  if [ -f ~/.config/mobileapp-builder/.env ]; then
    REFRESHED_TOKEN=$(grep '^CLAUDE_CODE_OAUTH_TOKEN=' ~/.config/mobileapp-builder/.env 2>/dev/null | cut -d= -f2-)
    if [ -n "$REFRESHED_TOKEN" ]; then
      export CLAUDE_CODE_OAUTH_TOKEN="$REFRESHED_TOKEN"
    fi
  fi

  # F3-b: Slack 監視 — sk_... / 2FA コードを .env に自動保存
  LATEST_MSG=$(/opt/homebrew/bin/openclaw message read --channel slack --target "$SLACK_CHANNEL" --limit 1 --json 2>/dev/null | jq -r '.payload.messages[0].text // empty' 2>/dev/null || true)
  SK_KEY=$(echo "$LATEST_MSG" | grep -oE 'sk_[A-Za-z0-9_]+' | head -1)
  if [ -n "$SK_KEY" ]; then
    SLUG=$(python3 -c "import json; print(json.load(open('$SCRIPT_DIR/prd.json')).get('project',''))" 2>/dev/null)
    PROJECT_ENV="$HOME/.config/mobileapp-builder/projects/$SLUG/.env"
    mkdir -p "$(dirname "$PROJECT_ENV")"
    if ! grep -q "RC_SECRET_KEY" "$PROJECT_ENV" 2>/dev/null; then
      echo "RC_SECRET_KEY=$SK_KEY" >> "$PROJECT_ENV"
      echo "  🔑 RC SK鍵を $PROJECT_ENV に保存"
    fi
  fi

  # F7-b: progress.txt サイズ管理（10KB 上限）
  if [ -f "$SCRIPT_DIR/progress.txt" ]; then
    PROGRESS_SIZE=$(wc -c < "$SCRIPT_DIR/progress.txt" | tr -d ' ')
    if [ "$PROGRESS_SIZE" -gt 10240 ]; then
      echo "🏭 progress.txt ${PROGRESS_SIZE}B > 10KB — アーカイブ実行"
      ARCHIVE_FILE="$SCRIPT_DIR/logs/progress-archive-$(date +%Y%m%d-%H%M%S).txt"
      cp "$SCRIPT_DIR/progress.txt" "$ARCHIVE_FILE"
      python3 -c "
import re
with open('$SCRIPT_DIR/progress.txt') as f: content = f.read()
sections = re.split(r'\n---\n', content)
patterns = sections[0] if sections[0].startswith('## Codebase') else ''
recent = '\n---\n'.join(sections[-2:]) if len(sections) > 2 else '\n---\n'.join(sections)
with open('$SCRIPT_DIR/progress.txt', 'w') as f:
    if patterns: f.write(patterns + '\n---\n')
    f.write(recent)
" 2>/dev/null || true
      echo "  ✅ アーカイブ: $ARCHIVE_FILE"
    fi
  fi

  # F3-c: WAITING_FOR_HUMAN auto-resolve（Slack から入力を自動取得）
  WAIT_COUNT=0
  while [ -f "$SCRIPT_DIR/progress.txt" ] && grep -q "WAITING_FOR_HUMAN" "$SCRIPT_DIR/progress.txt"; do
    echo "🏭 ⏸️ WAITING_FOR_HUMAN 検出。Slack 監視中... (${WAIT_COUNT}回目)"

    LATEST_MSG=$(/opt/homebrew/bin/openclaw message read --channel slack --target "$SLACK_CHANNEL" --limit 1 --json 2>/dev/null | jq -r '.payload.messages[0].text // empty' 2>/dev/null || true)

    # RC SK鍵検出
    SK_KEY=$(echo "$LATEST_MSG" | grep -oE 'sk_[A-Za-z0-9_]+' | head -1)
    if [ -n "$SK_KEY" ]; then
      echo "  🔑 RC SK鍵検出"
      SLUG=$(python3 -c "import json; print(json.load(open('$SCRIPT_DIR/prd.json')).get('project',''))" 2>/dev/null)
      PROJECT_ENV="$HOME/.config/mobileapp-builder/projects/$SLUG/.env"
      mkdir -p "$(dirname "$PROJECT_ENV")"
      echo "RC_SECRET_KEY=$SK_KEY" >> "$PROJECT_ENV"
      sed -i '' '/WAITING_FOR_HUMAN/d' "$SCRIPT_DIR/progress.txt"
      echo "  ✅ SK鍵を $PROJECT_ENV に保存。WAITING_FOR_HUMAN 解除"
      break
    fi

    # 2FA コード検出（フォールバック）
    TWO_FA=$(echo "$LATEST_MSG" | grep -oE '^[0-9]{6}$' | head -1)
    if [ -n "$TWO_FA" ]; then
      echo "  🔑 2FA コード検出: $TWO_FA"
      ASC_WEB_PASSWORD="$APPLE_ID_PASSWORD" asc web auth login \
        --apple-id "$APPLE_ID" --two-factor-code "$TWO_FA" 2>&1
      sed -i '' '/WAITING_FOR_HUMAN/d' "$SCRIPT_DIR/progress.txt"
      echo "  ✅ 2FA ログイン完了。WAITING_FOR_HUMAN 解除"
      break
    fi

    WAIT_COUNT=$((WAIT_COUNT + 1))
    if [ $WAIT_COUNT -ge 960 ]; then
      echo "🏭 ❌ WAITING_FOR_HUMAN タイムアウト（8時間）"
      notify_slack "❌ WAITING_FOR_HUMAN タイムアウト（8時間）。手動対応必要。"
      exit 2
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
  claude --dangerously-skip-permissions --verbose --print --output-format stream-json --mcp-config ~/.claude/mcp.json --model opusplan < "$SCRIPT_DIR/CLAUDE.md" 2>&1 | grep --line-buffered '^{' | tee "$tmpfile" | tee -a "$LOG_FILE" | jq --unbuffered -rj "$stream_text" || true
  OUTPUT=$(cat "$tmpfile")
  rm -f "$tmpfile"

  # Detect rate_limit_event JSON (status: "rejected") — catches 5-hour rate limit
  # Source: EyeRest 20260307 post-mortem — iterations 8-50 wasted by not detecting this
  if echo "$OUTPUT" | jq -e 'select(.type == "rate_limit_event" and .rate_limit_info.status == "rejected")' &>/dev/null; then
    echo "🏭 ⚠️ rate_limit REJECTED 検出。残りイテレーションをスキップ。"
    notify_slack "⚠️ rate_limit rejected。イテレーション $i で停止。"
    break
  fi

  # Detect "Out of extra usage" — only check CC's own text output (not tool_result file content)
  USAGE_TEXT=$(echo "$OUTPUT" | jq -r '
    if .type == "assistant" then (.message.content[]? | select(.type == "text") | .text) // ""
    elif .type == "result" then .result // ""
    elif .type == "system" then .subtype // ""
    else "" end' 2>/dev/null || true)
  if echo "$USAGE_TEXT" | grep -qi "out of extra usage\|out of.*usage\|usage.*exceeded\|hit your limit"; then
    echo "🏭 ⚠️ CC usage 超過検出。残りイテレーションをスキップ。"
    notify_slack "⚠️ CC usage 超過。イテレーション $i で停止。"
    break
  fi

  echo ""
  echo "🏭 Iteration $i 終了: $(date)"

  # Fix #4: 1 US enforcement — warn only, don't reset.
  # CC is instructed to hard-stop after 1 US via CLAUDE.md.
  # Resetting after the fact wastes tokens (CC already did the work).
  # We log a warning for monitoring but trust CLAUDE.md enforcement.
  if [ -f "$SCRIPT_DIR/prd.json" ]; then
    AFTER_PASSES=$(python3 -c "
import json
with open('$SCRIPT_DIR/prd.json') as f: d = json.load(f)
for us in d['userStories']:
    if us['passes']: print(us['id'])
" 2>/dev/null || true)
    NEW_PASSES=""
    while IFS= read -r us_id; do
      if [ -n "$us_id" ] && ! echo "$BEFORE_PASSES" | grep -qF "$us_id"; then
        NEW_PASSES="$NEW_PASSES $us_id"
      fi
    done <<< "$AFTER_PASSES"
    NEW_COUNT=$(echo "$NEW_PASSES" | xargs | wc -w | tr -d ' ')
    if [ "$NEW_COUNT" -gt 1 ]; then
      echo "⚠️ 1 US enforcement: $NEW_COUNT US completed in 1 iteration ($NEW_PASSES) — logged, not reset"
      notify_slack "⚠️ 1 US enforcement: ${NEW_COUNT} US in 1 iteration ($NEW_PASSES). Logged only."
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

    # F3-a: US-001 完了時に RC SK鍵の先行依頼
    while IFS= read -r line; do
      if echo "$line" | grep -q "US-001" && ! echo "$PREV_PASSES" | grep -qF "$line"; then
        APP_NAME=$(python3 -c "import json; print(json.load(open('$SCRIPT_DIR/prd.json')).get('project','unknown'))" 2>/dev/null)
        notify_slack "📱 RC セットアップお願いします（2分）:\n1. https://app.revenuecat.com → + Create new project → 名前: $APP_NAME\n2. Settings → API Keys → + New secret API key\n3. 権限を全て Read & Write → Generate\n4. sk_... をこのチャットに貼ってください"
      fi
    done <<< "$CURR_PASSES"

    PREV_PASSES="$CURR_PASSES"
  fi

  # 5-attempt limit: same US failing 5 times = BLOCKED
  # Source: harrymunro/ralph-wiggum — "If you cannot make a story pass after N attempts: STOP"
  # Source: EyeRest 20260307 post-mortem — prevent infinite retry loops
  CURRENT_US=$(python3 -c "
import json
with open('$SCRIPT_DIR/prd.json') as f: d = json.load(f)
for us in d['userStories']:
    if not us['passes']:
        print(us['id']); break
" 2>/dev/null || echo "UNKNOWN")
  if [ "$CURRENT_US" = "$LAST_FAILED_US" ]; then
    FAIL_COUNT=$((FAIL_COUNT + 1))
  else
    FAIL_COUNT=1
    LAST_FAILED_US="$CURRENT_US"
  fi
  if [ "$FAIL_COUNT" -ge 5 ]; then
    echo "🏭 ❌ $CURRENT_US が5回連続失敗。BLOCKED。"
    notify_slack "❌ $CURRENT_US が5回連続失敗。BLOCKED。手動対応必要。"
    break
  fi

  if echo "$OUTPUT" | grep -q "<promise>COMPLETE</promise>"; then
    echo "🏭 ✅ COMPLETE 検出。全 US 完了。"
    notify_slack "🎉 全 US 完了！App Store に提出しました。"
    exit 0
  fi

  # validate.sh — external quality gate (Source: SonarQube pattern)
  # Fix #3: Only reset the LATEST completed US, not all mentioned in output.
  # validate.sh output mentions US IDs in gate descriptions — partial match caused
  # unrelated US to be reset. Now we only reset the US that was just completed.
  if [ -f "$SCRIPT_DIR/validate.sh" ]; then
    echo "🔍 validate.sh 実行中..."
    VALIDATE_OUTPUT=$("$SCRIPT_DIR/validate.sh" 2>&1) && VALIDATE_EXIT=0 || VALIDATE_EXIT=$?
    echo "$VALIDATE_OUTPUT"
    if [ $VALIDATE_EXIT -ne 0 ]; then
      echo "🔴 validate.sh FAILED (exit=$VALIDATE_EXIT)"
      # Only reset the CURRENT US (highest priority passes:false candidate)
      # Don't re-run validate.sh (expensive) — use the output we already have
      if [ -f "$SCRIPT_DIR/prd.json" ] && echo "$VALIDATE_OUTPUT" | grep -q "❌ FAIL"; then
        RESET_US=$(python3 -c "
import json
with open('$SCRIPT_DIR/prd.json') as f: prd = json.load(f)
# Find the last US that was set to passes:true (most recently completed)
completed = [us for us in prd['userStories'] if us['passes']]
if completed:
    last = completed[-1]
    last['passes'] = False
    last['notes'] = last.get('notes','') + ' [auto-reset by validate.sh]'
    print(f'🔄 {last[\"id\"]} reset to passes:false')
    with open('$SCRIPT_DIR/prd.json','w') as f: json.dump(prd, f, indent=2, ensure_ascii=False)
else:
    print('No US to reset')
" 2>/dev/null || echo "reset failed")
        echo "$RESET_US"
        notify_slack "🔴 validate.sh FAILED at iteration $i — $RESET_US"
      fi
    fi
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
