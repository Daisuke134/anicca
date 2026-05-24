#!/usr/bin/env bash
# lib/recruit-platform.sh — multi-platform performer recruitment.
#
# Usage:
#   recruit-platform.sh post <platform> <city> <date> <set_length_min> <budget>
#   recruit-platform.sh poll <platform>
#   recruit-platform.sh accept <platform> <applicant_id>
#
# Platforms: cloudworks (JP) / indeed (JP+US) / timee (JP) / taskrabbit (US)
#
# 全 agent-{{profile.lateness.stakeholders.channel}} 経由で操作。事前に下記 skill を load:
#   agent-{{profile.lateness.stakeholders.channel}} skills get core --full
#
# このラッパー自体は agent-{{profile.lateness.stakeholders.channel}} の skill (agent-{{profile.lateness.stakeholders.channel}} navigate /
# agent-{{profile.lateness.stakeholders.channel}} fill / agent-{{profile.lateness.stakeholders.channel}} snapshot) を呼ぶ thin shell。
# DOM selector は hardcode しない — agent-{{profile.lateness.stakeholders.channel}} snapshot の eN ref を使う。
#
# state: data/recruit/<platform>-<job_id>.json で永続化
# Slack: 全 step で #metrics に流す

set -uo pipefail

ACTION="${1:?}"
PLATFORM="${2:?}"

SKILL_DIR="$HOME/.openclaw/skills/anicca-comedy-factory"
DATA_DIR="$SKILL_DIR/data/recruit"
mkdir -p "$DATA_DIR"

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
source "$HOME/.openclaw/skills/sao-content-factory/lib/slack.sh"

PLATFORM_URL=""
case "$PLATFORM" in
  cloudworks)  PLATFORM_URL="https://crowdworks.jp/public/jobs/new" ;;
  indeed)      PLATFORM_URL="https://www.indeed.com/employers/jobs/new" ;;
  timee)       PLATFORM_URL="https://timee.co.jp/business/dashboard/recruit/new" ;;
  taskrabbit)  PLATFORM_URL="https://www.taskrabbit.com/post-task" ;;
  *) echo "❌ unknown platform: $PLATFORM"; exit 1 ;;
esac

case "$ACTION" in
  post)
    CITY="${3:?}"; DATE="${4:?}"; SET_MIN="${5:?}"; BUDGET="${6:?}"
    JOB_ID="${PLATFORM}-${CITY}-${DATE}-$(date +%s)"
    STATE="$DATA_DIR/${JOB_ID}.json"

    TITLE_JP="【急募】Anicca 脚本で ${SET_MIN}-min stand-up 演じる comedy performer (${CITY} ${DATE})"
    TITLE_EN="[URGENT] Comedy performer for ${SET_MIN}-min Anicca-written stand-up (${CITY} ${DATE})"
    DESC=$(cat <<EOF
Anicca ({{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}} — 諸行無常 をテーマにした AI コメディアン) が書いた ${SET_MIN}-min の stand-up
を ${CITY} の open mic で演じてくれる方を募集。

報酬: ${BUDGET} (当日 Stripe で payout)
日時: ${DATE} 夜 (具体的時間は採用後 共有)
持ち物: なし (脚本と練習動画は採用後 メールで送付)
資格: comedic delivery, ${PLATFORM} の standard

応募方法: 過去の comedy 経験 (動画 / SNS link 1 つ) を添えて応募。
Anicca が AI で screening → 上位採用 → 当日 連絡。

aniccaai.com/comedy
EOF
)

    # Save initial state
    jq -n --arg id "$JOB_ID" --arg p "$PLATFORM" --arg c "$CITY" --arg d "$DATE" \
       --arg s "$SET_MIN" --arg b "$BUDGET" --arg t "$TITLE_JP" \
       '{job_id: $id, platform: $p, city: $c, date: $d, set_length_min: ($s|tonumber), budget: $b, title: $t, status: "drafted", url: "", applicants: []}' > "$STATE"

    echo "▶ recruit-platform: drafted job ${JOB_ID} for ${PLATFORM_URL}"
    echo "  next: agent-{{profile.lateness.stakeholders.channel}} に skill load → POST → URL 取得 → state 更新"
    echo "  agent-{{profile.lateness.stakeholders.channel}} skills get core --full"
    echo "  agent-{{profile.lateness.stakeholders.channel}} navigate \"$PLATFORM_URL\""
    echo "  agent-{{profile.lateness.stakeholders.channel}} fill <eN-ref-from-snapshot> \"$TITLE_JP\""
    echo "  ... (form fields per platform)"
    echo "  agent-{{profile.lateness.stakeholders.channel}} snapshot -i  # capture posted job URL → save to state.url"

    slack_metrics "*comedy recruit drafted:* ${PLATFORM} ${CITY} ${DATE} budget=${BUDGET}\nstate=${STATE}\nnext: agent-{{profile.lateness.stakeholders.channel}} で form submit (手動 or future automation)" >/dev/null || true
    echo "✅ recruit-platform post: drafted=$JOB_ID"
    ;;

  poll)
    # Gmail 経由で 応募者通知 を引く (Phase 1 minimum)
    QUERY="from:${PLATFORM}.com newer_than:7d (応募 OR application OR applicant)"
    APPS=$(/opt/homebrew/bin/gog gmail search --query "$QUERY" --account "${GOG_ACCOUNT:-{{profile.contact.personalEmail}}}" --max 20 --json 2>/dev/null || echo '{"messages":[]}')
    N=$(echo "$APPS" | jq '.messages | length' 2>/dev/null || echo 0)
    echo "✅ recruit-platform poll ${PLATFORM}: ${N} applicant notification(s)"
    ;;

  accept)
    APPLICANT_ID="${3:?}"
    echo "▶ recruit-platform accept ${PLATFORM}/${APPLICANT_ID} — TODO: send Anicca skit + practice video via Gmail"
    echo "✅ recruit-platform accept: drafted (next: gog send to applicant {{profile.lateness.stakeholders.channel}} + Stripe Connect Express invite)"
    ;;

  *) echo "❌ unknown action: $ACTION"; exit 1 ;;
esac
