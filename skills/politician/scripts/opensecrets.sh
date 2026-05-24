#!/usr/bin/env bash
# MODE=opensecrets — weekly competitor AI PAC scan via Vercel Agent Browser.
# No API key required. For each competitor, hits the public PAC-lookup page
# at opensecrets.org and records which orgs surface PAC matches. Dedupes the
# {competitor}:{first-PAC-name} fingerprint against state/politician/opensecrets-seen.json.
set -euo pipefail
SKILL="${SKILL:-$(cd "$(dirname "$0")/.." && pwd)}"
MODE=opensecrets
source "$SKILL/scripts/lib/slack_format.sh"
source "$SKILL/scripts/lib/agent_{{profile.lateness.stakeholders.channel}}.sh"

DRY="${POLITICIAN_DRY_RUN:-true}"
COMPETITORS=(OpenAI Anthropic Microsoft Google Meta IBM)
LOOKUP="https://www.opensecrets.org/political-action-committees-pacs/lookup"

if ! ab_available; then
  slack_skip "agent-{{profile.lateness.stakeholders.channel}} binary missing at $AB_BIN"
  exit 0
fi

for org in "${COMPETITORS[@]}"; do
  url="${LOOKUP}?name=${org// /+}"
  ab_planned_invocation "$url" >&2
done

if [[ "$DRY" == "true" ]]; then
  slack_post "💸 Competitor AI PAC scan" \
    "mode=DRY queried=${#COMPETITORS[@]} matched=\"\" source=agent-{{profile.lateness.stakeholders.channel}}"
  exit 0
fi

MATCHED=""
NEW_HITS=""
for org in "${COMPETITORS[@]}"; do
  url="${LOOKUP}?name=${org// /+}"
  ab_open "$url" >/dev/null
  TEXT="$(ab_text || echo '')"
  ab_close
  # Heuristic: a PAC result page contains "PAC" tokens and the org name in
  # close proximity. We extract the first ALL-CAPS-ish line containing PAC
  # as a coarse fingerprint per org.
  FP="$(printf '%s\n' "$TEXT" | grep -i 'PAC' | grep -i -F "$org" | head -1 | tr -s '[:space:]' ' ' | cut -c1-120)"
  if [[ -n "$FP" ]]; then
    MATCHED="$MATCHED$org,"
    printf '%s\n' "${org}::${FP}"
  fi
done | pol_dedupe opensecrets > /tmp/.pol_os_new.$$ || true
NEW_HITS="$(cat /tmp/.pol_os_new.$$ 2>/dev/null | wc -l | tr -d ' ')"
rm -f /tmp/.pol_os_new.$$ 2>/dev/null || true

slack_post "💸 Competitor AI PAC scan" \
  "queried=${#COMPETITORS[@]} matched=\"${MATCHED%,}\" new_hits=$NEW_HITS source=agent-{{profile.lateness.stakeholders.channel}}"
