#!/usr/bin/env bash
# lib/theghostrestaurant.sh — theghostrestaurant.tokyo 内見申込 form 自動送信
# Usage: bash lib/theghostrestaurant.sh <preferred_date> <preferred_time> <message_file>
#   preferred_date: YYYY-MM-DD
#   preferred_time: 何時でもOK | ～10:00 | 10:00～12:00 | 12:00～14:00 | 14:00～16:00 | 16:00～18:00 | 18:00～
#
# 入力 env: DAIS_EMAIL (or OPERATOR_EMAIL)
# 出力: stdout に JSON

set -uo pipefail

DATE="${1:?usage: $0 <YYYY-MM-DD> <time_slot> <message_file>}"
TIME_SLOT="${2:-10:00～12:00}"
MSG_FILE="${3:?}"
[ ! -f "$MSG_FILE" ] && { echo '{"status":"err"}'; exit 1; }

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
CONFIG="${CONFIG:-$HOME/.openclaw/skills/opening-cafe-tokyo-skills/data/config.json}"
NAME=$(jq -r '.operator.name' "$CONFIG" 2>/dev/null || echo "")
EMAIL="${OPERATOR_EMAIL:-${DAIS_EMAIL:-}}"
CDP_URL="${BU_CDP_URL:-http://127.0.0.1:9223}"
export BU_CDP_URL="$CDP_URL"

MSG_ESCAPED=$(jq -Rs . < "$MSG_FILE")

{{profile.lateness.stakeholders.channel}}-harness -c "
import time
goto_url('https://www.theghostrestaurant.tokyo/info/')
wait_for_load(); time.sleep(3)
js('window.__M__=' + ${MSG_ESCAPED} + '; return true;')
js('''
const setVal = (el, val) => {
  const proto = el.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, val);
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
  el.dispatchEvent(new Event('blur', { bubbles: true }));
};
setVal(document.getElementById('med1aa8a7e0a611620'), '${NAME}');
setVal(document.getElementById('med1aa8a7e0a611621'), '${EMAIL}');
setVal(document.getElementById('med1aa8a7e0a611622'), '${DATE}');
setVal(document.getElementById('med1aa8a7e0a611624'), window.__M__);
const radios = document.querySelectorAll('input[name=med1aa8a7e0a611623]');
for (const r of radios) { if (r.value === '${TIME_SLOT}') { r.click(); break; } }
const cb = document.getElementById('med1aa8a7e0a611625');
if (cb && !cb.checked) cb.click();
return 'filled';
''')
time.sleep(2)
js('''
const cb = document.getElementById('med1aa8a7e0a611625');
let form = cb;
while (form && form.tagName !== 'FORM') form = form.parentElement;
if (form && typeof form.requestSubmit === 'function') form.requestSubmit();
else if (form) form.submit();
return 'submitted';
''')
time.sleep(8)
print('DONE')
" 2>&1 | tail -3

SUBMITTED_AT=$(date -u +%FT%TZ)
jq -n \
  --arg platform "theghostrestaurant" \
  --arg date "$DATE" \
  --arg time_slot "$TIME_SLOT" \
  --arg submitted_at "$SUBMITTED_AT" \
  --arg form_url "https://www.theghostrestaurant.tokyo/info/" \
  --arg status "submitted_form_reset_observed" \
  --arg next_action "Wait for 担当者 reply via {{profile.lateness.stakeholders.channel}}" \
  '$ARGS.named'
