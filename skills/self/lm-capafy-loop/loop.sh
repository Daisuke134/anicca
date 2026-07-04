#!/usr/bin/env bash
# lm-capafy-loop/loop.sh — ONE no-human wake of the LM + Capafy MONEY LOOP (GLVS / HARD 0.40).
# Money = REAL Stripe LM $ MRR + REAL Capafy $ net revenue (to Dais's BANK). Anti-fake INVARIANTS:
#   INV-1 a value is REAL only if the provider returned a SUCCESS body; an error body (code!=0 / "error"
#         key / missing field) is NA, NEVER 0. Masking an error as $0 is the cardinal sin (FIND-002).
#   INV-2 HEAL and READ derive from the SAME fetched body (one fetch/surface) — no TOCTOU (FIND-002).
#   INV-3 revenue is DOLLARS, never a subscription count (FIND-001); $0/test subs excluded.
#   INV-4 on a read failure the status is a FAIL-SAFE "cannot trust", never the happy string (FIND-003).
#   INV-5 HEAL also asserts the Capafy publish loop actually RAN recently (log freshness) — the 6-week
#         silent-death guard (FIND-008).
# Test seam (FIND-004): LMCAP_TEST=1 + LMCAP_FIXTURE=<dir> → read <surface>.json/<surface>.code from files
#   instead of curl; LMCAP_DIR relocates state. No env var can point the goal at attacker data.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIR="${LMCAP_DIR:-$HERE}"; STATE_MD="$DIR/state/STATE.md"; mkdir -p "$DIR/state"
set -a; . ~/.openclaw/.env 2>/dev/null; set +a

# fetch <name> <url> [curl-auth-args...] → prints body; sets global RC_<name> to the http code.
fetch(){ local name="$1" url="$2"; shift 2
  if [ "${LMCAP_TEST:-}" = "1" ] && [ -n "${LMCAP_FIXTURE:-}" ]; then
    eval "RC_$name=\$(cat '$LMCAP_FIXTURE/$name.code' 2>/dev/null || echo 000)"
    cat "$LMCAP_FIXTURE/$name.json" 2>/dev/null || echo '{}'
    return 0
  fi
  local body code; body="$(curl -s --max-time 20 -w $'\n%{http_code}' "$@" "$url" 2>/dev/null)"
  code="${body##*$'\n'}"; body="${body%$'\n'*}"
  eval "RC_$name=\$code"; printf '%s' "$body"
}

HEAL=""; add_heal(){ HEAL="$HEAL$1; "; }
CAP_TOK="$(python3 -c "import json;print(json.load(open('$HOME/.openclaw/skills/capafy-autopublish/vendor/capafy-publisher/config.json'))['access_token'])" 2>/dev/null || echo)"

# ── Stripe key-mode guard (INV: live-money must be a live key) (FIND-009) ─────
case "${STRIPE_SECRET_KEY:-}" in sk_live_*) : ;; "") add_heal "STRIPE-KEY-MISSING";; *) add_heal "STRIPE-KEY-NOT-LIVE(mode!=live → \$ figures untrustworthy)";; esac

# ── Fetch each surface ONCE; derive BOTH health and value from that body (INV-2) ─
# Capafy account (auth) + sales trend (revenue)
CAP_ACCT="$(fetch cap_acct https://api.capafy.ai/agent/account -H "Authorization: Bearer $CAP_TOK")"
CAP_ACCT_CODE="$(printf '%s' "$CAP_ACCT" | python3 -c "import json,sys;print(json.load(sys.stdin).get('code','x'))" 2>/dev/null || echo x)"
[ "$CAP_ACCT_CODE" = "0" ] || add_heal "CAPAFY-AUTH-DOWN(code=$CAP_ACCT_CODE) → re-login (login-init→gog OTP→login-verify)"
CAP_TREND="$(fetch cap_trend https://api.capafy.ai/agent/sales/trend -H "Authorization: Bearer $CAP_TOK")"
CAP_REV="$(printf '%s' "$CAP_TREND" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    if d.get('code',0)!=0 or 'data' not in d: print('NA'); raise SystemExit   # INV-1: error body → NA not 0
    days=d['data'].get('data'); 
    if not isinstance(days,list): print('NA'); raise SystemExit
    print(round(float(sum(x.get('netRevenue',0) for x in days)),2))
except SystemExit: pass
except Exception: print('NA')" 2>/dev/null || echo NA)"

