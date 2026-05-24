#!/usr/bin/env bash
# anicca-cafe-license-applier — Phase 3: Uber Eats merchant signup
set -uo pipefail

SKILL=~/.openclaw/skills/anicca-cafe-license-applier
DRY_RUN="${DRY_RUN:-false}"
CDP_URL="${BU_CDP_URL:-http://127.0.0.1:9223}"
export BU_CDP_URL="$CDP_URL"

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
STATE="$SKILL/data/license/cafe-shinjuku.json"

LICENSE=$(jq -r '.license_number // empty' "$STATE")
if [ -z "$LICENSE" ]; then
  echo "⚠ 営業許可番号未取得。skip Uber onboard"; exit 1
fi

echo "▶ Phase 3: Uber Eats merchant signup (license=$LICENSE)"

if [ "$DRY_RUN" != "true" ]; then
  {{profile.lateness.stakeholders.channel}}-harness -c "
import time
goto_url('https://merchants.ubereats.com/jp/ja/sign-up/')
wait_for_load(); time.sleep(3)
print('UBER URL:', page_info().get('url',''))
fields = js('''
const inputs = Array.from(document.querySelectorAll('input, select, textarea'));
return JSON.stringify(inputs.slice(0,20).map(i => ({name:i.name||'', placeholder:i.placeholder||'', type:i.type})));
''')
print('UBER FIELDS:', fields[:600])
" 2>&1 | tail -10

  jq --arg t "$(date -u +%FT%TZ)" \
     '.uber_eats_signup_at = $t | .status = "uber_pending"' \
     "$STATE" > "$STATE.tmp" && mv "$STATE.tmp" "$STATE"
fi

if command -v openclaw &>/dev/null; then
  openclaw message send --channel slack --target "${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}" \
    --text "🛵 Uber Eats merchant signup 起動 — 営業許可 $LICENSE。1-2 週で契約面談" 2>/dev/null || true
fi

echo "✓ Phase 3 done"
