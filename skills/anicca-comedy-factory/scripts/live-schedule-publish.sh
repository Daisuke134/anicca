#!/usr/bin/env bash
# comedy-live-schedule-publish — Mon 10 JST 毎週
#
# Flow:
#   1. data/live-events/*.json を集約 (今日 〜 35 日先まで)
#   2. data/schedule.json (公開用) を生成
#   3. Slack #metrics に week ahead 通知
#
# /comedy LP 側は data/schedule.json を fetch して描画する責任。
# (LP 直接 push は branch / git context に依存するので skill scope 外)
#
# stdout last line: ✅ live-schedule-publish: <N> upcoming shows

set -euo pipefail

SKILL_DIR="$HOME/.openclaw/skills/anicca-comedy-factory"
DATA_DIR="$SKILL_DIR/data"
LIVE_DIR="$DATA_DIR/live-events"
SCHEDULE_FILE="$DATA_DIR/schedule.json"

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
source "$HOME/.openclaw/skills/sao-content-factory/lib/slack.sh"

NOW_S=$(date +%s)
H35=$(( 35 * 86400 ))

# Build schedule array: upcoming (date >= today, date <= today+35)
SCHEDULE=$(jq -s --argjson now "$NOW_S" --argjson h35 "$H35" '
  [.[]
    | select(.date)
    | (.date | strptime("%Y-%m-%d") | mktime) as $ts
    | select($ts >= $now and ($ts - $now) <= $h35)
    | {
        city: .city,
        date: .date,
        weekday: .weekday,
        primary_venue: .primary_recommendation.venue,
        rationale: .primary_recommendation.rationale,
        applied: ([.candidates[]?.applied // false] | any)
      }]
  | sort_by(.date)' "$LIVE_DIR"/*.json 2>/dev/null || echo '[]')

# Wrap with metadata
jq -n --argjson s "$SCHEDULE" --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{generated_at: $ts, upcoming: $s}' > "$SCHEDULE_FILE"

N=$(echo "$SCHEDULE" | jq 'length')

# Slack summary
SUMMARY="*comedy-live-schedule-publish:* $N upcoming show(s)"
if [ "$N" -gt 0 ]; then
  while IFS= read -r line; do
    SUMMARY="${SUMMARY}\n${line}"
  done < <(echo "$SCHEDULE" | jq -r '.[] | "• \(.city) \(.date) (\(.weekday)) → \(.primary_venue)\(if .applied then " ✓ applied" else "" end)"')
fi

slack_metrics "$(printf "%b" "$SUMMARY")" >/dev/null || true

echo "✅ live-schedule-publish: $N upcoming show(s)"
