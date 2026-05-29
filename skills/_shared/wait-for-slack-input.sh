#!/usr/bin/env bash
# wait-for-slack-input.sh — Anicca skill が Dais に Slack DM で 1 件入力を求めて受取る helper.
#
# 使い方:
#   bash wait-for-slack-input.sh <prompt> <session_key> <regex> [timeout_sec]
#
# 例 (Apple 2FA):
#   CODE=$(bash $ANICCA_HOME/skills/_shared/wait-for-slack-input.sh \
#       "Apple 6桁 認証コード教えて (TAB c95fea63)" \
#       "apple-dev-renew" \
#       "^[0-9]{6}$" \
#       900)
#
# 仕組み (Citations: sutando/docs/slack-bridge.md §63-75 proactive flow +
# Anicca extension awaiting/responses correlation in slack-bridge.py):
#   1. uuid 生成 (= awaiting key)
#   2. results/proactive-${uuid}.txt に prompt 書く
#      → slack-bridge.result_watcher が拾って owner DM に送る (sutando flow)
#   3. awaiting/${uuid}.json に {prompt, regex, sessionKey, created_at} 書く
#      → slack-bridge.handle_message が Dais DM 受信時 oldest-first で regex match
#         → match なら responses/${uuid}.txt に書込 + awaiting/${uuid}.json 消去
#   4. responses/${uuid}.txt 出現を 5s 間隔 polling (max timeout_sec, default 900s = 15min)
#   5. 出現したら content を stdout に echo + exit 0
#      timeout したら exit 1 (stderr に reason)
#
# 失敗モード:
#   - Slack bridge 停止 → proactive 送信されない → Dais 通知無 → timeout
#   - Dais reply が regex match しない → 永久 wait (timeout で抜ける)
#   - bridge launchd kill → restart で awaiting/ ファイル 引継ぎ (idempotent)

set -euo pipefail

PROMPT="${1:?prompt required}"
SESSION_KEY="${2:?session_key required}"
REGEX="${3:?regex required}"
TIMEOUT_SEC="${4:-900}"

BRIDGE_DIR="$HOME/.openclaw/services/slack-bridge"
AWAITING_DIR="$BRIDGE_DIR/awaiting"
RESPONSES_DIR="$BRIDGE_DIR/responses"
RESULTS_DIR="$BRIDGE_DIR/results"

# Pre-flight: bridge running?
if ! pgrep -f "slack-bridge.py" > /dev/null; then
  echo "❌ slack-bridge.py not running. launchctl list | grep slack-bridge" >&2
  exit 2
fi

# uuid 生成 (macOS uuidgen)
UUID="${SESSION_KEY}-$(uuidgen | tr 'A-Z' 'a-z' | cut -c1-8)"
PROACTIVE_FILE="$RESULTS_DIR/proactive-${UUID}.txt"
AWAITING_FILE="$AWAITING_DIR/${UUID}.json"
RESPONSE_FILE="$RESPONSES_DIR/${UUID}.txt"

# Step 2: proactive 書込 (bridge が owner DM に送る)
cat > "$PROACTIVE_FILE" <<EOF
$PROMPT

(Anicca 自動依頼 · sessionKey=${SESSION_KEY} · regex=\`${REGEX}\` · timeout ${TIMEOUT_SEC}s)
EOF

# Step 3: awaiting 書込 (bridge が DM 受信時に regex match)
NOW=$(date +%s)
python3 - "$AWAITING_FILE" "$PROMPT" "$REGEX" "$SESSION_KEY" "$NOW" <<'PY'
import json, sys
out, prompt, regex, sk, ts = sys.argv[1:6]
with open(out, "w") as f:
    json.dump({
        "prompt": prompt,
        "regex": regex,
        "sessionKey": sk,
        "created_at": int(ts),
    }, f, ensure_ascii=False)
PY

echo "  [wait-for-slack-input] awaiting $UUID (regex=$REGEX, timeout ${TIMEOUT_SEC}s)" >&2

# Step 4: polling
DEADLINE=$((NOW + TIMEOUT_SEC))
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  if [ -f "$RESPONSE_FILE" ]; then
    RESPONSE=$(cat "$RESPONSE_FILE")
    # Cleanup
    rm -f "$RESPONSE_FILE" "$PROACTIVE_FILE"
    echo "  [wait-for-slack-input] got match for $UUID" >&2
    echo "$RESPONSE"
    exit 0
  fi
  sleep 5
done

# Timeout — drop awaiting + proactive
rm -f "$AWAITING_FILE" "$PROACTIVE_FILE"
echo "❌ [wait-for-slack-input] timeout ${TIMEOUT_SEC}s for $UUID (regex=$REGEX)" >&2
exit 1
