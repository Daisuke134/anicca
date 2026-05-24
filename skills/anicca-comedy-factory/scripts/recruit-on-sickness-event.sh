#!/usr/bin/env bash
# comedy-recruit-on-sickness-event — Dais 体調不良検知時の緊急 performer 募集
#
# Usage:
#   recruit-on-sickness-event.sh <city> <date> [budget]
#
# 4 platform 全てに同時投稿 (cloudworks / indeed / timee / taskrabbit)。
# JP city → JP 3 platform / US city → indeed + taskrabbit。
# 結果を Slack で通知 + comedy-recruit-poll-daily が翌日 応募チェック。
#
# stdout: ✅ recruit-on-sickness: <N> platforms drafted

set -uo pipefail

CITY="${1:?}"
DATE="${2:?}"
BUDGET="${3:-¥3,000}"

SKILL_DIR="$HOME/.openclaw/skills/anicca-comedy-factory"
LIB="$SKILL_DIR/scripts/lib/recruit-platform.sh"

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
source "$HOME/.openclaw/skills/sao-content-factory/lib/slack.sh"

PLATFORMS=""
case "$CITY" in
  tokyo|jp|*tokyo*) PLATFORMS="cloudworks timee indeed" ;;
  sf|sfo|la|lax|us|*sf*|*la*) PLATFORMS="indeed taskrabbit"; BUDGET="${3:-\$30}" ;;
  *) PLATFORMS="cloudworks indeed" ;;
esac

drafted=0
for p in $PLATFORMS; do
  bash "$LIB" post "$p" "$CITY" "$DATE" "5" "$BUDGET" 2>&1 | tail -2
  drafted=$((drafted + 1))
done

slack_metrics "*🚨 SICKNESS RECRUIT FIRED!* ${CITY} ${DATE} budget=${BUDGET} platforms=${PLATFORMS}\nDrafts saved to data/recruit/. agent-{{profile.lateness.stakeholders.channel}} に skill load して form submit してください (or future automation)." >/dev/null || true
echo "✅ recruit-on-sickness: $drafted platform(s) drafted"
