#!/usr/bin/env bash
# comedy-watch-replies-6h — 6h 毎、全 reply chain を監視
#
# Watches:
#   1. Mutiny / 他 venue host への live-apply メールへの返信
#   2. クラウドワークス / Indeed / Timee / TaskRabbit からの応募者通知
#   3. Stripe Checkout webhook 由来の comedy ticket purchase notify
#   4. Dais Slack DM の sickness 検知 (キーワード: 体調 / sick / cancel)
#
# 各カテゴリの新着を Slack #metrics に流す + 該当 event-driven script を発火。
#
# stdout last line: ✅ watch-replies-6h: <reply_n>/<applicant_n>/<ticket_n>/<sickness_flag>

set -uo pipefail

SKILL_DIR="$HOME/.openclaw/skills/anicca-comedy-factory"
DATA_DIR="$SKILL_DIR/data"
STATE_DIR="$SKILL_DIR/state"
mkdir -p "$STATE_DIR"

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
: "${GOG_ACCOUNT:={{profile.contact.personalEmail}}}"

source "$HOME/.openclaw/skills/sao-content-factory/lib/slack.sh"

LAST_CHECK_FILE="$STATE_DIR/watch-replies-last.json"
[ -f "$LAST_CHECK_FILE" ] || echo '{}' > "$LAST_CHECK_FILE"

# 1. Venue host 返信 — live-events JSON に message_id を持つ thread への返信
reply_count=0
while IFS= read -r f; do
  [ -z "$f" ] && continue
  N=$(jq '.candidates | length' "$f")
  for i in $(seq 0 $((N - 1))); do
    applied=$(jq -r ".candidates[$i].applied // false" "$f")
    [ "$applied" != "true" ] && continue
    tid=$(jq -r ".candidates[$i].thread_id // .candidates[$i].message_id // empty" "$f")
    [ -z "$tid" ] && continue
    # Check thread for new replies (msg count > 1 means host replied)
    msgs=$(/opt/homebrew/bin/gog gmail thread "$tid" --account "$GOG_ACCOUNT" --json 2>/dev/null | jq '.messages | length' 2>/dev/null || echo 0)
    if [ "$msgs" -gt 1 ]; then
      # Already noted?
      noted=$(jq -r --arg t "$tid" '.noted_threads[$t] // empty' "$LAST_CHECK_FILE")
      if [ -z "$noted" ]; then
        venue=$(jq -r ".candidates[$i].name" "$f")
        date=$(jq -r '.date' "$f")
        slack_metrics "*comedy host reply!* venue=${venue} date=${date} thread=https://mail.google.com/mail/u/0/#inbox/${tid} msgs=${msgs}" >/dev/null || true
        tmp=$(mktemp)
        jq --arg t "$tid" --argjson m "$msgs" '.noted_threads[$t] = $m' "$LAST_CHECK_FILE" > "$tmp" && mv "$tmp" "$LAST_CHECK_FILE"
        reply_count=$((reply_count + 1))
      fi
    fi
  done
done < <(find "$DATA_DIR/live-events" -name "*.json" -mtime -90 2>/dev/null)

# 2. クラウドワークス / Indeed / Timee / TaskRabbit 応募通知 (Gmail 検索)
applicant_count=0
QUERY='from:(crowdworks.jp OR indeed.com OR timee.co.jp OR taskrabbit.com) subject:(応募 OR application OR new applicant) newer_than:1d is:unread'
APPS=$(/opt/homebrew/bin/gog gmail search --query "$QUERY" --account "$GOG_ACCOUNT" --max 20 --json 2>/dev/null || echo '{"messages":[]}')
applicant_count=$(echo "$APPS" | jq '.messages | length' 2>/dev/null || echo 0)
if [ "$applicant_count" -gt 0 ]; then
  slack_metrics "*comedy recruit:* $applicant_count new applicant notification(s) in Gmail. Anicca が screening 待ち" >/dev/null || true
fi

# 3. Stripe Checkout webhook ticket purchases (Gmail 経由 Stripe receipt)
ticket_count=0
TICKETS=$(/opt/homebrew/bin/gog gmail search --query 'from:stripe.com subject:(receipt OR payment received) "comedy" newer_than:1d is:unread' --account "$GOG_ACCOUNT" --max 20 --json 2>/dev/null || echo '{"messages":[]}')
ticket_count=$(echo "$TICKETS" | jq '.messages | length' 2>/dev/null || echo 0)
if [ "$ticket_count" -gt 0 ]; then
  slack_metrics "*comedy ticket sales:* $ticket_count new purchase(s) detected. Phase 2 Stripe webhook で fulfillment" >/dev/null || true
fi

# 4. Dais sickness Slack DM keyword (last 24h)
# Note: requires SLACK_BOT_TOKEN with conversations.history scope on DM channel
sickness_flag="ok"
if [ -n "${SLACK_BOT_TOKEN:-}" ] && [ -n "${DAIS_SLACK_USER_ID:-}" ]; then
  oldest=$(($(date +%s) - 86400))
  resp=$(curl -sS -X POST "https://slack.com/api/conversations.history" \
    -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data "channel=${DAIS_SLACK_DM_CHANNEL:-${DAIS_SLACK_USER_ID}}&oldest=${oldest}&limit=50" 2>/dev/null || echo '{}')
  match=$(echo "$resp" | jq -r '.messages[]? | .text // ""' 2>/dev/null | grep -iE "体調|sick|cancel|不参加|キャンセル" | head -1)
  if [ -n "$match" ]; then
    sickness_flag="alert"
    slack_metrics "*🚨 comedy sickness detect:* Dais の Slack DM に keyword 検出 → comedy-recruit-on-sickness-event 発動 候補。手動確認してから lib 起動。matched: ${match:0:80}" >/dev/null || true
  fi
fi

echo "✅ watch-replies-6h: replies=${reply_count} applicants=${applicant_count} tickets=${ticket_count} sickness=${sickness_flag}"
