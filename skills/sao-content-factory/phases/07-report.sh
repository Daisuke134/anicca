#!/usr/bin/env bash
# 07-report.sh — Build Slack summary line and emit on stdout
# (Slack post itself happens via the SKILL.md cron-delivery layer that picks up our stdout)
set -euo pipefail

SKILL_DIR="${SKILL_DIR:-$HOME/.openclaw/skills/sao-content-factory}"
[ -n "${VERSION_DIR:-}" ] || { echo "VERSION_DIR not set" >&2; exit 2; }
ENTITY_LOCAL="$VERSION_DIR/docs/entity.json"

TITLE=$(jq -r '.title' "$ENTITY_LOCAL")
ENTITY_NAME="${ENTITY:-unknown}"

POST_IDS=$(cat "$VERSION_DIR/docs/postiz_post_ids.txt" 2>/dev/null | tr '\n' ' ' || echo "")
JOB_SENT_FLAG="$SKILL_DIR/state/${ENTITY}-job-sent"
JOB_LINE=""
if [ -f "$JOB_SENT_FLAG" ]; then
  JOB_LINE=" | 📧 job {{profile.lateness.stakeholders.channel}}: $(cat "$JOB_SENT_FLAG")"
fi

# Use compact summary line that fits Slack
SUMMARY="🎬 SAO ${JST_DATE} — *${TITLE}* (${ENTITY_NAME}) → Postiz IDs: \`${POST_IDS}\`${JOB_LINE} | reel: \`${VERSION_DIR}/output/reel_9x16_en.mp4\`"
echo "$SUMMARY"
