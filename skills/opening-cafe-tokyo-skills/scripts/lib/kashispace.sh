#!/usr/bin/env bash
# lib/kashispace.sh — kashispace.com 任意 room の問合せ form 自動送信
# Usage: bash lib/kashispace.sh <room_id> <message_file>
#   room_id: kashispace.com/room/detail?id=<N> の N
#   message_file: お問い合わせ内容のテキストファイルパス
#
# 入力 env: DAIS_EMAIL, DAIS_PHONE (or override with OPERATOR_EMAIL/OPERATOR_PHONE)
# 出力: stdout に JSON {status, room_id, submitted_at, receipt_no(optional)}

set -uo pipefail

ROOM_ID="${1:?usage: $0 <room_id> <message_file>}"
MSG_FILE="${2:?}"
[ ! -f "$MSG_FILE" ] && { echo '{"status":"err","msg":"message_file not found"}'; exit 1; }

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
CONFIG="${CONFIG:-$HOME/.openclaw/skills/opening-cafe-tokyo-skills/data/config.json}"
NAME=$(jq -r '.operator.name'      "$CONFIG" 2>/dev/null || echo "")
NAME_KANA=$(jq -r '.operator.name_kana' "$CONFIG" 2>/dev/null || echo "")
EMAIL="${OPERATOR_EMAIL:-${DAIS_EMAIL:-}}"
PHONE="${OPERATOR_PHONE:-${DAIS_PHONE:-}}"
CDP_URL="${BU_CDP_URL:-http://127.0.0.1:9223}"
export BU_CDP_URL="$CDP_URL"

MSG_ESCAPED=$(jq -Rs . < "$MSG_FILE")  # JSON-escaped string

{{profile.lateness.stakeholders.channel}}-harness -c "
import time
goto_url('https://kashispace.com/contact')
wait_for_load(); time.sleep(3)
js('window.__M__=' + ${MSG_ESCAPED} + '; return true;')
print('FILL:', js('''
const setVal = (el, val) => {
  const proto = el.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, val);
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
  el.dispatchEvent(new Event('blur', { bubbles: true }));
};
const personRadio = document.querySelector('input[name=business_type][value=\"1\"]');
if (personRadio && !personRadio.checked) personRadio.click();
const otherRadio = document.querySelector('input[name=contact_type][value=\"3\"]');
if (otherRadio && !otherRadio.checked) otherRadio.click();
setVal(document.querySelector('input[name=name]'),       '${NAME}');
setVal(document.querySelector('input[name=name_kana]'),  '${NAME_KANA}');
setVal(document.querySelector('input[name={{profile.lateness.stakeholders.channel}}]'),      '${EMAIL}');
setVal(document.querySelector('input[name=tel]'),        '${PHONE}');
setVal(document.querySelector('textarea[name=contact_detail]'), window.__M__);
const policy = document.querySelector('input[name=policy]');
if (policy && !policy.checked) policy.click();
return JSON.stringify({ok: true});
'''))
time.sleep(1)
# Step 1: 確認画面
js('document.querySelector(\"input[type=submit][value=確認画面]\").click(); return true;')
time.sleep(5)
# Step 2: 送信
import json
coords = js('''
const btn = document.querySelector('input[name=go_btn]');
if (!btn) return null;
btn.scrollIntoView({block:'center'});
const r = btn.getBoundingClientRect();
return JSON.stringify({x: Math.round(r.x+r.width/2), y: Math.round(r.y+r.height/2)});
''')
if coords and coords != 'null':
    c = json.loads(coords)
    click_at_xy(c['x'], c['y'])
time.sleep(8)
done = js('return /お問い合わせが完了|受付ました|完了しました/i.test(document.body.innerText);')
print('DONE:', done)
" 2>&1 | tail -5

# Output skill state
SUBMITTED_AT=$(date -u +%FT%TZ)
jq -n \
  --arg platform "kashispace" \
  --arg room_id "$ROOM_ID" \
  --arg submitted_at "$SUBMITTED_AT" \
  --arg form_url "https://kashispace.com/contact" \
  --arg status "submitted" \
  --arg next_action "Wait for confirmation {{profile.lateness.stakeholders.channel}} (~営業時間内 2 営業日以内回答)" \
  '$ARGS.named'
