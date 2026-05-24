#!/usr/bin/env bash
# comedy-booking-en install.sh
set -euo pipefail
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

ACCOUNT=""; STAGE_NAME=""; LEGAL_NAME=""; PHONE=""; CITY="SF"; NETA_TYPE="standup"; NETA_LENGTH="5min"; BUDGET="20"; FREQ="monthly"; INSTANCE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --account) ACCOUNT="$2"; shift 2;;
    --{{profile.lateness.stakeholders.senderType}}-name) STAGE_NAME="$2"; shift 2;;
    --{{profile.lateness.stakeholders.senderType}}-name) LEGAL_NAME="$2"; shift 2;;
    --phone) PHONE="$2"; shift 2;;
    --city) CITY="$2"; shift 2;;
    --neta-type) NETA_TYPE="$2"; shift 2;;
    --neta-length) NETA_LENGTH="$2"; shift 2;;
    --budget-per-show) BUDGET="$2"; shift 2;;
    --frequency) FREQ="$2"; shift 2;;
    --instance) INSTANCE="$2"; shift 2;;
    *) echo "unknown flag $1"; exit 1;;
  esac
done

[ -n "$ACCOUNT" ] || { echo "❌ --account required"; exit 1; }
[ -n "$STAGE_NAME" ] || { echo "❌ --{{profile.lateness.stakeholders.senderType}}-name required"; exit 1; }
[ -n "$LEGAL_NAME" ] || { echo "❌ --{{profile.lateness.stakeholders.senderType}}-name required"; exit 1; }
[ -n "$PHONE" ] || { echo "❌ --phone required"; exit 1; }
[ -n "$INSTANCE" ] || INSTANCE=$(echo "$ACCOUNT" | tr '@.' '__')

SKILL=~/.openclaw/skills/anicca-comedy-factory/scripts/booking-en
mkdir -p "$SKILL/data/instances"
CFG="$SKILL/data/instances/${INSTANCE}.json"

python3 - "$CFG" "$ACCOUNT" "$STAGE_NAME" "$LEGAL_NAME" "$PHONE" "$CITY" "$NETA_TYPE" "$NETA_LENGTH" "$BUDGET" "$FREQ" <<'PY'
import sys, json
path, account, {{profile.lateness.stakeholders.senderType}}, {{profile.lateness.stakeholders.senderType}}, phone, city, neta_t, neta_l, budget, freq = sys.argv[1:11]
json.dump({
  "account": account, "{{profile.lateness.stakeholders.senderType}}_name": {{profile.lateness.stakeholders.senderType}}, "{{profile.lateness.stakeholders.senderType}}_name": {{profile.lateness.stakeholders.senderType}}, "phone": phone,
  "city": city, "neta_type": neta_t, "neta_length": neta_l,
  "budget_per_show": int(budget), "frequency": freq,
}, open(path, "w"), ensure_ascii=False, indent=2)
print("config written:", path)
PY

case "$FREQ" in
  monthly)  CRON="0 8 1 * *";;
  biweekly) CRON="0 8 1,15 * *";;
  weekly)   CRON="0 8 * * 1";;
  *) echo "❌ unknown frequency $FREQ"; exit 1;;
esac

CRON_NAME="comedy-booking-en-${INSTANCE}-${CITY}-${FREQ}"
TARGET="channel:${SLACK_CHANNEL_ID:-{{profile.channels.reportChannel}}}"

openclaw cron add \
  --name "$CRON_NAME" \
  --cron "$CRON" \
  --tz "Asia/Tokyo" \
  --agent anicca \
  --model openai-codex/gpt-5.4-mini \
  --to "$TARGET" \
  --message "skill: comedy-booking-en instance=${INSTANCE} (city=${CITY}) を起動。bash ~/.openclaw/skills/anicca-comedy-factory/scripts/booking-en/run.sh --instance ${INSTANCE} を実行。${CITY} の翌月 open mic 1 枠 ({{profile.lateness.stakeholders.senderType}}_name=${STAGE_NAME}, ${NETA_LENGTH} ${NETA_TYPE})。gcal の渡航期間に合わせて。walk-up only の場所は [WALK-UP] flag で gcal 入れる。Slack 報告。" \
  --description "comedy-booking-en ${FREQ} for ${STAGE_NAME} @ ${CITY}" \
  --json 2>&1 | tail -3

echo "✅ installed cron $CRON_NAME (${CRON} JST)"
openclaw gateway restart 2>&1 | tail -1
