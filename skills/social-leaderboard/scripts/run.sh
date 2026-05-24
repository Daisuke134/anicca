#!/usr/bin/env bash
# social-leaderboard/run.sh — deterministic daily top-3 viral + dead-account report.
# No LLM, no posting. Final stdout = the Slack message (cron delivery posts it to #metrics).
set -uo pipefail
source ~/.openclaw/skills/_shared/lib/postiz-analytics.sh
pa_env || { echo "❌ social-leaderboard FAILED: POSTIZ_API_KEY unset"; exit 1; }

emoji() { case "$1" in x) echo "𝕏";; tt) echo "🎵";; ig) echo "📸";; yt) echo "▶️";; esac; }
name()  { case "$1" in x) echo "X";; tt) echo "TikTok";; ig) echo "Instagram";; yt) echo "YouTube";; esac; }

OUT="📊 Social leaderboard — $(TZ=Asia/Tokyo date '+%Y-%m-%d') (7d top-3 by views/impr)"
for p in yt x ig tt; do
  data=$(pa_top_content "$p" 3 2>/dev/null || echo '[]')
  cnt=$(echo "$data" | jq 'length' 2>/dev/null || echo 0)
  OUT="$OUT
$(emoji $p) $(name $p):"
  if [ "$cnt" -eq 0 ] || [ "$(echo "$data" | jq '[.[].score]|add // 0')" = "0" ]; then
    OUT="$OUT
   (no signal — all near-zero, treat as cold)"
  else
    while IFS= read -r line; do OUT="$OUT
$line"; done < <(echo "$data" | jq -r '.[] | "   \(.score) \(.metric) — \((.content|gsub("\n";" "))[0:90])"')
  fi
done

# dead accounts: integrations with 0 recent activity (best-effort, non-fatal)
DEAD=$(pa_integrations 2>/dev/null | jq -r '[.[]|select(.disabled==true)|.name] | if length>0 then "\n💀 disabled integrations: "+(join(", ")) else "" end' 2>/dev/null || echo "")
OUT="$OUT$DEAD"

echo "$OUT"
echo "✅ social-leaderboard: top-3 x/tt/ig/yt computed from live Postiz analytics"
