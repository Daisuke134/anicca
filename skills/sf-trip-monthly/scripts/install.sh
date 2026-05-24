#!/usr/bin/env bash
# sf-trip-monthly install.sh
set -euo pipefail
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

ACCOUNT=""; LEGAL_NAME=""; PHONE=""; HOME_AIRPORT="NRT"
TARGET_CITY="SF"; TARGET_AIRPORT="SFO"; PTO_BUDGET="1"
HOTEL_PREF="Samesun SF"; HOTEL_BUDGET="70"; FLIGHT_BUDGET="1200"
WORK_BLOCK="Mon-Fri 9-17 JST"; FREQ="monthly"; INSTANCE=""

while [ $# -gt 0 ]; do
  case "$1" in
    --account) ACCOUNT="$2"; shift 2;;
    --{{profile.lateness.stakeholders.senderType}}-name) LEGAL_NAME="$2"; shift 2;;
    --phone) PHONE="$2"; shift 2;;
    --home-airport) HOME_AIRPORT="$2"; shift 2;;
    --target-city) TARGET_CITY="$2"; shift 2;;
    --target-airport) TARGET_AIRPORT="$2"; shift 2;;
    --pto-budget) PTO_BUDGET="$2"; shift 2;;
    --hotel-pref) HOTEL_PREF="$2"; shift 2;;
    --hotel-budget) HOTEL_BUDGET="$2"; shift 2;;
    --flight-budget) FLIGHT_BUDGET="$2"; shift 2;;
    --work-block) WORK_BLOCK="$2"; shift 2;;
    --frequency) FREQ="$2"; shift 2;;
    --instance) INSTANCE="$2"; shift 2;;
    *) echo "unknown flag $1"; exit 1;;
  esac
done

[ -n "$ACCOUNT" ] || { echo "❌ --account required"; exit 1; }
[ -n "$LEGAL_NAME" ] || { echo "❌ --{{profile.lateness.stakeholders.senderType}}-name required"; exit 1; }
[ -n "$INSTANCE" ] || INSTANCE=$(echo "$ACCOUNT" | tr '@.' '__')

SKILL=~/.openclaw/skills/sf-trip-monthly
mkdir -p "$SKILL/data/instances"
CFG="$SKILL/data/instances/${INSTANCE}.json"

python3 - "$CFG" "$ACCOUNT" "$LEGAL_NAME" "$PHONE" "$HOME_AIRPORT" "$TARGET_CITY" "$TARGET_AIRPORT" "$PTO_BUDGET" "$HOTEL_PREF" "$HOTEL_BUDGET" "$FLIGHT_BUDGET" "$WORK_BLOCK" "$FREQ" <<'PY'
import sys, json
path, account, {{profile.lateness.stakeholders.senderType}}, phone, home_ap, city, target_ap, pto, hotel, hotel_b, flight_b, work, freq = sys.argv[1:14]
json.dump({
  "account": account, "{{profile.lateness.stakeholders.senderType}}_name": {{profile.lateness.stakeholders.senderType}}, "phone": phone,
  "home_airport": home_ap, "target_city": city, "target_airport": target_ap,
  "pto_budget_days": int(pto), "hotel_pref": hotel,
  "hotel_budget_per_night_usd": int(hotel_b), "flight_budget_round_trip_usd": int(flight_b),
  "work_block": work, "frequency": freq,
}, open(path, "w"), ensure_ascii=False, indent=2)
print("config written:", path)
PY

case "$FREQ" in
  monthly) CRON="0 8 1 * *";;
  biweekly) CRON="0 8 1,15 * *";;
  weekly) CRON="0 8 * * 1";;
  *) echo "❌ unknown frequency $FREQ"; exit 1;;
esac

CRON_NAME="sf-trip-${INSTANCE}-${FREQ}"
TARGET="channel:${SLACK_CHANNEL_ID:-{{profile.channels.reportChannel}}}"

openclaw cron add \
  --name "$CRON_NAME" \
  --cron "$CRON" \
  --tz "Asia/Tokyo" \
  --agent anicca \
  --model openai-codex/gpt-5.4-mini \
  --to "$TARGET" \
  --message "skill: sf-trip-monthly instance=${INSTANCE} を起動。bash ~/.openclaw/skills/sf-trip-monthly/scripts/run.sh --instance ${INSTANCE} を実行。来月の ${TARGET_CITY} AI trip を plan + book: ①Lu.ma + CV + AIT で events discover ②open mic discover ③letsfg + Google Flights で最安 flight (max \\\$${FLIGHT_BUDGET}) ④Samesun book (max \\\$${HOTEL_BUDGET}/night) ⑤gcal 更新 + Slack 報告。${WORK_BLOCK} 抵触禁止、PTO max ${PTO_BUDGET} 日。" \
  --description "sf-trip-monthly ${FREQ} for ${LEGAL_NAME}" \
  --json 2>&1 | tail -3

echo "✅ installed cron $CRON_NAME (${CRON} JST)"
openclaw gateway restart 2>&1 | tail -1
