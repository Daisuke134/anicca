#!/usr/bin/env bash
set -uo pipefail
T=$(TZ=Asia/Tokyo date +%Y-%m-%d)
EXP="$HOME/.openclaw/workspace/experience-log/$T.jsonl"
OUT="$HOME/profitable-claude/skills/writer-agent/state/daily-lesson-$T.md"
if [ ! -s "$EXP" ]; then
  echo "EMPTY experience-log: $EXP" >&2
  exit 2
fi
{
  echo "# Anicca Daily Lessons $T"; echo ""
  echo "## Cron self-heals"; jq -r 'select(.kind=="cron_fix") | "- \(.target): \(.payload)"' "$EXP" 2>/dev/null | head -10
  echo "## Money moves"; jq -r 'select(.kind=="earn") | "- \(.target): \(.payload)"' "$EXP" 2>/dev/null | head -5
} > "$OUT"
echo "$OUT"
