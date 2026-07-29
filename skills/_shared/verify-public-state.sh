#!/usr/bin/env bash
# verify-public-state.sh — HARD RULE #14 + #8 遵守の核心 helper.
#
# 嘘 fix 防止: API の 200 OK を信じない。 必ず view-side で確認する。
# 例: Uber merchant menu 編集 API が 200 返しても、 view-online URL で
#     実際に snapshot grep して期待文字列を hit するまで「直った」と言わない。
#
# Usage:
#   bash verify-public-state.sh <target_url> <expected_regex> [count_min] [count_max]
#
# Args:
#   target_url     — view-side URL (e.g. https://www.ubereats.com/tokyo/...)
#   expected_regex — extended regex (egrep) で snapshot 内に hit すべきパターン
#   count_min      — hit 最低件数 (default: 1)
#   count_max      — hit 最大件数 (default: 無限大)
#
# Exit codes:
#   0 — verified (hit count_min 以上 count_max 以下)
#   1 — failed (hit 不足) + diff 詳細 stderr 出力
#   2 — camofox 失敗 (network / tab create error)
#   3 — args error
#
# Behavior:
#   1. camofox-browser :9377 で新規 tab open (isolated session で cache 影響なし)
#   2. snapshot 取得 + grep
#   3. hit count 検証
#   4. fail 時: Slack #metrics に diff + URL + screenshot リンク post
#   5. tab close で cleanup
#
# Citations (HARD RULE 出典):
#   - .claude/rules/verification.md HARD RULE #8 + #14
#   - memory/feedback_verify_every_output_before_declaring_done.md
#   - superpowers:verification-before-completion 5-step gate (IDENTIFY/RUN/READ/VERIFY/CLAIM)

set -uo pipefail

URL="${1:-}"
REGEX="${2:-}"
COUNT_MIN="${3:-1}"
COUNT_MAX="${4:-9999}"

if [ -z "$URL" ] || [ -z "$REGEX" ]; then
  echo "Usage: $0 <target_url> <expected_regex> [count_min] [count_max]" >&2
  exit 3
fi

CAMOFOX="http://localhost:9377"
USER_ID="anicca"
SESSION_KEY="verify-public-$(date +%s)-$$"

# 1. camofox health check
if ! curl -sS -m 3 "$CAMOFOX/health" > /dev/null 2>&1; then
  echo "[verify] ❌ camofox :9377 unreachable" >&2
  exit 2
fi

# 2. open tab
TAB_RESP=$(curl -sS -X POST "$CAMOFOX/tabs" \
  -H 'Content-Type: application/json' \
  --data-raw "$(printf '{"url":"%s","userId":"%s","sessionKey":"%s"}' "$URL" "$USER_ID" "$SESSION_KEY")")
TID=$(printf '%s' "$TAB_RESP" | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('tabId',''))" 2>/dev/null)

if [ -z "$TID" ]; then
  echo "[verify] ❌ tab create failed: $TAB_RESP" >&2
  exit 2
fi

# Cleanup function
cleanup() {
  curl -sS -X DELETE "$CAMOFOX/tabs/$TID?userId=$USER_ID" > /dev/null 2>&1 || true
}
trap cleanup EXIT

# 3. wait for page load (JS-heavy sites need time)
sleep 6

# 4. snapshot
SNAP=$(curl -sS -m 30 "$CAMOFOX/tabs/$TID/snapshot?userId=$USER_ID&sessionKey=$SESSION_KEY" \
  | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('snapshot',''))" 2>/dev/null)

if [ -z "$SNAP" ]; then
  echo "[verify] ❌ snapshot empty" >&2
  exit 2
fi

# 5. grep + count
HIT_COUNT=$(echo "$SNAP" | grep -cE "$REGEX" || true)

# 6. verdict
if [ "$HIT_COUNT" -ge "$COUNT_MIN" ] && [ "$HIT_COUNT" -le "$COUNT_MAX" ]; then
  echo "[verify] ✅ OK · pattern '$REGEX' hit $HIT_COUNT times (range $COUNT_MIN-$COUNT_MAX)"
  exit 0
fi

# 7. FAIL — record + report
FAIL_LOG="/tmp/verify-public-state-fail-$(date +%s).log"
{
  echo "=== verify-public-state.sh FAIL ==="
  echo "URL: $URL"
  echo "Pattern: $REGEX"
  echo "Hit count: $HIT_COUNT"
  echo "Expected range: $COUNT_MIN-$COUNT_MAX"
  echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo ""
  echo "=== snapshot (first 200 lines) ==="
  echo "$SNAP" | head -200
  echo ""
  echo "=== grep context (any partial matches) ==="
  echo "$SNAP" | grep -iE "$(echo "$REGEX" | tr '|' '\n' | head -3 | tr '\n' '|')" | head -10 || echo "(no partial matches)"
} > "$FAIL_LOG"

echo "[verify] ❌ FAIL · expected $COUNT_MIN-$COUNT_MAX hits, got $HIT_COUNT" >&2
echo "[verify] log: $FAIL_LOG" >&2

# 8. Slack #metrics post (best-effort)
LIFE_MANAGER_STATE_HOME="${LIFE_MANAGER_STATE_HOME:-$HOME/.local/state/life-manager}"
if [ -n "${SLACK_BOT_TOKEN:-}" ] || [ -f "$LIFE_MANAGER_STATE_HOME/.env" ]; then
  set -a; source "$LIFE_MANAGER_STATE_HOME/.env" 2>/dev/null; set +a
  python3 - "${SLACK_BOT_TOKEN:-}" "$URL" "$REGEX" "$HIT_COUNT" "$COUNT_MIN" "$COUNT_MAX" "$FAIL_LOG" <<'PYALERT' 2>/dev/null || true
import os, sys, json, urllib.request
tok, url, regex, hits, mn, mx, log = sys.argv[1:8]
msg = {
  "channel": os.environ.get("SLACK_CHANNEL_ID", ""),
  "text": f":warning: verify-public-state FAIL · URL `{url[:80]}` · pattern `{regex[:60]}` · got {hits} hits, expected {mn}-{mx} · log {log}",
}
try:
  if not msg["channel"]:
    raise ValueError("SLACK_CHANNEL_ID is not configured")
  req = urllib.request.Request("https://slack.com/api/chat.postMessage",
    data=json.dumps(msg).encode(),
    headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
    method="POST")
  urllib.request.urlopen(req, timeout=10)
except Exception as e:
  print(f"  slack post err: {e}", file=sys.stderr)
PYALERT
fi

exit 1
