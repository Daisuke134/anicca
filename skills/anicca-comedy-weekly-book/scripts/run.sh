#!/usr/bin/env bash
# anicca-comedy-weekly-book — recipe-style runner
# Usage: run.sh [DRY_RUN=1]
set -euo pipefail
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

DRY="${DRY_RUN:-0}"
NOW=$(date +%Y-%m-%dT%H-%M-%S)
RUN=~/.openclaw/skills/anicca-comedy-weekly-book/data/runs/$NOW
mkdir -p "$RUN"

echo "▶ comedy-weekly-book  $NOW  dry=$DRY"

# 1. snapshot Cal next 14 days
FROM=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
TO=$(date -u -v+14d '+%Y-%m-%dT%H:%M:%SZ')
/opt/homebrew/bin/gog -a {{profile.contact.personalEmail}} calendar list primary --from "$FROM" --to "$TO" --max 60 --json --results-only > "$RUN/cal.json"

# 2. scrape U&C パワーオブフリー schedule
/opt/homebrew/bin/firecrawl scrape "http://uandcenterprise.jp/entry.php" markdown > "$RUN/uandc.md"

# 3. pick candidate (next week, not in 9-17 work block, not conflicting)
CANDIDATE=$(python3 - "$RUN/cal.json" "$RUN/uandc.md" <<'PY'
import sys, json, re, datetime
cal=json.load(open(sys.argv[1]))
events=cal if isinstance(cal,list) else cal.get('events',[])
busy=[]
for e in events:
    s=e.get('start',{}).get('dateTime') or e.get('start',{}).get('date')
    en=e.get('end',{}).get('dateTime') or e.get('end',{}).get('date')
    if s and en: busy.append((s,en,e.get('summary','')))
txt=open(sys.argv[2]).read()
# parse vols + dates
shows=[]
for m in re.finditer(r'パワーオブフリー\(Ｓ\)\s*vol\.千(\d+).*?日にち\s*\|\s*(\d{4}/\d+/\d+)\((.)\).*?時間\s*\|\s*開場\s*(\d{1,2}:\d{2})／開演\s*(\d{1,2}:\d{2}).*?会場\s*\|\s*([^\n|]+).*?入り時間\s*\|\s*(\d{1,2}:\d{2})', txt, re.DOTALL):
    vol,d,wd,kaijo,kaien,venue,iri=m.groups()
    shows.append({'vol':vol,'date':d,'wd':wd,'kaijo':kaijo,'kaien':kaien,'venue':venue.strip(),'iri':iri})
# pick: next 14 days, not in 9-17 weekday work block, not conflicting
today=datetime.date.today()
def parse(d): return datetime.datetime.strptime(d,'%Y/%m/%d').date()
picked=None
for s in shows:
    dt=parse(s['date'])
    if dt<=today or (dt-today).days>14: continue
    iri_h,iri_m=map(int,s['iri'].split(':'))
    iri_dt=datetime.datetime.combine(dt, datetime.time(iri_h,iri_m))
    # weekday + 17:00 or earlier 入り → skip (work block)
    if dt.weekday()<5 and iri_h<17: continue
    # check conflicts (rough)
    conflict=False
    for bs,be,ss in busy:
        try:
            bs_dt=datetime.datetime.fromisoformat(bs.replace('Z','+00:00'))
            be_dt=datetime.datetime.fromisoformat(be.replace('Z','+00:00'))
        except: continue
        iri_dt_tz=iri_dt.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=9)))
        if bs_dt<=iri_dt_tz<be_dt:
            conflict=True; break
    if conflict: continue
    picked=s; break
print(json.dumps(picked or {}))
PY
)
echo "  candidate: $CANDIDATE"
echo "$CANDIDATE" > "$RUN/candidate.json"

VOL=$(echo "$CANDIDATE" | python3 -c "import sys,json;print(json.load(sys.stdin).get('vol',''))")
if [ -z "$VOL" ]; then
  echo "❌ no candidate. skipping."
  # slack note
  python3 - "$SLACK_CHANNEL_ID" "$SLACK_BOT_TOKEN" <<'PY'
import sys,json,urllib.request
ch,tok=sys.argv[1:3]
req=urllib.request.Request("https://slack.com/api/chat.postMessage",
  data=json.dumps({"channel":ch,"text":"🎤 comedy-weekly-book: no candidate this week (all 9-17 conflict or already booked)"}).encode(),
  headers={"Authorization":f"Bearer {tok}","Content-Type":"application/json; charset=utf-8"},method="POST")
urllib.request.urlopen(req,timeout=15)
PY
  exit 0
fi

DATE=$(echo "$CANDIDATE" | python3 -c "import sys,json;print(json.load(sys.stdin).get('date',''))")
WD=$(echo "$CANDIDATE" | python3 -c "import sys,json;print(json.load(sys.stdin).get('wd',''))")
KAIJO=$(echo "$CANDIDATE" | python3 -c "import sys,json;print(json.load(sys.stdin).get('kaijo',''))")
KAIEN=$(echo "$CANDIDATE" | python3 -c "import sys,json;print(json.load(sys.stdin).get('kaien',''))")
VENUE=$(echo "$CANDIDATE" | python3 -c "import sys,json;print(json.load(sys.stdin).get('venue',''))")
IRI=$(echo "$CANDIDATE" | python3 -c "import sys,json;print(json.load(sys.stdin).get('iri',''))")

