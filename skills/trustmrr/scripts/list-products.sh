#!/usr/bin/env bash
# trustmrr — end-to-end add/claim Anicca products on trustmrr.com
# Usage:
#   bash scripts/list-products.sh                       # list anicca only (default)
#   PRODUCT=anicca STRIPE_KEY=$STRIPE_RK_LIVE_ALL \
#     bash scripts/list-products.sh
#   DRY_RUN=true bash scripts/list-products.sh          # don't click submit
#
# Requires: {{profile.lateness.stakeholders.channel}}-harness, jq, curl, Chrome on 9223.

set -uo pipefail

SKILL=~/.openclaw/skills/trustmrr
DRY_RUN="${DRY_RUN:-false}"
PRODUCT="${PRODUCT:-anicca}"
HANDLE="${HANDLE:-aniccaai}"
CDP_URL="${BU_CDP_URL:-http://127.0.0.1:9223}"
export BU_CDP_URL="$CDP_URL"

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

STRIPE_KEY="${STRIPE_KEY:-${TRUSTMRR_STRIPE_KEY:-${STRIPE_RK_LIVE_ALL:-}}}"
: "${STRIPE_KEY:?Set STRIPE_KEY or STRIPE_RK_LIVE_ALL/TRUSTMRR_STRIPE_KEY in ~/.openclaw/.env}"
: "${DAIS_EMAIL:?DAIS_EMAIL not set}"

mkdir -p "$SKILL/data/listings"

echo "▶ trustmrr  product=$PRODUCT  dry_run=$DRY_RUN"

# ── 1. Skip if already listed ─────────────────────────────────────────────────
LISTING="$SKILL/data/listings/$PRODUCT.json"
if [ -f "$LISTING" ]; then
  STATUS=$(jq -r '.status // "unknown"' "$LISTING")
  if [ "$STATUS" = "listed_and_claimed" ]; then
    echo "  already listed: $(jq -r .trustmrr_url "$LISTING")"
    echo "  use REFRESH=true to re-run add flow"
    [ "${REFRESH:-false}" = "true" ] || exit 0
  fi
fi

# ── 2. Ensure Chrome 9223 is up ───────────────────────────────────────────────
if ! curl -sS -o /dev/null -w '%{http_code}' "$CDP_URL/json/version" | grep -q 200; then
  nohup '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
    --remote-debugging-port=9223 \
    --user-data-dir="$HOME/.{{profile.lateness.stakeholders.channel}}-harness-profile" \
    --no-first-run --no-default-{{profile.lateness.stakeholders.channel}}-check \
    > /tmp/chrome-9223.log 2>&1 &
  for i in 1 2 3 4 5 6 7 8; do
    sleep 1
    curl -sS -o /dev/null -w '%{http_code}' "$CDP_URL/json/version" | grep -q 200 && break
  done
fi

# ── 3. Open Add startup modal, fill, click via coords ─────────────────────────
if [ "$DRY_RUN" = "true" ]; then
  echo "  [DRY] skipping add flow"
  exit 0
fi

{{profile.lateness.stakeholders.channel}}-harness -c "
import time, os
APIKEY = '$STRIPE_KEY'
HANDLE = '$HANDLE'
goto_url('https://trustmrr.com/')
wait_for_load(); time.sleep(2)
js('const b=Array.from(document.querySelectorAll(\"button\")).find(x=>/^Add startup\$/i.test((x.textContent||\"\").trim())); if(b) b.click(); return true;')
time.sleep(3)
js('window.__APIKEY__=' + repr(APIKEY) + '; window.__HANDLE__=' + repr(HANDLE) + '; return true;')
fill = '''
const setVal = (el, val) => {
  const proto = el.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, val);
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
  el.dispatchEvent(new Event('blur', { bubbles: true }));
};
const apik = document.querySelector('input[name=\"apiKey\"]');
const h = document.querySelector('input[placeholder=\"username\"]');
if (apik) setVal(apik, window.__APIKEY__);
if (h) setVal(h, window.__HANDLE__);
return JSON.stringify({apiLen: apik?apik.value.length:0, handle: h?h.value:null});
'''
print('FILL:', js(fill))
time.sleep(2)
coords = js('''
const b = Array.from(document.querySelectorAll(\"button\")).find(x => /^Add startup\$/i.test((x.textContent||\"\").trim()) && !x.disabled);
if (!b) return JSON.stringify({err:'btn'});
const r = b.getBoundingClientRect();
return JSON.stringify({x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2)});
''')
print('COORDS:', coords)
import json
c = json.loads(coords)
if 'x' in c:
    click_at_xy(c['x'], c['y'])
    print('CLICKED Add startup')
" 2>&1 | tail -10

# ── 4. Wait for Stripe validation (5-15s) ─────────────────────────────────────
sleep 12

# ── 5. Discover the resulting slug ────────────────────────────────────────────
SLUG=$({{profile.lateness.stakeholders.channel}}-harness -c "
import time
url = page_info().get('url','')
import re
m = re.search(r'/startup/([^?#/]+)', url)
print(m.group(1) if m else '')
" 2>&1 | tail -1)

if [ -z "$SLUG" ]; then
  echo "  ⚠ no /startup/<slug> URL after submit — likely Stripe key rejected. Check tab manually."
  exit 1
fi

URL="https://trustmrr.com/startup/$SLUG"
echo "  listed → $URL"

# ── 6. Persist state ──────────────────────────────────────────────────────────
LISTED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
jq -n \
  --arg product_key "$SLUG" \
  --arg trustmrr_url "$URL" \
  --arg owner_{{profile.lateness.stakeholders.channel}} "$DAIS_EMAIL" \
  --arg listed_at "$LISTED_AT" \
  --arg status "listed_unclaimed" \
  --argjson anonymous_mode false \
  --argjson listed_for_sale false \
  '$ARGS.named' > "$SKILL/data/listings/$SLUG.json"
echo "  state → $SKILL/data/listings/$SLUG.json"
echo "  next: claim flow ({{profile.lateness.stakeholders.channel}} OTP) — use scripts/claim.sh $SLUG"

# ── 7. Slack notify ──────────────────────────────────────────────────────────
if command -v openclaw &>/dev/null; then
  openclaw message send --channel slack --target "${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}" \
    --text "📊 TrustMRR listing ready — $URL  (claim via {{profile.lateness.stakeholders.channel}} OTP)" 2>/dev/null || true
fi
