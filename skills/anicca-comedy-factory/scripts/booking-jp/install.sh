#!/usr/bin/env bash
# comedy-booking-jp install.sh
set -euo pipefail
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

ACCOUNT=""; STAGE_NAME=""; LEGAL_NAME=""; PHONE=""; NETA_TYPE="漫談"; NETA_LENGTH="3min"; PERSONA="pin"; BUDGET="2500"; FREQ="weekly"; INSTANCE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --account) ACCOUNT="$2"; shift 2;;
    --{{profile.lateness.stakeholders.senderType}}-name) STAGE_NAME="$2"; shift 2;;
    --{{profile.lateness.stakeholders.senderType}}-name) LEGAL_NAME="$2"; shift 2;;
    --phone) PHONE="$2"; shift 2;;
    --neta-type) NETA_TYPE="$2"; shift 2;;
    --neta-length) NETA_LENGTH="$2"; shift 2;;
    --persona-type) PERSONA="$2"; shift 2;;
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

SKILL=~/.openclaw/skills/anicca-comedy-factory/scripts/booking-jp
mkdir -p "$SKILL/data/instances"
CFG="$SKILL/data/instances/${INSTANCE}.json"

python3 - "$CFG" "$ACCOUNT" "$STAGE_NAME" "$LEGAL_NAME" "$PHONE" "$NETA_TYPE" "$NETA_LENGTH" "$PERSONA" "$BUDGET" "$FREQ" <<'PY'
import sys, json
path, account, {{profile.lateness.stakeholders.senderType}}, {{profile.lateness.stakeholders.senderType}}, phone, neta_t, neta_l, persona, budget, freq = sys.argv[1:11]
json.dump({
  "account": account, "{{profile.lateness.stakeholders.senderType}}_name": {{profile.lateness.stakeholders.senderType}}, "{{profile.lateness.stakeholders.senderType}}_name": {{profile.lateness.stakeholders.senderType}}, "phone": phone,
  "neta_type": neta_t, "neta_length": neta_l, "persona": persona,
  "budget_per_show": int(budget), "frequency": freq,
}, open(path, "w"), ensure_ascii=False, indent=2)
print("config written:", path)
PY

case "$FREQ" in
  weekly)   CRON="0 8 * * 1";;
  biweekly) CRON="0 8 1,15 * *";;
  monthly)  CRON="0 8 1 * *";;
  *) echo "❌ unknown frequency $FREQ"; exit 1;;
esac

CRON_NAME="comedy-booking-jp-${INSTANCE}-${FREQ}"
TARGET="channel:${SLACK_CHANNEL_ID:-{{profile.channels.reportChannel}}}"

openclaw cron add \
  --name "$CRON_NAME" \
  --cron "$CRON" \
  --tz "Asia/Tokyo" \
  --agent anicca \
  --model openai-codex/gpt-5.4-mini \
  --to "$TARGET" \
  --message "skill: comedy-booking-jp instance=${INSTANCE} を起動。bash ~/.openclaw/skills/anicca-comedy-factory/scripts/booking-jp/run.sh --instance ${INSTANCE} を実行。来週の Tokyo open mic 1 枠を取る (U&C / GRIP / たか7 / K-PRO の順に試す)。9-17 work block 外、土日もしくは平日夜。{{profile.lateness.stakeholders.senderType}}_name=${STAGE_NAME} ピン ${NETA_TYPE}。<training-school>/所属 一切書かない (HARD RULE #4)。gcal [TENTATIVE] 追加。Slack 報告。" \
  --description "comedy-booking-jp ${FREQ} for ${STAGE_NAME}" \
  --json 2>&1 | tail -3

echo "✅ installed cron $CRON_NAME (${CRON} JST)"
openclaw gateway restart 2>&1 | tail -1
