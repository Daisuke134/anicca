#!/usr/bin/env bash
# MODE=fec — annual FEC Form 3X (independent-expenditure-only PAC) prep.
# Stays DRY until PAC_FORMED=true AND treasurer signs off.
set -euo pipefail
SKILL="${SKILL:-$(cd "$(dirname "$0")/.." && pwd)}"
MODE=fec
source "$SKILL/scripts/lib/api_clients.sh"
source "$SKILL/scripts/lib/slack_format.sh"

DRY="${POLITICIAN_DRY_RUN:-true}"
PAC="${PAC_FORMED:-false}"

PERIOD="$(date -u +%Y-year-end)"
mkdir -p "$SKILL/data/filings/fec" "$SKILL/data/sign_acks"
DRAFT_PATH="$SKILL/data/filings/fec/${PERIOD}.draft.json"

# Show the api.open.fec curl we'd use to validate committee_id (read-only).
POL_API_DRY=1 pol_fec_committee_totals "C00XXXXXX" 2026 >&2 || true

if [[ "$DRY" == "true" || "$PAC" != "true" ]]; then
  cat >&2 <<EOF
[would-prepare FEC Form 3X for $PERIOD]
  filer: <pending — humans.yaml: treasurer not yet set>
  committee_id: <pending — assigned by FEC after Form 1>
  receipts: <Stripe→PAC ledger sum>
  disbursements: <independent-expenditure ledger sum>
  output: $DRAFT_PATH
  human-signoff sentinel: $SKILL/data/sign_acks/${PERIOD}.signed.json
  efs portal: https://webforms.fec.gov/webforms/form3x/
EOF
  slack_post "📊 FEC Form 3X prep" \
    "period=$PERIOD receipts=stub disbursements=stub unlock=DRY (PAC_FORMED=$PAC POLITICIAN_DRY_RUN=$DRY)"
  exit 0
fi

# LIVE path (PAC_FORMED=true && POLITICIAN_DRY_RUN=false) — never auto-submits.
LEDGER="$HOME/.openclaw/state/politician/pac-ledger.jsonl"
mkdir -p "$(dirname "$LEDGER")"; [[ -f "$LEDGER" ]] || : > "$LEDGER"

YEAR=$(date -u +%Y)
TREASURER_NAME="$(python3 -c "import yaml;d=yaml.safe_load(open('$SKILL/data/humans.yaml'));print((d.get('treasurer') or {}).get('{{profile.lateness.stakeholders.senderType}}_name') or '')")"
COMMITTEE_ID="$(python3 -c "import json,os;p='$HOME/.openclaw/state/anicca.json';d=json.load(open(p)) if os.path.exists(p) else {};print((d.get('politician') or {}).get('fec_committee_id') or '')")"

# Aggregate Form 3X line items from ledger.
AGG_JSON="$(python3 - "$LEDGER" "$YEAR" <<'PY'
import json, sys
agg = {"line_11a_individual": 0.0, "line_11b_other_committees": 0.0,
       "line_17_operating": 0.0, "line_24_indep_expenditures": 0.0,
       "total_receipts": 0.0, "total_disbursements": 0.0, "rows": 0}
with open(sys.argv[1]) as f:
    for ln in f:
        ln = ln.strip()
        if not ln: continue
        try: r = json.loads(ln)
        except Exception: continue
        if not r.get("date","").startswith(sys.argv[2]): continue
        agg["rows"] += 1
        amt = float(r.get("amount_usd") or 0)
        kind = r.get("kind","")
        if kind in agg: agg[kind] += amt
        if kind.startswith("line_1"): agg["total_receipts"] += amt
        if kind.startswith("line_2") or kind.startswith("line_17"): agg["total_disbursements"] += amt
print(json.dumps(agg))
PY
)"

# Persist the structured draft for treasurer review.
echo "$AGG_JSON" | jq --arg p "$PERIOD" --arg t "$TREASURER_NAME" --arg c "$COMMITTEE_ID" \
  '{period:$p, treasurer:$t, committee_id:$c, totals:.}' > "$DRAFT_PATH"

PORTAL_LIVE="https://webforms.fec.gov/webforms/form3x/"
HARNESS_LOG="$SKILL/data/filings/fec/${PERIOD}.harness.log"
if curl -fsS --max-time 5 http://127.0.0.1:9223/json/version >/dev/null 2>&1; then
  curl -fsS -X PUT "http://127.0.0.1:9223/json/new?$(printf '%s' "$PORTAL_LIVE" | jq -sRr @uri)" >"$HARNESS_LOG" 2>&1 || true
  HARNESS_STATUS="opened"
else
  HARNESS_STATUS="harness-unavailable"
fi

RECEIPTS=$(jq -r '.totals.total_receipts' "$DRAFT_PATH")
DISB=$(jq -r '.totals.total_disbursements' "$DRAFT_PATH")
slack_post "📊 FEC Form 3X prep" \
  "period=$PERIOD receipts=\$${RECEIPTS} disbursements=\$${DISB} draft=\"$DRAFT_PATH\" harness=$HARNESS_STATUS sign_status=awaiting-treasurer-click"
