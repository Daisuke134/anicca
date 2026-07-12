#!/bin/bash
# token-daily-report.sh — 掟4 (2026-07-12, docs/loop-engineering/31-token-audit): daily Anthropic-subscription
# burn report to Dais's Telegram, so an 85%-gone-unnoticed week can never happen again.
# Wake → report → die (single-shot; no persistent session).
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

YESTERDAY=$(TZ=Asia/Tokyo date -v-1d +%Y%m%d)
JSON=$(npx -y ccusage@latest session --since "$YESTERDAY" --json 2>/dev/null || echo '{}')

SUMMARY=$(echo "$JSON" | jq -r '
  (.session // []) | map(select(.agent=="claude")) |
  if length == 0 then "Claude消費: データなし(ccusage失敗 or 消費ゼロ)"
  else
    "Claude(サブスク)消費 since \("'"$YESTERDAY"'"): $\(map(.totalCost)|add|floor) API換算 / \(map(.totalTokens)|add/1000000|floor)Mtok / \(length) sessions\n" +
    "犯人TOP3:\n" +
    (sort_by(-.totalCost) | .[0:3] | map("  $\(.totalCost|floor)  \(.modelsUsed|join(","))  \(.period[0:8])…") | join("\n"))
  end' 2>/dev/null)
[ -z "$SUMMARY" ] && SUMMARY="token日報の生成に失敗(jq/ccusage要確認)"

# Persistent Sonnet sessions (the hidden-socket leak class from the 2026-07-12 incident)
TMUX_COUNT=$(ps aux | grep -c '[t]mux -S /tmp/anicca-.*\.sock' || true)
ZOMBIES=$(ps -axo etime=,command= | grep '[t]mux -S /tmp/anicca-selffix' | awk '$1 ~ /-/ {c++} END {print c+0}')

openclaw message send --channel telegram --target 8547730585 \
  -m "📊 token日報 $(TZ=Asia/Tokyo date +%m/%d)
$SUMMARY
常駐tmuxセッション: ${TMUX_COUNT:-0}本 / 1日超ゾンビselffix: ${ZOMBIES:-0}本
(掟: 常駐禁止・自壊タイマー・引退届が先)" --json
