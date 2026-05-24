#!/usr/bin/env bash
# MODE=staffer_brief — weekly Mon 9am ET cold-{{profile.lateness.stakeholders.channel}} drip.
# Stays DRY_RUN until LOBBYIST_HIRED=true.
set -euo pipefail
SKILL="${SKILL:-$(cd "$(dirname "$0")/.." && pwd)}"
MODE=staffer_brief
source "$SKILL/scripts/lib/api_clients.sh"
source "$SKILL/scripts/lib/crm.sh"
source "$SKILL/scripts/lib/bill_drafter.sh"
source "$SKILL/scripts/lib/slack_format.sh"
source "$SKILL/scripts/lib/coordination_wall.sh"

DRY="${POLITICIAN_DRY_RUN:-true}"
LOB="${LOBBYIST_HIRED:-false}"

# Ensure CRM is initialised + targets are seeded (idempotent).
# Degrade gracefully: on FUSE-mount sandboxes, SQLite locking can fail. The
# real cron runs on native FS where this is fine; we still want smoke tests
# to surface a useful summary even when the DB layer cannot open.
CRM_OK=true
if ! crm_init >/dev/null 2>&1; then
  CRM_OK=false
fi
if [[ "$CRM_OK" == "true" ]]; then
  crm_load_targets >/dev/null 2>&1 || CRM_OK=false
fi

if [[ "$CRM_OK" == "true" ]]; then
  DUE_LINES="$(crm_offices_due 2>/dev/null || true)"
  DUE_COUNT=$(echo -n "$DUE_LINES" | grep -c . || echo 0)
else
  # Fallback: count entries in target_legislators.json directly.
  DUE_COUNT=$(jq '.targets | length' "$SKILL/data/target_legislators.json" 2>/dev/null || echo 0)
fi

