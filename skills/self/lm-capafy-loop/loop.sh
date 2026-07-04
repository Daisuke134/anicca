#!/usr/bin/env bash
# lm-capafy-loop/loop.sh — ONE no-human wake of the LM + Capafy MONEY LOOP (GLVS / HARD 0.40).
# Money = REAL Stripe LM $ MRR (monthly) + REAL Capafy $ monthly payout (to Dais's BANK). Anti-fake:
#   INV-1 error body → NA, NEVER 0 (masking is the cardinal sin).  INV-2 one fetch/surface (no TOCTOU).
#   INV-3 dollars not counts; $0 subs → $0.  INV-4 NA → FAIL-SAFE status.  INV-5 assert Capafy publish
#   loop RAN recently (6-week-death guard) + write a selfheal-request on any HEAL so the loop self-fixes.
#   INV-6 monthly is compared to monthly (LM MRR + Capafy PAYOUT month) — never sum mismatched windows.
# Seams (tests never touch prod): LMCAP_TEST=1 + LMCAP_FIXTURE=<dir> (API bodies), LMCAP_LOGFILE (freshness
#   file), LMCAP_DIR (state), LMCAP_REQ (selfheal-request path). STRIPE key mode enforced.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIR="${LMCAP_DIR:-$HERE}"; STATE_MD="$DIR/state/STATE.md"; mkdir -p "$DIR/state"
set -a; . ~/.openclaw/.env 2>/dev/null; set +a
REQ="${LMCAP_REQ:-$HOME/.openclaw/state/lm-capafy-selfheal-request.json}"
LP="${LMCAP_LOGFILE:-$HOME/.openclaw/skills/capafy-autopublish/state/daily_loop.log}"

fetch(){ local name="$1" url="$2"; shift 2
  if [ "${LMCAP_TEST:-}" = "1" ] && [ -n "${LMCAP_FIXTURE:-}" ]; then cat "$LMCAP_FIXTURE/$name.json" 2>/dev/null || echo '{}'; return 0; fi
  curl -s --max-time 20 "$@" "$url" 2>/dev/null
}
HEAL=""; add_heal(){ HEAL="$HEAL$1; "; }
CAP_TOK="$(python3 -c "import json;print(json.load(open('$HOME/.openclaw/skills/capafy-autopublish/vendor/capafy-publisher/config.json'))['access_token'])" 2>/dev/null || echo)"

# Stripe key-mode guard (FIND-009)
case "${STRIPE_SECRET_KEY:-}" in sk_live_*) : ;; "") add_heal "STRIPE-KEY-MISSING";; *) add_heal "STRIPE-KEY-NOT-LIVE";; esac

# Capafy auth (health) — same body drives nothing else, but is a distinct surface
CAP_ACCT="$(fetch cap_acct https://api.capafy.ai/agent/account -H "Authorization: Bearer $CAP_TOK")"
[ "$(printf '%s' "$CAP_ACCT" | python3 -c "import json,sys;print(json.load(sys.stdin).get('code','x'))" 2>/dev/null||echo x)" = "0" ] || add_heal "CAPAFY-AUTH-DOWN → re-login (login-init→gog OTP→login-verify)"

# Capafy MONTHLY revenue from payout-record (real month, apples-to-apples with MRR) (FIND-012)
CAP_PAY="$(fetch cap_payout https://api.capafy.ai/agent/developer/payout-record -H "Authorization: Bearer $CAP_TOK")"
CAP_MO="$(printf '%s' "$CAP_PAY" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    if d.get('code',0)!=0 or 'data' not in d: print('NA'); raise SystemExit   # INV-1
    recs=d['data'] if isinstance(d['data'],list) else []
    print(round(float(max((r.get('amount',0) for r in recs), default=0)),2))
