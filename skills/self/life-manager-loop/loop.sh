#!/usr/bin/env bash
# life-manager-loop/loop.sh — ONE no-human wake of the LIFE MANAGER money loop (GLVS / HARD 0.40).
# Money = REAL Stripe $ MRR (to Dais's BANK). Split out of the (wrongly-combined) lm-capafy-loop.
# Anti-fake (VCSDD-proven): error→NA never masked-$0; $ MRR not sub-count (expand price, live-shape
# verified); NA→READ-FAILED; sk_live guard; HEAL LM /health + Stripe; selfheal-request on HEAL.
# Seams: LM_TEST=1 + LM_FIXTURE=<dir>, LM_DIR, LM_REQ.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIR="${LM_DIR:-$HERE}"; STATE_MD="$DIR/state/STATE.md"; mkdir -p "$DIR/state"
set -a; . $HOME/.local/state/life-manager/.env 2>/dev/null; set +a
REQ="${LM_REQ:-$HOME/.local/state/life-manager/state/life-manager-loop-selfheal-request.json}"
fetch(){ local name="$1" url="$2"; shift 2
  if [ "${LM_TEST:-}" = "1" ] && [ -n "${LM_FIXTURE:-}" ]; then cat "$LM_FIXTURE/$name.json" 2>/dev/null || echo '{}'; return 0; fi
  curl -s --max-time 20 "$@" "$url" 2>/dev/null; }
HEAL=""; add_heal(){ HEAL="$HEAL$1; "; }

# Stripe key mode
case "${STRIPE_SECRET_KEY:-}" in sk_live_*) : ;; "") add_heal "STRIPE-KEY-MISSING";; *) add_heal "STRIPE-KEY-NOT-LIVE";; esac
# LM /health
if [ "${LM_TEST:-}" != "1" ]; then
  LMH="$(curl -s --max-time 10 -o /dev/null -w '%{http_code}' https://life-call-production.up.railway.app/health 2>/dev/null||echo 000)"
  [ "$LMH" = "200" ] || add_heal "LM-HEALTH-$LMH → check Railway life-call"
fi
# real $ MRR (INV: dollars, expand price, live-shape verified; $0 subs → $0)
LM_MRR="$(printf '%s' "$(fetch lm_subs 'https://api.stripe.com/v1/subscriptions?status=active&limit=100&expand[]=data.items.data.price' -u "${STRIPE_SECRET_KEY:-x}:")" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    if 'error' in d or d.get('object')!='list': print('NA'); raise SystemExit
    total=0.0
    for s in d.get('data',[]):
        for it in (s.get('items',{}) or {}).get('data',[]):
            pr=it.get('price'); pr=pr if isinstance(pr,dict) else {}
            amt=(pr.get('unit_amount') or 0)/100.0
            if (pr.get('recurring') or {}).get('interval')=='year': amt/=12.0
            total+=amt*(it.get('quantity') or 1)
    print(round(total,2))
except SystemExit: pass
except Exception: print('NA')" 2>/dev/null||echo NA)"

PREV="$(grep -E '^lm_mrr_usd:' "$STATE_MD" 2>/dev/null | awk '{print $2}' | tail -1)"; PREV="${PREV:-n/a}"
if [ -n "$HEAL" ]; then STATUS="HEAL-NEEDED — ${HEAL}(MRR \$$LM_MRR)"
elif [ "$LM_MRR" = "NA" ]; then STATUS="READ-FAILED — LM MRR cannot be read; DO NOT trust"
elif awk "BEGIN{exit !($LM_MRR>0)}" 2>/dev/null; then STATUS="EARNING \$$LM_MRR/mo — grow: fix the weakest funnel step + Reddit demand"
else STATUS="NO LM revenue yet (\$0/mo) — 3 test users only; bottleneck = DEMAND (real users); fix the weakest funnel step + drive signups"; fi
if [ -n "$HEAL" ]; then mkdir -p "$(dirname "$REQ")"; printf '{"loop":"life-manager","ts":"%s","heal":"%s"}\n' "$(date -u +%FT%TZ)" "${HEAL//\"/}" > "$REQ"; else rm -f "$REQ" 2>/dev/null||true; fi
TMP="$STATE_MD.tmp.$$"
{
  echo "# Life Manager money loop — STATE (GLVS, no-human, money → Dais bank)"
  echo "goal: real Stripe \$ MRR, growing. Real \$ only; never masked-error-as-0; \$ MRR not a sub count."
  echo "last_wake_utc: $(date -u +%FT%TZ)"
  echo "heal_first: ${HEAL:-all healthy (LM /health 200 ✓, Stripe live-key ✓)}"
  echo "lm_mrr_usd: $LM_MRR"
  echo "prev_lm_mrr_usd: $PREV"
  echo "status: $STATUS"
  echo "selfheal_request: ${HEAL:+written→$REQ}${HEAL:-none}"
  echo "next: HEAL-NEEDED→fix (a selfheal-request was written); READ-FAILED→recompute; else ACT: read the Telegram funnel (start→calendar→phone→pay→retain), fix the ONE weakest step OR drive Reddit demand; VERIFY a real new paid Stripe sub."
} > "$TMP" && mv "$TMP" "$STATE_MD"
echo "[life-manager-loop] MRR=\$$LM_MRR | heal=${HEAL:-none} | $STATUS"

# Liveness heartbeat (FIND-032): touch it HERE, in the deterministic MEASURE core (runs first on every
# pass — startup + daily cron — completes in ~2s, cannot derail). Previously the heartbeat was touched
# ONLY at the very end of the open-ended STARTUP/cron pass ("FINALLY touch"), AFTER STEP2 ACT — a
# rabbit-hole-prone agentic task (funnel/Telegram-bot debugging) that can run for hours and never return
# to the touch. That starved the heartbeat → healthcheck STALE → restart → pkill kills the in-progress
# claude → fresh claude re-enters the same STEP2 → still no touch within the 5-min window → STALE again
# → restart loop that kills the very session that would refresh the heartbeat → give-up → self-fix.
# The healthcheck contract is "liveness + stuck-detection only" (revenue truth = verify-loops.sh), so
# liveness must mean "the loop executed its measurable core this pass", NOT "an open-ended money task
# fully completed". Skip under test mode so the real prod heartbeat is never touched by test-loop.sh.
[ "${LM_TEST:-}" = "1" ] || { mkdir -p "$HOME/.local/state/life-manager/state" && touch "$HOME/.local/state/life-manager/state/.life-manager-loop-last-pass" 2>/dev/null; } || true