# LM real $ MRR from Stripe active subs (INV-3: dollars, exclude \$0/test)
LM_BODY="$(fetch lm_subs 'https://api.stripe.com/v1/subscriptions?status=active&limit=100&expand[]=data.items' -u "${STRIPE_SECRET_KEY:-x}:")"
LM_MRR="$(printf '%s' "$LM_BODY" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    if 'error' in d or d.get('object')!='list': print('NA'); raise SystemExit   # INV-1: Stripe error → NA
    total=0.0
    for s in d.get('data',[]):
        for it in (s.get('items',{}) or {}).get('data',[]):
            pr=it.get('price') or {}; amt=(pr.get('unit_amount') or 0)/100.0
            iv=(pr.get('recurring') or {}).get('interval','month')
            if iv=='year': amt=amt/12.0
            total+=amt*(it.get('quantity') or 1)
    print(round(total,2))                                                       # \$ MRR, \$0 subs contribute \$0
except SystemExit: pass
except Exception: print('NA')" 2>/dev/null || echo NA)"

# ── HEAL: Capafy publish loop actually RAN recently? (INV-5, the 6-week-death guard) ──
LP="$HOME/.openclaw/skills/capafy-autopublish/state/daily_loop.log"
if [ -f "$LP" ]; then
  AGE_D=$(( ( $(date +%s) - $(stat -f %m "$LP" 2>/dev/null || echo 0) ) / 86400 ))
  [ "$AGE_D" -le 2 ] || add_heal "CAPAFY-LOOP-STALE(${AGE_D}d since last run) → check cron/launchd fired daily_loop.sh"
else add_heal "CAPAFY-LOOP-NEVER-RAN(no daily_loop.log) → wire + fire daily_loop.sh"; fi

# ── prior STATE (INV: read the spine before judging) (FIND-006) ──────────────
PREV_MRR="$(grep -E '^lm_mrr_usd:' "$STATE_MD" 2>/dev/null | awk '{print $2}' | tail -1)"; PREV_MRR="${PREV_MRR:-n/a}"

# ── STATUS (INV-4 fail-safe: NA → cannot trust; never the happy string) ──────
SPEND=200
if [ -n "$HEAL" ]; then STATUS="HEAL-NEEDED — $HEAL"
elif [ "$LM_MRR" = "NA" ] || [ "$CAP_REV" = "NA" ]; then STATUS="READ-FAILED (LM_MRR=$LM_MRR Capafy=$CAP_REV) — a real total cannot be summed; DO NOT trust, recompute before acting"
else
  TOTAL="$(python3 -c "print(round(${LM_MRR}+${CAP_REV},2))" 2>/dev/null || echo NA)"
  if awk "BEGIN{exit !($TOTAL>0)}" 2>/dev/null; then STATUS="EARNING \$$TOTAL/mo (LM \$$LM_MRR + Capafy \$$CAP_REV) — grow toward \$$SPEND"
  else STATUS="NO realised revenue yet (\$0) — bottleneck = DEMAND (users/sales), not code"; fi
fi

# ── STATE.md atomic ──────────────────────────────────────────────────────────
TMP="$STATE_MD.tmp.$$"
{
  echo "# LM + Capafy money loop — STATE (GLVS, no-human, money → Dais bank)"
  echo "goal: real LM Stripe \$ MRR + Capafy \$ net revenue > Dais monthly spend (~\$$SPEND). Done ONLY on real provider-reported \$, NEVER 'published/posted', NEVER a masked error-as-0."
  echo "last_wake_utc: $(date -u +%FT%TZ)"
  echo "heal_first: ${HEAL:-all surfaces healthy (Capafy auth ✓, Stripe live-key ✓, Capafy loop ran ≤2d ✓)}"
  echo "lm_mrr_usd: $LM_MRR"
  echo "prev_lm_mrr_usd: $PREV_MRR"
  echo "capafy_net_revenue_usd_3d: $CAP_REV"
  echo "status: $STATUS"
  echo "next: if HEAL-NEEDED → fix that surface FIRST; elif READ-FAILED → recompute, do not act on a bad number; else pick the single highest-EV self-improve action (LM funnel / Capafy listing→winner / Reddit demand) and VERIFY a real \$ delta."
} > "$TMP" && mv "$TMP" "$STATE_MD"
echo "[lm-capafy-loop] LM_MRR=\$$LM_MRR Capafy_3d=\$$CAP_REV | heal=${HEAL:-none} | $STATUS"