# 4. compose entry mail
BODY="/tmp/uandc-entry-$NOW.txt"
cat > "$BODY" <<EOF
U&Cエンタプライズ ライブエントリー担当者様

お世話になっております。
下記の通り「パワーオブフリー(Ｓ) vol.千${VOL}」への出演エントリーをお願いいたします。

希望月日・曜日◆ ${DATE}(${WD})

ライブ名◆ パワーオブフリー(Ｓ) vol.千${VOL}

ユニット名◆ {{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}

人数(ピンorコンビorトリオ)◆ ピン

ネタ形態(漫才orコントor漫談)◆ 漫談

代表者名(必ず本名)◆ <your-name>

電話番号◆ 080-4627-0314

連絡先メール: {{profile.contact.personalEmail}}

キャンセルポリシー (5日前以降キャンセル料発生 / 2日前以降は理由問わず発生) を承知の上、エントリーさせていただきます。

何卒よろしくお願いいたします。

{{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}} (<your-name>)
{{profile.contact.personalEmail}}
080-4627-0314
EOF

# 5. send mail
if [ "$DRY" = "1" ]; then
  echo "[DRY] would send entry mail"
  MID="dry-run"
else
  RESP=$(/opt/homebrew/bin/gog -a {{profile.contact.personalEmail}} gmail send \
    --to "live_entry@yahoo.co.jp" \
    --subject "ライブ出演希望 — パワーオブフリー(Ｓ) vol.千${VOL} / {{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}(ピン)" \
    --body-file "$BODY" --json)
  echo "$RESP" > "$RUN/mail.json"
  MID=$(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('messageId',''))")
fi
echo "  mail sent: $MID"

# 6. add to gcal [TENTATIVE]
if [ "$DRY" != "1" ]; then
  # gcal block must START at DEPARTURE (home→会場 travel buffer), not 入り time — Dais is
  # human, transport takes time, never late. 家→新宿バッシュ ≈ 30min.
  ISO_DATE="${DATE/\//-}"
  DEP_HM=$(python3 -c "import datetime;t=datetime.datetime.strptime('${IRI}','%H:%M')-datetime.timedelta(minutes=30);print(t.strftime('%H:%M'))")
  START="${ISO_DATE}T${DEP_HM}:00+09:00"
  END_HM=$(python3 -c "h,m=map(int,'${KAIEN}'.split(':'));h+=2; print(f'{h:02d}:{m:02d}')")
  END="${ISO_DATE}T${END_HM}:00+09:00"
  /opt/homebrew/bin/gog -a {{profile.contact.personalEmail}} calendar create primary \
    --summary "🎤 [TENTATIVE] パワーオブフリー(S) vol.千${VOL} — {{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}(ピン 漫談 3分)" \
    --from "$START" --to "$END" \
    --location "$VENUE" \
    --description "出発 ${DEP_HM} (家→会場 移動30分・buffer込み, 遅刻厳禁) / 入り ${IRI} / 開場 ${KAIJO} / 開演 ${KAIEN}
ネタ尺 3分 (2:45 徐々暗転)
ピン 漫談、芸名 {{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}
エントリー料 ¥2000 (現金、お釣り銭なし推奨)
cancellable=false from 2 days before
申込 mail msgId: ${MID}" --json > "$RUN/cal.json" || true
fi

# 7. Slack
python3 - "$SLACK_CHANNEL_ID" "$SLACK_BOT_TOKEN" "$VOL" "$DATE" "$KAIEN" "$VENUE" "$MID" <<'PY'
import sys, json, urllib.request
ch,tok,vol,date,kaien,venue,mid=sys.argv[1:8]
payload={
  "channel":ch,
  "text":f"🎤 comedy-weekly-book: vol.千{vol} {date} {kaien} {venue} entry sent",
  "blocks":[
    {"type":"header","text":{"type":"plain_text","text":"🎤 comedy weekly entry"}},
    {"type":"section","fields":[
      {"type":"mrkdwn","text":f"*ライブ:*\nパワーオブフリー(S) vol.千{vol}"},
      {"type":"mrkdwn","text":f"*日時:*\n{date} 開演 {kaien}"},
      {"type":"mrkdwn","text":f"*会場:*\n{venue}"},
      {"type":"mrkdwn","text":f"*mail msgId:*\n`{mid}`"},
    ]},
  ],
}
req=urllib.request.Request("https://slack.com/api/chat.postMessage",
  data=json.dumps(payload).encode(),
  headers={"Authorization":f"Bearer {tok}","Content-Type":"application/json; charset=utf-8"},method="POST")
urllib.request.urlopen(req,timeout=15)
PY

echo "✅ comedy-weekly-book complete  raw=$RUN"
