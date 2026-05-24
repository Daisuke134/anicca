#!/usr/bin/env bash
# barber-booking install.sh — config + auto cron add + gateway restart
set -euo pipefail
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

ACCOUNT=""; ADDRESS=""; NAME=""; GENDER="male"; PHONE=""; PRICE_MAX="5000"; FREQ="quarterly"; INSTANCE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --account) ACCOUNT="$2"; shift 2;;
    --address) ADDRESS="$2"; shift 2;;
    --name) NAME="$2"; shift 2;;
    --gender) GENDER="$2"; shift 2;;
    --phone) PHONE="$2"; shift 2;;
    --price-max) PRICE_MAX="$2"; shift 2;;
    --frequency) FREQ="$2"; shift 2;;
    --instance) INSTANCE="$2"; shift 2;;
    *) echo "unknown flag $1"; exit 1;;
  esac
done

[ -n "$ACCOUNT" ] || { echo "❌ --account required"; exit 1; }
[ -n "$ADDRESS" ] || { echo "❌ --address required"; exit 1; }
[ -n "$NAME" ] || { echo "❌ --name required"; exit 1; }
[ -n "$PHONE" ] || { echo "❌ --phone required"; exit 1; }
[ -n "$INSTANCE" ] || INSTANCE=$(echo "$ACCOUNT" | tr '@.' '__')

SKILL=~/.openclaw/skills/barber-booking
mkdir -p "$SKILL/data/instances"
CFG="$SKILL/data/instances/${INSTANCE}.json"

python3 - "$CFG" "$ACCOUNT" "$ADDRESS" "$NAME" "$GENDER" "$PHONE" "$PRICE_MAX" "$FREQ" <<'PY'
import sys, json
path, account, address, name, gender, phone, price_max, freq = sys.argv[1:9]
json.dump({
  "account": account, "address": address, "name": name,
  "gender": gender, "phone": phone, "price_max": int(price_max),
  "frequency": freq,
}, open(path, "w"), ensure_ascii=False, indent=2)
print("config written:", path)
PY

# cron expr based on frequency
case "$FREQ" in
  monthly)   CRON="0 9 15 * *";;
  quarterly) CRON="0 9 15 3,6,9,12 *";;
  biannual)  CRON="0 9 15 3,9 *";;
  yearly)    CRON="0 9 15 6 *";;
  *) echo "❌ unknown frequency $FREQ"; exit 1;;
esac

CRON_NAME="barber-booking-${INSTANCE}-${FREQ}"
TARGET="channel:${SLACK_CHANNEL_ID:-{{profile.channels.reportChannel}}}"

openclaw cron add \
  --name "$CRON_NAME" \
  --cron "$CRON" \
  --tz "Asia/Tokyo" \
  --agent anicca \
  --model openai-codex/gpt-5.4-mini \
  --to "$TARGET" \
  --message "skill: barber-booking instance=${INSTANCE} を起動。bash ~/.openclaw/skills/barber-booking/scripts/run.sh --instance ${INSTANCE} を実行。Google Maps で 4.3★+ かつ ¥${PRICE_MAX} 以下の美容室を ${ADDRESS} 周辺で発見、reservia or HotPepper or {{profile.lateness.stakeholders.channel}} backup で予約完走、gcal [CONFIRMED] 追加、Slack #metrics 報告。9-17 平日本業ブロック避ける。HARD RULE #4 適用 (<training-school>/所属 書かない)。" \
  --description "barber-booking ${FREQ} for ${NAME}" \
  --json 2>&1 | tail -3

echo "✅ installed cron $CRON_NAME (${CRON} JST)"
openclaw gateway restart 2>&1 | tail -1
