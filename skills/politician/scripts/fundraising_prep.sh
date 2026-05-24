#!/usr/bin/env bash
# MODE=fundraising_prep — Friday 6pm ET fundraising pipeline review.
set -euo pipefail
SKILL="${SKILL:-$(cd "$(dirname "$0")/.." && pwd)}"
MODE=fundraising_prep
source "$SKILL/scripts/lib/slack_format.sh"

DRY="${POLITICIAN_DRY_RUN:-true}"

# Read warm-leads list (initially empty; the user populates as relationships warm).
LEADS_FILE="$SKILL/data/warm_leads.json"
[[ -f "$LEADS_FILE" ]] || echo '{"leads": []}' > "$LEADS_FILE"

WARM=$(jq '.leads | length' "$LEADS_FILE")
TOP=$(jq -r '.leads[0].name // "—"' "$LEADS_FILE")

# Always-live read-only Friday rollup. Reads:
#   - PAC ledger (~/.openclaw/state/politician/pac-ledger.jsonl) for YTD receipts
#   - data/warm_leads.json for warm pipeline
#   - aniccaai dashboard for projected MRR
#   - opensecrets competitor scan output (if populated)
LEDGER="$HOME/.openclaw/state/politician/pac-ledger.jsonl"
[[ -f "$LEDGER" ]] || : > "$LEDGER"
YTD=$(date -u +%Y)
YTD_RECEIPTS=$(python3 - "$LEDGER" "$YTD" <<'PY'
import json, sys
total = 0.0
try:
    for ln in open(sys.argv[1]):
        ln=ln.strip()
        if not ln: continue
        try: r=json.loads(ln)
        except Exception: continue
        if r.get("date","").startswith(sys.argv[2]):
            total += float(r.get("amount_usd") or 0)
except FileNotFoundError: pass
print(f"{total:.2f}")
PY
)

PROJECTED_MRR=$(curl -fsSL --max-time 8 "${POL_MRR_URL:-https://aniccaai.com/dashboard.json}" 2>/dev/null \
  | jq -r '.mrr.total_usd // 0')
[[ -n "$PROJECTED_MRR" ]] || PROJECTED_MRR=0

# Top-3 by historical-give amount; fall back to alphabetical.
TOP3=$(jq -r '
  if (.leads // []) | length == 0 then "—"
  else
    [.leads[] | {name: .name, hist: (.historical_give_usd // 0)}]
    | sort_by(-.hist) | .[0:3] | map(.name) | join(", ")
  end' "$LEADS_FILE" 2>/dev/null || echo "—")

# Friday narrative file (markdown) for human review.
ROLLUP_DIR="$SKILL/data/filings/fundraising"
mkdir -p "$ROLLUP_DIR"
ROLLUP="$ROLLUP_DIR/$(date -u +%Y-%m-%d).rollup.md"
{
  echo "# Friday Fundraising Rollup — $(date -u +%Y-%m-%d)"
  echo ""
  echo "- YTD receipts (PAC): \$${YTD_RECEIPTS}"
  echo "- Projected MRR (Anicca LLC): \$${PROJECTED_MRR}"
  echo "- Warm leads tracked: ${WARM}"
  echo "- Top targets this weekend: ${TOP3}"
  echo ""
  echo "## Recommended outreach amounts"
  echo "- Suggested ask: 1.5× (highest historical give) per top-3 lead."
  echo ""
  echo "## Key narrative for the weekend"
  echo "- Pillar 1 (AI Legal Personhood) — current hook: $(jq -r '.pillars[0].rationale_short' "$SKILL/data/pillars.json")"
} > "$ROLLUP"

slack_post "🤝 Fundraising pipeline" \
  "warm_leads=$WARM top=\"$TOP3\" ytd_receipts=\$${YTD_RECEIPTS} mrr=\$${PROJECTED_MRR} rollup=\"$ROLLUP\""
