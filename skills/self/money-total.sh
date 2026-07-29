#!/usr/bin/env bash
LIFE_MANAGER_REPO="${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$LIFE_MANAGER_REPO" ] || { echo "LIFE_MANAGER_REPO could not be resolved" >&2; exit 2; }
export LIFE_MANAGER_REPO
# money-total.sh — thin aggregator (NOT a loop). Reads the two money loops' STATE.md and reports total
# real monthly revenue vs Dais's monthly spend. Never re-computes; just sums the two already-verified
# real numbers. Anti-fake: if either loop reports NA/READ-FAILED, the TOTAL is untrustworthy (NA), never
# a masked partial. Seam: MT_CAPAFY_STATE / MT_LM_STATE / MT_SPEND for tests.
set -uo pipefail
CAP_ST="${MT_CAPAFY_STATE:-$LIFE_MANAGER_REPO/skills/self/capafy-loop/state/STATE.md}"
LM_ST="${MT_LM_STATE:-$LIFE_MANAGER_REPO/skills/self/life-manager-loop/state/STATE.md}"
SPEND="${MT_SPEND:-200}"
val(){ grep -E "^$2:" "$1" 2>/dev/null | awk '{print $2}' | tail -1; }
CAP="$(val "$CAP_ST" capafy_monthly_payout_usd)"; CAP="${CAP:-MISSING}"
LM="$(val "$LM_ST" lm_mrr_usd)"; LM="${LM:-MISSING}"
# a value counts only if it's a clean number; NA/READ-FAILED/MISSING → untrustworthy total
num(){ printf '%s' "$1" | grep -qE '^[0-9]+(\.[0-9]+)?$'; }
if num "$CAP" && num "$LM"; then
  TOTAL="$(python3 -c "print(round(${CAP}+${LM},2))")"
  if awk "BEGIN{exit !($TOTAL>=$SPEND)}" 2>/dev/null; then VERDICT="SUCCESS — \$$TOTAL/mo ≥ spend \$$SPEND (AI earns more than the human spends)"
  elif awk "BEGIN{exit !($TOTAL>0)}" 2>/dev/null; then VERDICT="EARNING \$$TOTAL/mo (need \$$SPEND) — grow demand"
  else VERDICT="\$0/mo — no real revenue yet; bottleneck = DEMAND"; fi
else TOTAL="NA"; VERDICT="UNTRUSTWORTHY — a loop reported NA/READ-FAILED (LM=$LM Capafy=$CAP); fix that loop before trusting the total"; fi
echo "monthly_revenue_total_usd: $TOTAL"
echo "  life_manager_mrr_usd: $LM"
echo "  capafy_monthly_payout_usd: $CAP"
echo "  dais_monthly_spend_usd: $SPEND"
echo "  verdict: $VERDICT"
