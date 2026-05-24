#!/usr/bin/env bash
# anicca-cafe-license-applier — Phase 1: 食品衛生責任者 + 開業届け
set -uo pipefail

SKILL=~/.openclaw/skills/anicca-cafe-license-applier
DRY_RUN="${DRY_RUN:-false}"
CDP_URL="${BU_CDP_URL:-http://127.0.0.1:9223}"
export BU_CDP_URL="$CDP_URL"

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
: "${DAIS_EMAIL:?}"
: "${DAIS_PRIMARY_PW:?}"

mkdir -p "$SKILL/data/license"
STATE="$SKILL/data/license/cafe-shinjuku.json"

# Init state if first run
if [ ! -f "$STATE" ]; then
  jq -n \
    --arg permit_type "飲食店営業（調理販売）" \
    --arg issuing_authority "新宿区保健所" \
    --arg operator "<your-name>" \
    --arg kitchen_address "TBD (キッチンスペース.com 信濃町)" \
    --arg status "preparing" \
    --argjson operator_id_kojin null \
    --argjson license_number null \
    --argjson food_safety_cert_id null \
    --argjson uber_eats_merchant_id null \
    '$ARGS.named' > "$STATE"
fi

echo "▶ Phase 1: 食品衛生責任者 + 開業届け  dry_run=$DRY_RUN"

# ── Step 1: 食品衛生責任者 養成講習 申込 ──────────────────────────────────────
echo "  Step 1: toshokuken.or.jp 講習会申込"
if [ "$DRY_RUN" != "true" ]; then
  {{profile.lateness.stakeholders.channel}}-harness -c "
import time
goto_url('https://www.toshokuken.or.jp/')
wait_for_load(); time.sleep(2)
print('TOSHOKUKEN URL:', page_info().get('url',''))
# Discover 講習会日程ページ
courses = js('''
const links = Array.from(document.querySelectorAll('a'));
return JSON.stringify(links.filter(a => /講習|養成|食品衛生|申込/.test(a.textContent||'')).slice(0,10).map(a => ({text:(a.textContent||'').trim().slice(0,60), href:a.href})));
''')
print('COURSES:', courses[:500])
" 2>&1 | tail -10
  jq '.status = "food_safety_in_progress"' "$STATE" > "$STATE.tmp" && mv "$STATE.tmp" "$STATE"
fi

# ── Step 2: 開業届け via freee ───────────────────────────────────────────────
echo "  Step 2: freee.co.jp 開業届けテンプレ生成"
if [ "$DRY_RUN" != "true" ]; then
  {{profile.lateness.stakeholders.channel}}-harness -c "
import time
goto_url('https://www.freee.co.jp/kaigyou/')
wait_for_load(); time.sleep(2)
print('FREEE URL:', page_info().get('url',''))
# 開業届書類作成 form 検出
form = js('''
const inputs = Array.from(document.querySelectorAll('input, select'));
return JSON.stringify(inputs.slice(0,10).map(i => ({name:i.name||'', type:i.type, placeholder:i.placeholder||''})));
''')
print('FREEE FORM:', form[:400])
" 2>&1 | tail -5
fi

# ── Slack alert: 講習出席必須 ────────────────────────────────────────────────
if command -v openclaw &>/dev/null; then
  openclaw message send --channel slack --target "${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}" \
    --text "🍱 cafe-license Phase 1 起動 — 食衛責 講習申込 + 開業届け。toshokuken.or.jp と freee.co.jp の form 状態を確認してください" 2>/dev/null || true
fi

echo "✓ Phase 1 done. Next: bash scripts/application.sh (after kitchen contract)"
