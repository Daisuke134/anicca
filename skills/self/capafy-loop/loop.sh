#!/usr/bin/env bash
# capafy-loop/loop.sh — ONE no-human wake of the CAPAFY money loop (GLVS / HARD 0.40). Money = REAL
# Capafy $ monthly payout (to Dais's BANK). Split out of the (wrongly-combined) lm-capafy-loop —
# 1 product = 1 loop, like earn/clip vs earn/affiliate. Anti-fake invariants (VCSDD-proven):
#   INV-1 error body → NA, NEVER masked-$0.  INV-2 one fetch/surface.  INV-3 dollars not counts.
#   INV-4 NA → FAIL-SAFE status.  INV-5 assert the publish loop RAN ≤2d (6-week-death guard) + write a
#   selfheal-request on any HEAL so the loop self-fixes.  Monthly = LATEST payout month (not max-ever).
# Seams: CAPAFY_TEST=1 + CAPAFY_FIXTURE=<dir>, CAPAFY_LOGFILE, CAPAFY_DIR, CAPAFY_REQ.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIR="${CAPAFY_DIR:-$HERE}"; STATE_MD="$DIR/state/STATE.md"; mkdir -p "$DIR/state"
set -a; . ~/.openclaw/.env 2>/dev/null; set +a
REQ="${CAPAFY_REQ:-$HOME/.openclaw/state/capafy-loop-selfheal-request.json}"
LP="${CAPAFY_LOGFILE:-$HOME/.openclaw/skills/capafy-autopublish/state/daily_loop.log}"
fetch(){ local name="$1" url="$2"; shift 2
  if [ "${CAPAFY_TEST:-}" = "1" ] && [ -n "${CAPAFY_FIXTURE:-}" ]; then cat "$CAPAFY_FIXTURE/$name.json" 2>/dev/null || echo '{}'; return 0; fi
  curl -s --max-time 20 "$@" "$url" 2>/dev/null; }
HEAL=""; add_heal(){ HEAL="$HEAL$1; "; }
CAP_TOK="$(python3 -c "import json;print(json.load(open('$HOME/.openclaw/skills/capafy-autopublish/vendor/capafy-publisher/config.json'))['access_token'])" 2>/dev/null || echo)"

