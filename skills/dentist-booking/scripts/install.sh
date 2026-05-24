#!/usr/bin/env bash
# dentist-booking install.sh
set -euo pipefail
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

ACCOUNT=""; ADDRESS=""; NAME=""; GENDER="male"; PHONE=""; PREF_CLINIC=""; FREQ="quarterly"; INSTANCE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --account) ACCOUNT="$2"; shift 2;;
    --address) ADDRESS="$2"; shift 2;;
    --name) NAME="$2"; shift 2;;
    --gender) GENDER="$2"; shift 2;;
    --phone) PHONE="$2"; shift 2;;
    --preferred-clinic) PREF_CLINIC="$2"; shift 2;;
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

SKILL=~/.openclaw/skills/dentist-booking
mkdir -p "$SKILL/data/instances"
CFG="$SKILL/data/instances/${INSTANCE}.json"

python3 - "$CFG" "$ACCOUNT" "$ADDRESS" "$NAME" "$GENDER" "$PHONE" "$PREF_CLINIC" "$FREQ" <<'PY'
import sys, json
path, account, address, name, gender, phone, clinic, freq = sys.argv[1:9]
json.dump({
  "account": account, "address": address, "name": name,
  "gender": gender, "phone": phone, "preferred_clinic": clinic or None,
  "frequency": freq,
}, open(path, "w"), ensure_ascii=False, indent=2)
print("config written:", path)
PY

case "$FREQ" in
  monthly)   CRON="0 9 1 * *";;
  quarterly) CRON="0 9 1 2,5,8,11 *";;
  biannual)  CRON="0 9 1 2,8 *";;
  yearly)    CRON="0 9 1 6 *";;
  *) echo "❌ unknown frequency $FREQ"; exit 1;;
esac

CRON_NAME="dentist-booking-${INSTANCE}-${FREQ}"
TARGET="channel:${SLACK_CHANNEL_ID:-{{profile.channels.reportChannel}}}"

openclaw cron add \
  --name "$CRON_NAME" \
  --cron "$CRON" \
  --tz "Asia/Tokyo" \
  --agent anicca \
  --model openai-codex/gpt-5.4-mini \
  --to "$TARGET" \
  --message "skill: dentist-booking instance=${INSTANCE} を起動。bash ~/.openclaw/skills/dentist-booking/scripts/run.sh --instance ${INSTANCE} を実行。preferred-clinic があればそこ、無ければ Maps で 4.3★ 30件+ の歯科発見。土曜午前 10:00 候補 4 つで予約メール / EPARK 予約。gcal [PENDING] 追加、Slack 報告。9-17 平日本業 NG。" \
  --description "dentist-booking ${FREQ} for ${NAME}" \
  --json 2>&1 | tail -3

echo "✅ installed cron $CRON_NAME (${CRON} JST)"
openclaw gateway restart 2>&1 | tail -1
