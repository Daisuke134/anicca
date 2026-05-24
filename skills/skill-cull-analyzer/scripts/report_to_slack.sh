#!/usr/bin/env bash
# Format report JSON → Slack #metrics post.
set -euo pipefail

REPORT="${1:-/tmp/skill_cull_report.json}"
CHANNEL="${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}"   # #metrics

if [ ! -f "$REPORT" ]; then
  echo "ERR: $REPORT not found" >&2
  exit 1
fi

# Build pretty Slack message
TXT=$(jq -r '
  "📊 *Skill 棚卸し週報* (\(.generated_at[0:10]))\n" +
  "\n*== Claude Code (Opus) ==*\n" +
  "🔥 Top: " + (.claude_code.top | map("\(.skill)(\(.count_30d))") | join(" / ")) + "\n" +
  "🪦 削除候補 (3 週未使用 \(.claude_code.kill_candidates | length) 個): " +
    (.claude_code.kill_candidates | map(.skill) | join(", ")) + "\n" +
  "❓ 疑問符 (1-2 回 \(.claude_code.doubt | length) 個): " +
    (.claude_code.doubt | map(.skill) | join(", ")) + "\n" +
  "観測 skill 数: \(.claude_code.total_observed)\n" +
  "\n*== Anicca (OpenClaw) ==*\n" +
  "🔥 Top: " + (.anicca.top | map("\(.skill)(\(.count_30d))") | join(" / ")) + "\n" +
  "🪦 削除候補 (\(.anicca.kill_candidates | length) 個): " +
    (.anicca.kill_candidates | map(.skill) | join(", ")) + "\n" +
  "❓ 疑問符 (\(.anicca.doubt | length) 個): " +
    (.anicca.doubt | map(.skill) | join(", ")) + "\n" +
  (if .inventory then
    "\n*== Inventory ==*\n" +
    "Anicca skill 棚: \(.inventory.anicca_skills_on_disk) 個\n" +
    "最近 SKILL.md 更新: " + ((.inventory.most_recent_touched // []) | map("\(.skill)(\(.added_at))") | join(", "))
  else "" end)
' "$REPORT")

echo "=== Message preview ==="
echo "$TXT"
echo ""

if [ "${DRY_RUN:-0}" = "1" ]; then
  echo "[DRY_RUN] Skipping Slack send"
  exit 0
fi

# Send via openclaw message — write to temp file (avoids shell-escape issues with multiline)
if command -v openclaw &> /dev/null; then
  TMP_MSG=$(mktemp -t skill_cull_msg.XXXXXX)
  printf '%s' "$TXT" > "$TMP_MSG"
  openclaw message send --channel slack --target "channel:${CHANNEL}" --message "$(cat "$TMP_MSG")" 2>&1 | tail -3
  rm -f "$TMP_MSG"
else
  echo "WARN: openclaw CLI not found, skipping send" >&2
fi
