#!/usr/bin/env bash
# anicca-socials orchestrator — daily cron entry point.
set -uo pipefail
SKILL=~/.openclaw/skills/anicca-socials
export SKILL_DIR="$SKILL"

# Load envs (Postiz key from monk-factory, Slack from openclaw)
[ -f ~/anicca-monk-factory/.env ] && set -a && source ~/anicca-monk-factory/.env && set +a
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

echo "🔄 anicca-socials starting at $(date -u +%FT%TZ)"

python3 "$SKILL/scripts/fetch.py" || { echo "❌ fetch failed"; exit 10; }
python3 "$SKILL/scripts/slack.py" || { echo "❌ slack failed"; exit 11; }

echo "✅ anicca-socials done at $(date -u +%FT%TZ)"
