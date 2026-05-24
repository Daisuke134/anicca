#!/usr/bin/env bash
# lib/delegate-to-humans.sh — クラウドワークス / ココナラ に有償タスク投稿。
#
# Skill ができないことを ¥報酬 で 人間に依頼する mechanism。
# 例:
#   - 5/12 内見訪問代理 (¥3k for friend)
#   - PET ボトル 大量発注代行 (¥500)
#   - ステッカー印刷 (¥1k)
#
# Note: Vitamix は Dais 自宅にあるため delegation 不要 (5/8 確定)。
#
# Usage:
#   bash lib/delegate-to-humans.sh <task_slug> <reward_jpy> <description_file>
#
# Pipeline:
#   1. クラウドワークス API or {{profile.lateness.stakeholders.channel}}-harness で 募集投稿
#   2. data/cafe/delegations/<slug>.json に履歴
#   3. Slack #metrics に投稿 URL + 期日 通知
#   4. 応募 reply を Gmail / Slack 監視 (poll or webhook)
#   5. 最初の応募者選定 → 報酬 Stripe 送金 → タスク完了確認 → 次に進む
#
# stdout final line:
#   ✅ delegate <slug>: posted | reward=¥<n> | url=<crowdworks_url>
#   ❌ delegate FAILED: <reason>

set -uo pipefail

TASK_SLUG="${1:?usage: delegate-to-humans.sh <task_slug> <reward_jpy> <description_file>}"
REWARD="${2:?missing reward_jpy}"
DESC_FILE="${3:?missing description_file}"

SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills
DATA_DIR="$SKILL/data/cafe/delegations"
mkdir -p "$DATA_DIR"
STATE_FILE="$DATA_DIR/$TASK_SLUG.json"

set -a; source "$HOME/.openclaw/.env"; set +a

PYTHON="python3"

if [ -f "$STATE_FILE" ]; then
  STATUS=$($PYTHON -c "import json; print(json.load(open('$STATE_FILE')).get('status','?'))")
  if [ "$STATUS" = "posted" ] || [ "$STATUS" = "completed" ]; then
    echo "▶ already $STATUS: $TASK_SLUG"
    echo "✅ delegate $TASK_SLUG: skipped (already $STATUS)"
    exit 0
  fi
fi

if [ ! -f "$DESC_FILE" ]; then
  echo "❌ delegate FAILED: description file not found: $DESC_FILE"
  exit 1
fi

DESC=$(cat "$DESC_FILE")

# Phase 1 (current): Slack 投稿 → Dais 個人ネットワーク募集
# Phase 2 (future): クラウドワークス / ココナラ API or {{profile.lateness.stakeholders.channel}}-harness 自動投稿
SLACK_PAYLOAD=$($PYTHON - "$SLACK_CHANNEL_ID" "$TASK_SLUG" "$REWARD" "$DESC" <<'PY'
import sys, json
ch, slug, reward, desc = sys.argv[1:5]
payload = {
    "channel": ch,
    "text": f"🪙 delegation: {slug} (¥{reward})",
    "blocks": [
        {"type":"header","text":{"type":"plain_text","text":f"🪙 delegation request: {slug}"}},
        {"type":"section","text":{"type":"mrkdwn",
          "text":f"*reward:* ¥{reward}\n*deadline:* see description\n*post target:* クラウドワークス + ココナラ + Slack network"}},
        {"type":"section","text":{"type":"mrkdwn","text":f"*description:*\n>>> {desc[:1500]}"}},
    ]
}
print(json.dumps(payload))
PY
)

TS=$(curl -s -X POST -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d "$SLACK_PAYLOAD" \
  https://slack.com/api/chat.postMessage \
  | $PYTHON -c "import sys,json; print(json.load(sys.stdin).get('ts','?'))")

# Persist state
$PYTHON - "$STATE_FILE" "$TASK_SLUG" "$REWARD" "$TS" "$DESC_FILE" <<'PY'
import sys, json, datetime, pathlib
p = pathlib.Path(sys.argv[1])
db = {
    "task_slug":  sys.argv[2],
    "reward_jpy": int(sys.argv[3]),
    "posted_at":  datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "slack_ts":   sys.argv[4],
    "description_file": sys.argv[5],
    "status":     "posted",
    "channels":   ["slack:network"],
    "applicants": [],
    "selected":   None,
    "completed_at": None,
}
p.write_text(json.dumps(db, ensure_ascii=False, indent=2))
PY

echo "✅ delegate $TASK_SLUG: posted | reward=¥$REWARD | slack ts=$TS"
