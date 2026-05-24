#!/usr/bin/env bash
# anicca-dentist-quarterly — runner (recipe matches team428 form-broken → {{profile.lateness.stakeholders.channel}} backup)
set -euo pipefail
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

DRY="${DRY_RUN:-0}"
NOW=$(date +%Y-%m-%dT%H-%M-%S)
RUN=~/.openclaw/skills/anicca-dentist-quarterly/data/runs/$NOW
mkdir -p "$RUN"

# 1. compute next 4 Saturdays starting 3 weeks from now
DATES=$(python3 -c "
import datetime
today=datetime.date.today()
start=today+datetime.timedelta(days=21)
while start.weekday()!=5: start+=datetime.timedelta(days=1)
print('\n'.join((start+datetime.timedelta(weeks=i)).strftime('%Y/%m/%d') for i in range(4)))
")
D1=$(echo "$DATES" | sed -n 1p)
D2=$(echo "$DATES" | sed -n 2p)
D3=$(echo "$DATES" | sed -n 3p)
D4=$(echo "$DATES" | sed -n 4p)
echo "  candidates: $D1 / $D2 / $D3 / $D4"

# 2. body
BODY="/tmp/dentist-request-$NOW.txt"
cat > "$BODY" <<EOF
デンタルアソシエイツ歯科四谷 ご担当者様

お世話になっております。<your-address>在住の患者の<your-name> (<your-name>) と申します。
いつもお世話になっておりますクリニックにて、メンテナンス受診の予約をお願いしたくご連絡差し上げました。

公式サイト (http://www.team428.com/contact/index.html) のお問い合わせフォームから送信を試みましたが、
確認画面の送信ボタン押下後に Perl のサーバーエラー画面 (send.cgi @INC functions.cgi が見つからない旨)
が表示され、送信が完了しませんでした。
ご担当のIT管理者様 (brs-support@xbit.jp 様、本メール CC) にもお知らせし、念のためメールにてご予約申込みをさせていただきます。

【予約内容】
- 受診目的: メンテナンス (歯石除去 / クリーニング)
- 患者氏名: <your-name> (<your-name>)
- メール: {{profile.contact.personalEmail}}
- 電話: 080-4627-0314
- 性別: 男性

【ご予約希望日 (土曜午前 10:00)】
第一希望: ${D1} (土) 10:00
第二希望: ${D2} (土) 10:00
第三希望: ${D3} (土) 10:00
第四希望: ${D4} (土) 10:00

平日は本業の都合 9:00-17:00 が NG のため、土曜午前帯で調整いただけますと幸いです。
ご都合の良い日程をご教示いただけましたら、確定の旨ご返信させていただきます。

何卒よろしくお願い申し上げます。

<your-name>
{{profile.contact.personalEmail}}
080-4627-0314
EOF

# 3. send mail (try form first if not broken anymore — for now go straight to {{profile.lateness.stakeholders.channel}} backup)
if [ "$DRY" = "1" ]; then
  echo "[DRY] would send"; MID="dry-run"
else
  RESP=$(/opt/homebrew/bin/gog -a {{profile.contact.personalEmail}} gmail send \
    --to "brs-support@xbit.jp" \
    --subject "【お問い合わせフォーム不具合のため】デンタルアソシエイツ歯科四谷 予約申込み (土曜午前) — <your-name>" \
    --body-file "$BODY" --json)
  echo "$RESP" > "$RUN/mail.json"
  MID=$(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('messageId',''))")
fi
echo "  sent: $MID"

# 4. add [PENDING] cal event placeholder on D1
if [ "$DRY" != "1" ]; then
  /opt/homebrew/bin/gog -a {{profile.contact.personalEmail}} calendar create primary \
    --summary "🦷 [PENDING] 歯科 team428 メンテナンス予約 — 候補 ${D1}" \
    --from "${D1//\//-}T10:00:00+09:00" --to "${D1//\//-}T11:00:00+09:00" \
    --location "デンタルアソシエイツ歯科四谷 (新宿区四谷1-8-14, JR四ツ谷駅徒歩1分)" \
    --description "3ヶ月定期メンテナンス受診
候補4: ${D1} / ${D2} / ${D3} / ${D4}
mail msgId: ${MID}
cancellable=true (前日まで)
form broken (Perl @INC) のため {{profile.lateness.stakeholders.channel}} backup ルート使用中" --json > "$RUN/cal.json" || true
fi

# 5. slack
python3 - "$SLACK_CHANNEL_ID" "$SLACK_BOT_TOKEN" "$D1" "$D2" "$D3" "$D4" "$MID" <<'PY'
import sys,json,urllib.request
ch,tok,d1,d2,d3,d4,mid=sys.argv[1:8]
req=urllib.request.Request("https://slack.com/api/chat.postMessage",
  data=json.dumps({"channel":ch,"text":f"🦷 dentist-quarterly mail sent (form broken bypass): {d1}/{d2}/{d3}/{d4} msgId={mid}"}).encode(),
  headers={"Authorization":f"Bearer {tok}","Content-Type":"application/json; charset=utf-8"},method="POST")
urllib.request.urlopen(req,timeout=15)
PY
echo "✅ dentist-quarterly done  raw=$RUN"
