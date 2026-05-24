#!/usr/bin/env bash
# anicca-haircut-quarterly — Rein (reservia) camofox booking
# Recipe: walk through reservia steps (staff → menu → date → form → confirm)
set -euo pipefail
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

DRY="${DRY_RUN:-0}"
NOW=$(date +%Y-%m-%dT%H-%M-%S)
RUN=~/.openclaw/skills/anicca-haircut-quarterly/data/runs/$NOW
mkdir -p "$RUN"

# 1. compute target: 4 weeks out, Sunday at 11:00
TARGET=$(python3 -c "
import datetime
t=datetime.date.today()+datetime.timedelta(days=28)
while t.weekday()!=6: t+=datetime.timedelta(days=1)
print(t.isoformat())
")
TARGET_UTC_DT="${TARGET}+02:00:00"
echo "  target: $TARGET 11:00 JST (Sunday)"
echo "$TARGET" > "$RUN/target.txt"

# 2. open reservia via camofox (sessionKey=haircut so it doesn't reuse stale tabs)
SESSION="haircut"
TAB_RESP=$(curl -sS -X POST "http://127.0.0.1:9377/tabs" -H "Content-Type: application/json" \
  -d "{\"url\":\"https://reservia.jp/reserve/datetime/84ad9ba1c3?is_guest=1&staff_id=78811&start_page=1&menu_id=316739&start_date=${TARGET}\",\"userId\":\"anicca\",\"sessionKey\":\"$SESSION\"}")
TAB=$(echo "$TAB_RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tabId',''))")
echo "  tab: $TAB"
sleep 6

# 3. click 11:00 Sunday slot (JS find by URL match)
TARGET_URL_PART="datetime=${TARGET}+02%3A00%3A00"
python3 <<PY
import json,urllib.request
TAB="$TAB"
expr='''(()=>{
  const link=[...document.querySelectorAll('a')].find(a=>(a.href||'').includes("$TARGET_URL_PART"));
  if(!link) return JSON.stringify({err:'no slot for $TARGET'});
  link.click();
  return 'clicked '+link.href;
})()'''
body=json.dumps({"userId":"anicca","sessionKey":"$SESSION","expression":expr}).encode()
req=urllib.request.Request(f"http://127.0.0.1:9377/tabs/{TAB}/evaluate",data=body,headers={"Content-Type":"application/json"},method="POST")
print(json.loads(urllib.request.urlopen(req,timeout=10).read().decode()).get('result'))
PY
sleep 5

# 4. fill form fields by name attribute (CRITICAL — DOM order is misleading)
python3 <<PY
import json,urllib.request
TAB="$TAB"
expr=r'''(()=>{
  const set=(el,v)=>{
    if(!el) return;
    const setter=Object.getOwnPropertyDescriptor(el instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:HTMLInputElement.prototype,'value').set;
    setter.call(el,v);
    el.dispatchEvent(new Event('input',{bubbles:true}));
    el.dispatchEvent(new Event('change',{bubbles:true}));
  };
  set(document.querySelector('[name="Reservation[name]"]'),'<your-name>');
  set(document.querySelector('[name="Reservation[{{profile.lateness.stakeholders.channel}}]"]'),'{{profile.contact.personalEmail}}');
  set(document.querySelector('[name="Reservation[tel]"]'),'08046270314');
  const cb=document.querySelector('[name="Reservation[is_new_member]"]');
  if(cb && !cb.checked) cb.click();
  return JSON.stringify({
    name:document.querySelector('[name="Reservation[name]"]')?.value,
    {{profile.lateness.stakeholders.channel}}:document.querySelector('[name="Reservation[{{profile.lateness.stakeholders.channel}}]"]')?.value,
    tel:document.querySelector('[name="Reservation[tel]"]')?.value,
    newmember:document.querySelector('[name="Reservation[is_new_member]"]')?.checked
  });
})()'''
body=json.dumps({"userId":"anicca","sessionKey":"$SESSION","expression":expr}).encode()
req=urllib.request.Request(f"http://127.0.0.1:9377/tabs/{TAB}/evaluate",data=body,headers={"Content-Type":"application/json"},method="POST")
print(json.loads(urllib.request.urlopen(req,timeout=10).read().decode()).get('result'))
PY

# 5. submit (Confirm Booking)
if [ "$DRY" != "1" ]; then
  python3 <<PY
import json,urllib.request
TAB="$TAB"
expr='''(()=>{
  const btn=[...document.querySelectorAll('button,input[type=submit]')].find(b=>(b.textContent||b.value||'').includes('Confirm Booking')||(b.textContent||'').includes('予約'));
  if(!btn) return 'no submit';
  btn.click();
  return 'submitted';
})()'''
body=json.dumps({"userId":"anicca","sessionKey":"$SESSION","expression":expr}).encode()
req=urllib.request.Request(f"http://127.0.0.1:9377/tabs/{TAB}/evaluate",data=body,headers={"Content-Type":"application/json"},method="POST")
print(json.loads(urllib.request.urlopen(req,timeout=10).read().decode()).get('result'))
PY
  sleep 6
fi

# 6. screenshot for proof
curl -sS "http://127.0.0.1:9377/tabs/$TAB/screenshot?userId=anicca&sessionKey=$SESSION" -o "$RUN/after.png" 2>&1 | head -1 || true

# 7. add gcal event
if [ "$DRY" != "1" ]; then
  /opt/homebrew/bin/gog -a {{profile.contact.personalEmail}} calendar create primary \
    --summary "💇 [TENTATIVE] Rein 散髪 (カット 30分)" \
    --from "${TARGET}T11:00:00+09:00" --to "${TARGET}T11:30:00+09:00" \
    --location "Rein (新宿区四谷1-4 綿半野原ビル1F, 四ツ谷駅徒歩2分)" \
    --description "カット ¥2900 (シャンプー無し)
予約系: reservia.jp
cancellable=true (30 min 前まで、それ以降 ¥1450)
camofox tab=${TAB}" --json > "$RUN/cal.json" || true
fi

# 8. slack
python3 - "$SLACK_CHANNEL_ID" "$SLACK_BOT_TOKEN" "$TARGET" "$RUN" <<'PY'
import sys,json,urllib.request
ch,tok,t,run=sys.argv[1:5]
req=urllib.request.Request("https://slack.com/api/chat.postMessage",
  data=json.dumps({"channel":ch,"text":f"💇 haircut-quarterly: Rein {t} 11:00 booking attempted, raw={run}"}).encode(),
  headers={"Authorization":f"Bearer {tok}","Content-Type":"application/json; charset=utf-8"},method="POST")
urllib.request.urlopen(req,timeout=15)
PY
echo "✅ haircut-quarterly done  raw=$RUN"
