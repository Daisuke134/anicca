#!/usr/bin/env bash
# comedy-recruit-poll-daily — 14:00 JST 毎日
#
# 全 platform に対し Gmail 通知 + agent-{{profile.lateness.stakeholders.channel}} で dashboard 確認 (将来)。
# 応募者を集約 → Slack に "current applicants" 一覧。
# Dais がリアクションで採用承認 → recruit-platform.sh accept 発動。

set -uo pipefail

SKILL_DIR="$HOME/.openclaw/skills/anicca-comedy-factory"
LIB="$SKILL_DIR/scripts/lib/recruit-platform.sh"

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
source "$HOME/.openclaw/skills/sao-content-factory/lib/slack.sh"

total=0
summary=""
for p in cloudworks indeed timee taskrabbit; do
  out=$(bash "$LIB" poll "$p" 2>&1 | tail -1)
  n=$(echo "$out" | grep -oE '[0-9]+' | head -1 || echo 0)
  total=$((total + n))
  if [ "$n" -gt 0 ]; then
    summary="${summary}\n• ${p}: ${n} applicant(s)"
  fi
done

if [ "$total" -gt 0 ]; then
  slack_metrics "$(printf "%b" "*comedy-recruit-poll-daily:* total=${total} applicant notification(s)${summary}\nGmail 確認 → Anicca screening → Dais 承認 で採用")" >/dev/null || true
fi

echo "✅ recruit-poll-daily: $total applicant notification(s)"
