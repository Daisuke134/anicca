#!/usr/bin/env bash
# MODE=bill_tracker — congress.gov AI bill scan via Vercel Agent Browser.
# No API key required. Scrapes the public quick-search page for the 119th
# congress, dedupes against state/politician/bill_tracker-seen.json, posts
# new bills to Slack #metrics.
set -euo pipefail
SKILL="${SKILL:-$(cd "$(dirname "$0")/.." && pwd)}"
MODE=bill_tracker
source "$SKILL/scripts/lib/slack_format.sh"
source "$SKILL/scripts/lib/agent_{{profile.lateness.stakeholders.channel}}.sh"

DRY="${POLITICIAN_DRY_RUN:-true}"
QUERY="${POL_BILL_QUERY:-artificial+intelligence}"
CONGRESS="${POL_CONGRESS:-119}"
URL="https://www.congress.gov/quick-search/legislation?wordsPhrases=${QUERY}&congresses%5B%5D=${CONGRESS}"

if ! ab_available; then
  slack_skip "agent-{{profile.lateness.stakeholders.channel}} binary missing at $AB_BIN"
  exit 0
fi

ab_planned_invocation "$URL" >&2

if [[ "$DRY" == "true" ]]; then
  slack_post "📜 Congress.gov AI bill scan" \
    "query=\"$QUERY\" mode=DRY new_bills=0 on_radar=0 source=agent-{{profile.lateness.stakeholders.channel}} url=$URL"
  exit 0
fi

ab_open "$URL" >/dev/null
TEXT="$(ab_text || echo '')"
ab_close

# Bill IDs on congress.gov: H.R.1234, S.567, H.J.Res.42, S.Con.Res.7, etc.
ALL_IDS="$(printf '%s\n' "$TEXT" \
  | grep -Eo '\b(H\.R\.|S\.|H\.J\.Res\.|S\.J\.Res\.|H\.Con\.Res\.|S\.Con\.Res\.|H\.Res\.|S\.Res\.)[0-9]+' \
  | sort -u)"
TOTAL=$(printf '%s\n' "$ALL_IDS" | sed '/^$/d' | wc -l | tr -d ' ')
NEW_IDS="$(printf '%s\n' "$ALL_IDS" | sed '/^$/d' | pol_dedupe bill_tracker)"
NEW_COUNT=$(printf '%s\n' "$NEW_IDS" | sed '/^$/d' | wc -l | tr -d ' ')

# Cross-reference with target_legislators.json — flag bills mentioning a target.
ON_RADAR=0
TARGETS_JSON="$SKILL/data/target_legislators.json"
if [[ -f "$TARGETS_JSON" && -n "$NEW_IDS" ]]; then
  ON_RADAR=$(POL_PAGE_TEXT="$TEXT" python3 - "$TARGETS_JSON" <<'PY'
import json, sys, os
text = os.environ.get("POL_PAGE_TEXT", "")
targets = json.load(open(sys.argv[1]))
names = {t["name"] for t in targets.get("targets", [])}
hits = sum(1 for n in names if n.split()[-1] in text)
print(hits)
PY
)
fi

SAMPLE="$(printf '%s\n' "$NEW_IDS" | sed '/^$/d' | head -3 | paste -sd, -)"
slack_post "📜 Congress.gov AI bill scan" \
  "new_bills=$NEW_COUNT total_seen=$TOTAL on_radar=$ON_RADAR sample=\"${SAMPLE:-none}\" source=agent-{{profile.lateness.stakeholders.channel}}"
