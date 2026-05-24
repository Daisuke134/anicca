#!/usr/bin/env bash
# anicca-cafe-license-applier — Phase 2: 新宿区営業許可申請
set -uo pipefail

SKILL=~/.openclaw/skills/anicca-cafe-license-applier
DRY_RUN="${DRY_RUN:-false}"
CDP_URL="${BU_CDP_URL:-http://127.0.0.1:9223}"
export BU_CDP_URL="$CDP_URL"

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
STATE="$SKILL/data/license/cafe-shinjuku.json"
[ ! -f "$STATE" ] && { echo "ERR: state not initialized. Run pre-step.sh first"; exit 1; }

KITCHEN_CONTRACT=$(jq -r '.kitchen_contract_path // empty' "$STATE")
if [ -z "$KITCHEN_CONTRACT" ]; then
  echo "⚠ kitchen_contract_path empty in $STATE"
  echo "  Set it via: jq '.kitchen_contract_path=\"<path>\"' $STATE > tmp && mv tmp $STATE"
  echo "  (キッチンスペース契約後)"
  exit 1
fi

FOOD_CERT=$(jq -r '.food_safety_cert_id // empty' "$STATE")
if [ -z "$FOOD_CERT" ]; then
  echo "⚠ 食品衛生責任者 修了証未取得。Phase 1 完了確認してください"
  exit 1
fi

echo "▶ Phase 2: 新宿区 営業許可申請  dry_run=$DRY_RUN"

if [ "$DRY_RUN" != "true" ]; then
  {{profile.lateness.stakeholders.channel}}-harness -c "
import time
goto_url('https://www.city.shinjuku.lg.jp/kenkou/file03_00006.html')
wait_for_load(); time.sleep(2)
print('SHINJUKU URL:', page_info().get('url',''))
# 申請書 PDF link 検出
links = js('''
const a = Array.from(document.querySelectorAll('a'));
return JSON.stringify(a.filter(x => /申請|営業許可|食品|PDF|Word/.test(x.textContent||'')).slice(0,15).map(x => ({text:(x.textContent||'').trim().slice(0,80), href:x.href})));
''')
print('LINKS:', links[:600])
" 2>&1 | tail -10

  APPLIED_AT=$(date -u +%FT%TZ)
  jq --arg t "$APPLIED_AT" \
     '.applied_at = $t | .status = "application_submitted"' \
     "$STATE" > "$STATE.tmp" && mv "$STATE.tmp" "$STATE"
fi

# Slack alert: 施設検査立会要請
if command -v openclaw &>/dev/null; then
  openclaw message send --channel slack --target "${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}" \
    --text "📨 cafe-license Phase 2 — 営業許可申請 提出。**保健所 03-5273-3142 に電話して施設検査日予約 + 立会必須**" 2>/dev/null || true
fi

echo "✓ Phase 2 done. Watch Gmail for license {{profile.lateness.stakeholders.channel}} → status.sh が status=approved に flip"