# Pillar rotation — week of year mod 4 picks the pillar.
WK=$(date -u +%V); PILLAR=$(( (10#$WK % 4) + 1 ))

# Queue a K-Dense bill draft request (idempotent: one per pillar per week).
PILLAR_TITLE=$(jq -r ".pillars[] | select(.id == $PILLAR) | .name" "$SKILL/data/pillars.json")
if [[ -n "$PILLAR_TITLE" && "$DRY" == "true" ]]; then
  KDENSE_FILE="$(bill_drafter_queue "$PILLAR" "Model bill — $PILLAR_TITLE — week $WK" 1500 2>/dev/null || echo "[would-queue: $PILLAR_TITLE]")"
fi

QUEUED="$(bill_drafter_status)"

if [[ "$DRY" == "true" || "$LOB" != "true" ]]; then
  COORD_INFO="$(coord_summary 2>/dev/null || echo 'wall=missing')"
  slack_post "✉️ Weekly staffer outreach" \
    "due_offices=$DUE_COUNT pillar=$PILLAR title=\"$PILLAR_TITLE\" kdense_queued=\"$QUEUED\" coord_wall=\"$COORD_INFO\" unlock=DRY (LOBBYIST_HIRED=$LOB POLITICIAN_DRY_RUN=$DRY)"
  exit 0
fi

# LIVE path (LOBBYIST_HIRED=true && POLITICIAN_DRY_RUN=false):
#   1. for each due office, look up primary staffer {{profile.lateness.stakeholders.channel}} from CRM
#   2. compose {{profile.lateness.stakeholders.channel}} body via the K-Dense queued draft + outreach template
#   3. send via Resend API (RESEND_API_KEY)
#   4. record outreach row with sent_at + draft_id
#   5. coordination_blacklist.json check before every send
pol_require_env RESEND_API_KEY "(staffer_brief LIVE requires Resend API key)" || { slack_post "✉️ Weekly staffer outreach" "live_path=blocked reason=RESEND_API_KEY-missing"; exit 0; }

LOBBYIST_FROM_EMAIL="$(python3 -c "import sys,yaml;d=yaml.safe_load(open('$SKILL/data/humans.yaml'));print((d.get('lobbyist') or {}).get('{{profile.lateness.stakeholders.channel}}') or '')")"
LOBBYIST_NAME="$(python3 -c "import sys,yaml;d=yaml.safe_load(open('$SKILL/data/humans.yaml'));print((d.get('lobbyist') or {}).get('{{profile.lateness.stakeholders.senderType}}_name') or '')")"
if [[ -z "$LOBBYIST_FROM_EMAIL" || "$LOBBYIST_FROM_EMAIL" == "None" ]]; then
  slack_post "✉️ Weekly staffer outreach" "live_path=blocked reason=humans.yaml-lobbyist-{{profile.lateness.stakeholders.channel}}-empty"
  exit 0
fi

BLACKLIST_FILE="$SKILL/data/coordination_blacklist.json"
TEMPLATE_FILE="$SKILL/data/outreach_templates/staffer.md"
[[ -f "$TEMPLATE_FILE" ]] || TEMPLATE_FILE=""

SENT_OK=0; SENT_FAIL=0; SKIPPED_BL=0
TS_NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Each due-line is "office_id|member_name|party". Look up that office's primary staffer.
while IFS='|' read -r OFFICE_ID MEMBER PARTY; do
  [[ -z "$OFFICE_ID" ]] && continue
  STAFFER_ROW="$(python3 - "$CRM_DB" "$OFFICE_ID" <<'PY'
import sqlite3, sys
con = sqlite3.connect(sys.argv[1])
row = con.execute(
  "SELECT id,full_name,{{profile.lateness.stakeholders.channel}} FROM staffer WHERE office_id=? ORDER BY id LIMIT 1",
  (int(sys.argv[2]),)
).fetchone()
print("|".join(str(x or "") for x in row) if row else "")
PY
  )"
  [[ -z "$STAFFER_ROW" ]] && continue
  STAFFER_ID="${STAFFER_ROW%%|*}"; rest="${STAFFER_ROW#*|}"
  STAFFER_NAME="${rest%%|*}"; STAFFER_EMAIL="${rest##*|}"
  [[ -z "$STAFFER_EMAIL" || "$STAFFER_EMAIL" == "None" ]] && continue

  # Coordination wall — single enforcement point. Checks both legislator-id
  # (OFFICE_ID) and staffer {{profile.lateness.stakeholders.channel}} (incl. domain glob). Non-zero → skip,
  # don't crash. Slack alert is posted by coord_check_recipient itself.
  if ! coord_check_recipient "$OFFICE_ID" "$STAFFER_EMAIL"; then
    SKIPPED_BL=$((SKIPPED_BL+1)); continue
  fi

  SUBJECT="Re: ${PILLAR_TITLE} — talking points for ${MEMBER}"
  DRAFT_ID="${TS_NOW}-${STAFFER_ID}-p${PILLAR}"
  if [[ -n "$TEMPLATE_FILE" ]]; then
    BODY="$(MEMBER="$MEMBER" PILLAR_TITLE="$PILLAR_TITLE" envsubst < "$TEMPLATE_FILE")"
  else
    BODY="Hi ${STAFFER_NAME%% *},\n\nSharing this week's pillar-${PILLAR} brief on ${PILLAR_TITLE} for ${MEMBER}'s consideration.\n\n— ${LOBBYIST_NAME} (registered LDA lobbyist for Anicca AI Politics LLC)"
  fi

  HTTP_CODE="$(curl -sS -o /tmp/resend_resp_$$ -w '%{http_code}' \
    -X POST 'https://api.resend.com/{{profile.lateness.stakeholders.channel}}s' \
    -H "Authorization: Bearer ${RESEND_API_KEY}" \
    -H 'Content-Type: application/json' \
    --data "$(jq -n --arg from "${LOBBYIST_NAME} <${LOBBYIST_FROM_EMAIL}>" \
                   --arg to   "$STAFFER_EMAIL" \
                   --arg sub  "$SUBJECT" \
                   --arg body "$BODY" \
                   '{from:$from,to:[$to],subject:$sub,text:$body}')" \
    || echo 000)"

  if [[ "$HTTP_CODE" =~ ^2 ]]; then
    SENT_OK=$((SENT_OK+1))
    python3 - "$CRM_DB" "$STAFFER_ID" "$DRAFT_ID" "$TS_NOW" <<'PY'
import sqlite3, sys
con = sqlite3.connect(sys.argv[1])
con.execute(
  "INSERT INTO outreach(staffer_id,channel,draft_id,sent_at) VALUES(?,?,?,?)",
  (int(sys.argv[2]), "{{profile.lateness.stakeholders.channel}}", sys.argv[3], sys.argv[4]),
)
con.execute("UPDATE staffer SET last_contacted_at=? WHERE id=?", (sys.argv[4], int(sys.argv[2])))
con.commit()
PY
  else
    SENT_FAIL=$((SENT_FAIL+1))
    echo "[resend-fail $HTTP_CODE] staffer_id=$STAFFER_ID {{profile.lateness.stakeholders.channel}}=$STAFFER_EMAIL" >&2
  fi
  rm -f /tmp/resend_resp_$$
done <<< "$DUE_LINES"

slack_post "✉️ Weekly staffer outreach" \
  "due_offices=$DUE_COUNT sent=$SENT_OK failed=$SENT_FAIL blacklisted=$SKIPPED_BL pillar=$PILLAR unlock=LIVE"