# auth
[ "$(printf '%s' "$(fetch cap_acct https://api.capafy.ai/agent/account -H "Authorization: Bearer $CAP_TOK")" | python3 -c "import json,sys;print(json.load(sys.stdin).get('code','x'))" 2>/dev/null||echo x)" = "0" ] || add_heal "CAPAFY-AUTH-DOWN → re-login (login-init→gog OTP→login-verify)"
# monthly payout = LATEST month (INV-1 error→NA; FIND-015 latest not max)
CAP_MO="$(printf '%s' "$(fetch cap_payout https://api.capafy.ai/agent/developer/payout-record -H "Authorization: Bearer $CAP_TOK")" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    if d.get('code',0)!=0 or 'data' not in d: print('NA'); raise SystemExit
    recs=d['data'] if isinstance(d['data'],list) else []
    if not recs: print('0.0'); raise SystemExit
    latest=max(recs,key=lambda r:str(r.get('payoutMonth','')))
    print(round(float(latest.get('amount',0) or 0),2))
except SystemExit: pass
except Exception: print('NA')" 2>/dev/null||echo NA)"
# 3d net = labeled leading indicator (NOT the monthly figure)
CAP_3D="$(printf '%s' "$(fetch cap_trend https://api.capafy.ai/agent/sales/trend -H "Authorization: Bearer $CAP_TOK")" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    if d.get('code',0)!=0 or 'data' not in d: print('NA'); raise SystemExit
    days=d['data'].get('data'); print(round(float(sum(x.get('netRevenue',0) for x in days)),2)) if isinstance(days,list) else print('NA')
except SystemExit: pass
except Exception: print('NA')" 2>/dev/null||echo NA)"
# A4 sales reconcile: mirror server sales/trend + payout-info into the DEDICATED capafy ledger
# (bank revenue, NOT on-chain — kept out of the on-chain realized reader) and surface the PENDING
# seller balance the old report missed (it only read monthly PAID payout = $0, hiding a real sale).
REC_LEDGER="$DIR/state/capafy-earn-ledger.jsonl"
if [ "${CAPAFY_TEST:-}" = "1" ]; then
  REC_JSON="$(python3 "$HERE/capafy_earn_reconcile.py" --ledger "$REC_LEDGER" --sales-json "${CAPAFY_FIXTURE:-/nonexistent}/cap_trend.json" --payout-json "${CAPAFY_FIXTURE:-/nonexistent}/cap_payout.json" 2>/dev/null || echo '{}')"
else
  REC_JSON="$(python3 "$HERE/capafy_earn_reconcile.py" --ledger "$REC_LEDGER" --lookback-days 14 2>/dev/null || echo '{}')"
fi
read -r CAP_BAL CAP_REALIZED CAP_LIFE CAP_ORD <<EOF_REC
$(printf '%s' "$REC_JSON" | python3 -c "import json,sys
try:
    d=json.load(sys.stdin); print(d.get('balance_payout_usd','NA'),d.get('total_payout_usd','NA'),d.get('lifetime_gross_usd','NA'),d.get('lifetime_orders','NA'))
except Exception: print('NA NA NA NA')" 2>/dev/null || echo 'NA NA NA NA')
EOF_REC
CAP_BAL="${CAP_BAL:-NA}"; CAP_REALIZED="${CAP_REALIZED:-NA}"; CAP_LIFE="${CAP_LIFE:-NA}"; CAP_ORD="${CAP_ORD:-NA}"

# publish loop freshness (INV-5, 6-week-death guard)
if [ -f "$LP" ]; then AGE=$(( ($(date +%s) - $(stat -f %m "$LP" 2>/dev/null||echo 0)) / 86400 )); [ "$AGE" -le 2 ] || add_heal "CAPAFY-LOOP-STALE(${AGE}d) → run daily_loop.sh"; else add_heal "CAPAFY-LOOP-NEVER-RAN → wire+fire daily_loop.sh"; fi

PREV="$(grep -E '^capafy_monthly_payout_usd:' "$STATE_MD" 2>/dev/null | awk '{print $2}' | tail -1)"; PREV="${PREV:-n/a}"
if [ -n "$HEAL" ]; then STATUS="HEAL-NEEDED — ${HEAL}(monthly \$$CAP_MO)"
elif [ "$CAP_MO" = "NA" ]; then STATUS="READ-FAILED — Capafy monthly cannot be read; DO NOT trust"
elif awk "BEGIN{exit !($CAP_MO>0)}" 2>/dev/null; then STATUS="EARNING \$$CAP_MO/mo — grow: clone the current top sellers' pricing/copy, retire dead listings, publish proven niches"
elif awk "BEGIN{exit !(\"$CAP_BAL\"!=\"NA\" && $CAP_BAL>0)}" 2>/dev/null; then STATUS="SALE(S) LANDED, \$0 PAID OUT yet — \$$CAP_LIFE gross lifetime ($CAP_ORD order/s), \$$CAP_BAL seller balance PENDING (unpaid to bank), realized payout \$$CAP_REALIZED. NOT 'earned' until totalPayout>0. Grow: more competitive listings + trigger first payout"
else STATUS="NO Capafy revenue yet (\$0/mo) — bottleneck = our listings aren't competitive/discoverable (top sellers DO sell); fix supply-QUALITY not volume"; fi
if [ -n "$HEAL" ]; then mkdir -p "$(dirname "$REQ")"; printf '{"loop":"capafy","ts":"%s","heal":"%s"}\n' "$(date -u +%FT%TZ)" "${HEAL//\"/}" > "$REQ"; else rm -f "$REQ" 2>/dev/null||true; fi
TMP="$STATE_MD.tmp.$$"
{
  echo "# Capafy money loop — STATE (GLVS, no-human, money → Dais bank)"
  echo "goal: real Capafy \$ monthly payout, growing. Real \$ only; never masked-error-as-0; monthly = latest payout month."
  echo "last_wake_utc: $(date -u +%FT%TZ)"
  echo "heal_first: ${HEAL:-all healthy (auth ✓, publish loop ran ≤2d ✓)}"
  echo "capafy_monthly_payout_usd: $CAP_MO"
  echo "prev_capafy_monthly_payout_usd: $PREV"
  echo "capafy_3d_net_usd_leading: $CAP_3D"
  echo "capafy_seller_balance_pending_usd: $CAP_BAL"
  echo "capafy_realized_payout_usd: $CAP_REALIZED"
  echo "capafy_lifetime_gross_usd: $CAP_LIFE"
  echo "capafy_lifetime_orders: $CAP_ORD"
  echo "status: $STATUS"
  echo "selfheal_request: ${HEAL:+written→$REQ}${HEAL:-none}"
  echo "next: HEAL-NEEDED→fix (a selfheal-request was written); READ-FAILED→recompute; else ACT: clone a current top seller's pricing/structure into one new listing OR retire a dead one OR publish one via daily_loop.sh; VERIFY a real subscriber / status=4, not just 'published'."
} > "$TMP" && mv "$TMP" "$STATE_MD"
echo "[capafy-loop] monthly=\$$CAP_MO 3d_lead=\$$CAP_3D | heal=${HEAL:-none} | $STATUS"
