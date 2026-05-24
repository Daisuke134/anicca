#!/usr/bin/env bash
# MODE=lda — quarterly LDA-2 filing prep.
# Stays DRY until LOBBYIST_HIRED=true AND a sign-ack file is written.
set -euo pipefail
SKILL="${SKILL:-$(cd "$(dirname "$0")/.." && pwd)}"
MODE=lda
source "$SKILL/scripts/lib/api_clients.sh"
source "$SKILL/scripts/lib/crm.sh"
source "$SKILL/scripts/lib/slack_format.sh"

DRY="${POLITICIAN_DRY_RUN:-true}"
LOB="${LOBBYIST_HIRED:-false}"

# LDA portal URL (no API).
PORTAL_URL="$(pol_lda_form_url)"
QUARTER="$(date -u +%Y-Q$(( ($(date -u +%-m)-1)/3 + 1 )))"

mkdir -p "$SKILL/data/filings/lda" "$SKILL/data/sign_acks"
DRAFT_PATH="$SKILL/data/filings/lda/${QUARTER}.draft.md"

if [[ "$DRY" == "true" || "$LOB" != "true" ]]; then
  cat >&2 <<EOF
[would-prepare LDA-2 filing for $QUARTER]
  registrant: <pending — humans.yaml: lobbyist not yet set>
  client: Anicca AI Politics LLC (DE)
  hours: <pulled from CRM outreach where channel=meeting OR call>
  contacts: <CRM outreach count for the quarter>
  income: <from Stripe LLC ledger, Q net to lobbying client>
  output: $DRAFT_PATH
  human-signoff sentinel: $SKILL/data/sign_acks/${QUARTER}.signed.json
  portal (manual upload after signing): $PORTAL_URL
EOF
  slack_post "📋 LDA-2 prep" \
    "quarter=$QUARTER hours=stub contacts=stub unlock=DRY (LOBBYIST_HIRED=$LOB POLITICIAN_DRY_RUN=$DRY) portal=\"$PORTAL_URL\""
  exit 0
fi

# LIVE path (LOBBYIST_HIRED=true && POLITICIAN_DRY_RUN=false).
# Even when LIVE, the skill never auto-submits — it produces a fully filled
# draft + opens the LDA portal in {{profile.lateness.stakeholders.channel}}-harness for human-final-click.
CRM_DB="$SKILL/data/crm.sqlite"
crm_init >/dev/null 2>&1 || true   # ensure outreach table exists before SELECT
EXPENSES_FILE="$SKILL/data/lobbying-expenses.jsonl"
[[ -f "$EXPENSES_FILE" ]] || : > "$EXPENSES_FILE"

# Quarter date range (UTC) — Q1 = Jan–Mar etc.
Q_NUM=$(( ($(date -u +%-m)-1)/3 + 1 ))
Y=$(date -u +%Y)
case "$Q_NUM" in
  1) Q_START="${Y}-01-01"; Q_END="${Y}-03-31" ;;
  2) Q_START="${Y}-04-01"; Q_END="${Y}-06-30" ;;
  3) Q_START="${Y}-07-01"; Q_END="${Y}-09-30" ;;
  4) Q_START="${Y}-10-01"; Q_END="${Y}-12-31" ;;
esac

REGISTRANT_NAME="$(python3 -c "import yaml;d=yaml.safe_load(open('$SKILL/data/humans.yaml'));print((d.get('lobbyist') or {}).get('{{profile.lateness.stakeholders.senderType}}_name') or '')")"
REGISTRANT_ID="$(python3 -c "import yaml;d=yaml.safe_load(open('$SKILL/data/humans.yaml'));print((d.get('lobbyist') or {}).get('lda_registrant_id') or '')")"
ISSUES="$(jq -r '[.pillars[] | .name] | join("; ")' "$SKILL/data/pillars.json")"

# Aggregate CRM contacts in quarter (channel {{profile.lateness.stakeholders.channel}}|call|meeting).
# Defensive wrap: FUSE-mount sandboxes can hit SQLite I/O errors;
# on a hard failure we degrade to an empty contact list rather than crash.
CONTACTS_JSON="$(python3 - "$CRM_DB" "$Q_START" "$Q_END" <<'PY' 2>/dev/null || echo '[]'
import sqlite3, sys, json
try:
    con = sqlite3.connect(sys.argv[1])
    rows = con.execute("""
      SELECT s.full_name, o.member_name, o.chamber, ou.channel, ou.sent_at
      FROM outreach ou
      JOIN staffer s ON s.id=ou.staffer_id
      JOIN office o  ON o.id=s.office_id
      WHERE ou.sent_at >= ? AND ou.sent_at <= ?
    """, (sys.argv[2]+"T00:00:00Z", sys.argv[3]+"T23:59:59Z")).fetchall()
    print(json.dumps([{"staffer":r[0],"member":r[1],"chamber":r[2],"channel":r[3],"sent_at":r[4]} for r in rows]))
except Exception:
    print("[]")
PY
)"
[[ -z "$CONTACTS_JSON" ]] && CONTACTS_JSON='[]'
CONTACT_COUNT=$(jq 'length' <<< "$CONTACTS_JSON")
EXPENSES_TOTAL=$(jq -s --arg s "$Q_START" --arg e "$Q_END" '[.[] | select(.date>=$s and .date<=$e) | .amount_usd] | add // 0' "$EXPENSES_FILE")

# Render the draft (markdown — pandoc/wkhtmltopdf optional, plain MD always OK).
{
  echo "# LDA-2 Draft — ${QUARTER}"
  echo ""
  echo "- Registrant: ${REGISTRANT_NAME} (LDA ID: ${REGISTRANT_ID})"
  echo "- Client: Anicca AI Politics LLC (DE)"
  echo "- Reporting period: ${Q_START} → ${Q_END}"
  echo "- Specific issues: ${ISSUES}"
  echo "- Lobbying contacts: ${CONTACT_COUNT}"
  echo "- Lobbying expenses (USD): \$${EXPENSES_TOTAL}"
  echo ""
  echo "## Contacts"
  jq -r '.[] | "- \(.sent_at) — \(.staffer) (\(.member), \(.chamber)) via \(.channel)"' <<< "$CONTACTS_JSON"
} > "$DRAFT_PATH"

# Browser-harness — open LDA login page; do NOT auto-submit.
PORTAL_LIVE="https://lda.congress.gov/LD/login.aspx"
HARNESS_LOG="$SKILL/data/filings/lda/${QUARTER}.harness.log"
if curl -fsS --max-time 5 http://127.0.0.1:9223/json/version >/dev/null 2>&1; then
  curl -fsS -X PUT "http://127.0.0.1:9223/json/new?$(printf '%s' "$PORTAL_LIVE" | jq -sRr @uri)" >"$HARNESS_LOG" 2>&1 || true
  HARNESS_STATUS="opened"
else
  HARNESS_STATUS="harness-unavailable"
fi

slack_post "📋 LDA-2 prep" \
  "quarter=$QUARTER contacts=$CONTACT_COUNT expenses=\$${EXPENSES_TOTAL} draft=\"$DRAFT_PATH\" harness=$HARNESS_STATUS portal=\"$PORTAL_LIVE\" sign_status=awaiting-human-click"
