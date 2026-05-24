#!/usr/bin/env bash
# kpro-gereron-apply-weekly.sh — Mon 09:00 JST cron
#
# K-PRO ゲレロンステージ (entry@kpro-web.com): pin 2000 yen, Sat/Sun heavy.
# Sends weekly application {{profile.lateness.stakeholders.channel}} targeting next 2-3 weeks of weekend slots.
#
# state: data/kpro-gereron/<week>.json (idempotent per week)

set -uo pipefail

SKILL_DIR="$HOME/.openclaw/skills/anicca-comedy-factory"
DATA_DIR="$SKILL_DIR/data/kpro-gereron"
mkdir -p "$DATA_DIR"

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
source "$HOME/.openclaw/skills/sao-content-factory/lib/slack.sh"

WEEK=$(date "+%Y-%m-%d")
STATE="$DATA_DIR/${WEEK}.json"
[ -f "$STATE" ] && [ "${FORCE:-0}" != "1" ] && { echo "skip: already sent $WEEK"; exit 0; }

# Compute next 4 weekend dates
NEXT_SAT=$(date -j -v+Sat "+%Y-%m-%d")
NEXT_SUN=$(date -j -v+Sun "+%Y-%m-%d")

BODY=$(cat <<EOF
ゲレロンステージ運営の皆様

お世話になります。
<your-school>生 1 年目の 成田 大輔 ({{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}) と申します。

ゲレロンステージへの出演を希望しております。
下記の通りご応募申し上げます。

希望日時: ${NEXT_SAT} (土) もしくは ${NEXT_SUN} (日) いずれかの公演 (枠が空いている回でお願いいたします)
グループ名: {{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}} (Anicca)
代表者氏名: 成田 大輔 (<your-name>)
連絡先: {{profile.contact.personalEmail}}
ネタ形態: ピン

可能であれば 2 分のピンネタ で出演させていただきたく、
お席が空いていましたらご検討お願いいたします。

何卒よろしくお願いいたします。

成田 大輔
{{profile.contact.personalEmail}}
https://aniccaai.com/comedy
EOF
)

/opt/homebrew/bin/gog gmail send \
  --account {{profile.contact.personalEmail}} \
  --to "entry@kpro-web.com" \
  --subject "ゲレロンステージ 出演応募 / {{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}} (ピン) — 成田 大輔 ${NEXT_SAT} or ${NEXT_SUN}" \
  --body "$BODY" \
  --json 2>&1 > "$STATE.tmp"

MID=$(jq -r '.messageId // "FAIL"' "$STATE.tmp" 2>/dev/null || echo FAIL)
if [ "$MID" = "FAIL" ] || [ -z "$MID" ]; then
  slack_metrics "❌ kpro-gereron-apply-weekly: send failed week=$WEEK" >/dev/null || true
  rm -f "$STATE.tmp"
  echo "❌ kpro-gereron-apply-weekly: send failed"
  exit 1
fi

mv "$STATE.tmp" "$STATE"
slack_metrics "*📨 kpro-gereron-apply-weekly:* メール送信完了 (msg=${MID}). ${NEXT_SAT} or ${NEXT_SUN} (土日) ピン枠で応募." >/dev/null || true
echo "✅ kpro-gereron-apply-weekly: sent ${MID} for ${NEXT_SAT}/${NEXT_SUN}"
