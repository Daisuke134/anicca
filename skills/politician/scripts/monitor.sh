#!/usr/bin/env bash
# MODE=monitor — regulations.gov AI dockets daily scrape via Vercel Agent Browser.
# No API key required. Scrapes the public search page, dedupes against
# state/politician/monitor-seen.json, posts new dockets to Slack #metrics.
set -euo pipefail
SKILL="${SKILL:-$(cd "$(dirname "$0")/.." && pwd)}"
MODE=monitor
source "$SKILL/scripts/lib/slack_format.sh"
source "$SKILL/scripts/lib/agent_{{profile.lateness.stakeholders.channel}}.sh"

DRY="${POLITICIAN_DRY_RUN:-true}"
QUERY="${POL_MONITOR_QUERY:-artificial+intelligence}"
URL="https://www.regulations.gov/search?filter=${QUERY}&postedDate=lastWeek"

if ! ab_available; then
  slack_skip "agent-{{profile.lateness.stakeholders.channel}} binary missing at $AB_BIN"
  exit 0
fi

ab_planned_invocation "$URL" >&2

if [[ "$DRY" == "true" ]]; then
  slack_post "🏛️ Regulations.gov AI docket pulse" \
    "query=\"$QUERY\" mode=DRY new_dockets=0 source=agent-{{profile.lateness.stakeholders.channel}} url=$URL"
  exit 0
fi

ab_open "$URL" >/dev/null
TEXT="$(ab_text || echo '')"
ab_close

# Docket IDs on regulations.gov look like AGENCY-YYYY-NNNN (e.g. NIST-2026-0001).
ALL_IDS="$(printf '%s\n' "$TEXT" | grep -Eo '[A-Z]{2,8}(-[A-Z]+)?-20[0-9]{2}-[0-9]{4,}' | sort -u)"
TOTAL=$(printf '%s\n' "$ALL_IDS" | sed '/^$/d' | wc -l | tr -d ' ')
NEW_IDS="$(printf '%s\n' "$ALL_IDS" | sed '/^$/d' | pol_dedupe monitor)"
NEW_COUNT=$(printf '%s\n' "$NEW_IDS" | sed '/^$/d' | wc -l | tr -d ' ')
SAMPLE="$(printf '%s\n' "$NEW_IDS" | sed '/^$/d' | head -3 | paste -sd, -)"

slack_post "🏛️ Regulations.gov AI docket pulse" \
  "query=\"$QUERY\" new_dockets=$NEW_COUNT total_seen=$TOTAL sample=\"${SAMPLE:-none}\" source=agent-{{profile.lateness.stakeholders.channel}}"