except SystemExit: pass
except Exception: print('NA')" 2>/dev/null || echo NA)"
# Capafy 3d leading indicator (NOT summed into the monthly goal; labeled)
CAP_3D="$(printf '%s' "$(fetch cap_trend https://api.capafy.ai/agent/sales/trend -H "Authorization: Bearer $CAP_TOK")" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    if d.get('code',0)!=0 or 'data' not in d: print('NA'); raise SystemExit
    days=d['data'].get('data'); print(round(float(sum(x.get('netRevenue',0) for x in days)),2)) if isinstance(days,list) else print('NA')
except SystemExit: pass
except Exception: print('NA')" 2>/dev/null || echo NA)"

# LM real $ MRR — expand price so unit_amount is present (FIND-013: verified against live sub shape) ─
LM_BODY="$(fetch lm_subs 'https://api.stripe.com/v1/subscriptions?status=active&limit=100&expand[]=data.items.data.price' -u "${STRIPE_SECRET_KEY:-x}:")"
LM_MRR="$(printf '%s' "$LM_BODY" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    if 'error' in d or d.get('object')!='list': print('NA'); raise SystemExit   # INV-1
    total=0.0
    for s in d.get('data',[]):
        for it in (s.get('items',{}) or {}).get('data',[]):
            pr=it.get('price');  pr=pr if isinstance(pr,dict) else {}
            amt=(pr.get('unit_amount') or 0)/100.0
            if (pr.get('recurring') or {}).get('interval')=='year': amt/=12.0
            total+=amt*(it.get('quantity') or 1)
    print(round(total,2))
except SystemExit: pass
except Exception: print('NA')" 2>/dev/null || echo NA)"

# HEAL: Capafy publish loop ran recently? (INV-5, 6-week-death guard; seam-able path FIND-011) ─
if [ -f "$LP" ]; then
  AGE=$(( ( $(date +%s) - $(stat -f %m "$LP" 2>/dev/null || echo 0) ) / 86400 ))
  [ "$AGE" -le 2 ] || add_heal "CAPAFY-LOOP-STALE(${AGE}d) → check cron fired daily_loop.sh"
else add_heal "CAPAFY-LOOP-NEVER-RAN → wire+fire daily_loop.sh"; fi

# prior STATE (FIND-006)
PREV="$(grep -E '^monthly_revenue_usd:' "$STATE_MD" 2>/dev/null | awk '{print $2}' | tail -1)"; PREV="${PREV:-n/a}"

# Monthly total (INV-6 apples-to-apples) + FIND-007 (show earning even under HEAL)
SPEND=200; TOTAL="NA"
if [ "$LM_MRR" != "NA" ] && [ "$CAP_MO" != "NA" ]; then TOTAL="$(python3 -c "print(round(${LM_MRR}+${CAP_MO},2))" 2>/dev/null||echo NA)"; fi
EARN_NOTE=""; [ "$TOTAL" != "NA" ] && EARN_NOTE=" (current monthly: \$$TOTAL)"
if [ -n "$HEAL" ]; then STATUS="HEAL-NEEDED — ${HEAL}${EARN_NOTE}"
elif [ "$TOTAL" = "NA" ]; then STATUS="READ-FAILED (LM_MRR=$LM_MRR Capafy_mo=$CAP_MO) — cannot sum a real total; DO NOT trust, recompute"
elif awk "BEGIN{exit !($TOTAL>0)}" 2>/dev/null; then STATUS="EARNING \$$TOTAL/mo (LM \$$LM_MRR + Capafy \$$CAP_MO) — grow toward \$$SPEND"
else STATUS="NO realised revenue yet (\$0/mo) — bottleneck = DEMAND (users/sales), not code"; fi

# INV-5: on ANY heal, drop a selfheal-request so the claude-p loop self-fixes next wake (FIND-014)
if [ -n "$HEAL" ]; then mkdir -p "$(dirname "$REQ")"; printf '{"ts":"%s","heal":"%s"}\n' "$(date -u +%FT%TZ)" "${HEAL//\"/}" > "$REQ"; else rm -f "$REQ" 2>/dev/null||true; fi

TMP="$STATE_MD.tmp.$$"
{
  echo "# LM + Capafy money loop — STATE (GLVS, no-human, money → Dais bank)"
  echo "goal: real monthly LM Stripe MRR + Capafy payout > Dais monthly spend (~\$$SPEND). Real \$ only; never masked-error-as-0; monthly compared to monthly."
  echo "last_wake_utc: $(date -u +%FT%TZ)"
  echo "heal_first: ${HEAL:-all healthy (Capafy auth ✓, Stripe live-key ✓, publish loop ran ≤2d ✓)}"
  echo "lm_mrr_usd: $LM_MRR"
  echo "capafy_monthly_payout_usd: $CAP_MO"
  echo "capafy_3d_net_usd_leading: $CAP_3D"
  echo "monthly_revenue_usd: $TOTAL"
  echo "prev_monthly_revenue_usd: $PREV"
  echo "status: $STATUS"
  echo "selfheal_request: ${HEAL:+written→$REQ}${HEAL:-none}"
  echo "next: HEAL-NEEDED→fix that surface first (a selfheal-request was written); READ-FAILED→recompute; else pick the single highest-EV self-improve action (LM funnel / Capafy listing→winner / Reddit demand) and VERIFY a real \$ delta."
} > "$TMP" && mv "$TMP" "$STATE_MD"
echo "[lm-capafy-loop] monthly=\$$TOTAL (LM \$$LM_MRR + Capafy \$$CAP_MO) 3d_lead=\$$CAP_3D | heal=${HEAL:-none} | $STATUS"
