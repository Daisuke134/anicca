#!/usr/bin/env bash
# lm-capafy-loop/loop.sh — ONE no-human wake of the Life-Manager + Capafy MONEY LOOP (GLVS / HARD 0.40).
# Modeled on ~/anicca/skills/self/founder-loop/founder-loop.sh but the earn = REAL Stripe LM subs + REAL
# Capafy subscription sales (money to Dais's BANK, not a crypto wallet). Anti-fake: a metric is only
# "real" if the provider API returns it; "published/posted" is NEVER revenue. HEAL-FIRST: check each
# revenue surface's health before reading. Writes STATE.md atomically, reports one line. Never fabricates.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIR="${LMCAP_DIR:-$HERE}"; STATE_MD="$DIR/state/STATE.md"; mkdir -p "$DIR/state"
set -a; . ~/.openclaw/.env 2>/dev/null; set +a

now(){ date -u +%FT%TZ; }
HEAL=""; add_heal(){ HEAL="$HEAL$1; "; }

# ── 0. HEAL-FIRST: is each revenue surface alive? ────────────────────────────
# Capafy auth
CAP_TOK="$(python3 -c "import json;print(json.load(open('$HOME/.openclaw/skills/capafy-autopublish/vendor/capafy-publisher/config.json'))['access_token'])" 2>/dev/null || echo)"
CAP_HEALTH="$(curl -s --max-time 15 https://api.capafy.ai/agent/account -H "Authorization: Bearer $CAP_TOK" 2>/dev/null | python3 -c "import json,sys;print(json.load(sys.stdin).get('code'))" 2>/dev/null || echo err)"
[ "$CAP_HEALTH" = "0" ] || add_heal "CAPAFY-AUTH-DOWN(code=$CAP_HEALTH) → re-login (login-init→gog OTP→login-verify)"
# LM /health
LM_HEALTH="$(curl -s --max-time 10 -o /dev/null -w '%{http_code}' https://life-call-production.up.railway.app/health 2>/dev/null || echo 000)"
[ "$LM_HEALTH" = "200" ] || add_heal "LM-HEALTH-$LM_HEALTH → restart life-call / check Railway"
# Stripe key
ST_HEALTH="$(curl -s --max-time 12 -o /dev/null -w '%{http_code}' https://api.stripe.com/v1/subscriptions?limit=1 -u "${STRIPE_SECRET_KEY:-x}:" 2>/dev/null || echo 000)"
[ "$ST_HEALTH" = "200" ] || add_heal "STRIPE-$ST_HEALTH → check STRIPE_SECRET_KEY"

# ── 1. READ real revenue (anti-fake: only what the API returns) ──────────────
# Capafy net revenue (last 3d trend)
CAP_REV="$(curl -s --max-time 15 https://api.capafy.ai/agent/sales/trend -H "Authorization: Bearer $CAP_TOK" 2>/dev/null | python3 -c "import json,sys
try:
  d=json.load(sys.stdin).get('data',{}).get('data',[]); print(round(sum(x.get('netRevenue',0) for x in d),2))
except: print('NA')" 2>/dev/null || echo NA)"
# LM active paid subs (Stripe)
LM_SUBS="$(curl -s --max-time 15 'https://api.stripe.com/v1/subscriptions?status=active&limit=100' -u "${STRIPE_SECRET_KEY:-x}:" 2>/dev/null | python3 -c "import json,sys
try:
  d=json.load(sys.stdin); print(len(d.get('data',[])))
except: print('NA')" 2>/dev/null || echo NA)"

# ── 2. GOAL-check on REAL numbers (never 'the wake ran') ─────────────────────
SPEND=200
STATUS="NO realised external revenue yet — bottleneck = DEMAND (users/sales), not code"
if printf '%s' "$CAP_REV" | grep -qE '^[0-9.]+$' && awk "BEGIN{exit !($CAP_REV>0)}" 2>/dev/null; then STATUS="EARNING (Capafy net \$$CAP_REV) — grow it"; fi
if printf '%s' "$LM_SUBS" | grep -qE '^[0-9]+$' && [ "${LM_SUBS:-0}" -gt 0 ] 2>/dev/null; then STATUS="EARNING (LM $LM_SUBS active subs) — grow it"; fi
[ -n "$HEAL" ] && STATUS="HEAL-NEEDED — $HEAL"

# ── 3. STATE.md atomic ──────────────────────────────────────────────────────
TMP="$STATE_MD.tmp.$$"
{
  echo "# LM + Capafy money loop — STATE (GLVS, no-human, money → Dais bank)"
  echo "goal: LM Stripe revenue + Capafy subscription revenue > Dais monthly spend (~\$$SPEND). Done ONLY on real provider-reported revenue, NEVER 'published/posted'."
  echo "last_wake_utc: $(now)"
  echo "heal_first: ${HEAL:-all revenue surfaces healthy (Capafy auth ✓, LM /health 200, Stripe ✓)}"
  echo "lm_active_paid_subs: $LM_SUBS"
  echo "capafy_net_revenue_usd_3d: $CAP_REV"
  echo "status: $STATUS"
  echo "next: if HEAL-NEEDED → fix that surface first; else pick the single highest-EV self-improve action (LM funnel / Capafy listing→winner / Reddit demand) and VERIFY a real revenue delta."
} > "$TMP" && mv "$TMP" "$STATE_MD"

echo "[lm-capafy-loop] wake done | LM_subs=$LM_SUBS Capafy_net_3d=$CAP_REV | heal=${HEAL:-none} | $STATUS"
