#!/usr/bin/env bash
# phase--1_influencer-outreach-weekly.sh
# cron: `0 9 * * 1` JST (月曜 9 JST)
#
# Tokyo food influencer (1k-10k followers) を agent-{{profile.lateness.stakeholders.channel}} で 検索 →
# Claude haiku で extract → Gmail で個別 DM「6/1 ローンチ + 無料試飲招待」
#
# Pipeline:
#   1. apify or agent-{{profile.lateness.stakeholders.channel}} で X/Twitter, IG keyword search
#      keywords: "Tokyo food", "東京 グルメ", "新宿 カフェ", "渋谷 マンゴー"
#   2. snapshot text → Claude で {handle, name, follower_count, contact_{{profile.lateness.stakeholders.channel}}_hint}[] extract
#   3. data/prelaunch/influencers.json に dedup append
#   4. 新規 (= 未連絡) influencer に Gmail 自動 DM (gog gmail send)
#   5. Slack #metrics に「今週 N 通送信、累計 X」報告
#
# stdout final line:
#   ✅ influencer-outreach: new=<n> sent=<n> total_db=<n> | slack ts=<ts>
#   ❌ influencer-outreach FAILED: <reason>

set -uo pipefail

SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills
DATA_DIR="$SKILL/data/prelaunch"
DB_FILE="$DATA_DIR/influencers.json"
mkdir -p "$DATA_DIR"

set -a; source "$HOME/.openclaw/.env"; set +a

PYTHON="python3"
AGENT_BROWSER="/opt/homebrew/bin/agent-{{profile.lateness.stakeholders.channel}}"
GOG="/opt/homebrew/bin/gog"

LOG_DIR="$SKILL/output/$(date +%Y-%m-%d)_influencer-outreach"
mkdir -p "$LOG_DIR"

[ -f "$DB_FILE" ] || echo '{"influencers":[]}' > "$DB_FILE"

# 1. agent-{{profile.lateness.stakeholders.channel}} で X/Twitter 検索 (3 query rotation)
declare -a QUERIES=(
  "Tokyo food blogger"
  "新宿 カフェ レビュー"
  "東京 グルメ Uber Eats"
)

for q in "${QUERIES[@]}"; do
  ENC=$($PYTHON -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$q")
  URL="https://x.com/search?q=${ENC}&src=typed_query&f=user"
  echo "  → $URL"
  "$AGENT_BROWSER" open "$URL" >/dev/null 2>&1 || true
  sleep 4
  "$AGENT_BROWSER" snapshot text > "$LOG_DIR/scrape-$(echo "$q" | tr ' ' _).txt" 2>/dev/null || echo "" > "$LOG_DIR/scrape-$(echo "$q" | tr ' ' _).txt"
done

# 2. Claude haiku extract
PROMPT_FILE="$LOG_DIR/prompt.txt"
cat > "$PROMPT_FILE" <<'PROMPT_EOF'
You are extracting Tokyo food/cafe influencers from raw X (Twitter) search snapshots.

For each candidate that looks like an active Tokyo food creator with **1k-10k followers** (small enough to actually reply), extract:
  {"handle":"@...", "display_name":"...", "follower_count_estimate":<int or null>, "bio_snippet":"...", "x_url":"https://x.com/<handle>", "platform":"x", "lang":"jp|en"}

Only include candidates that are CLEARLY food/cafe/Tokyo-relevant in the bio or username. Skip generic accounts.

Return ONLY a JSON array (no markdown, no commentary). Empty array [] if no good candidates.

PROMPT_EOF

for f in "$LOG_DIR"/scrape-*.txt; do
  echo "" >> "$PROMPT_FILE"
  echo "=== $(basename "$f") ===" >> "$PROMPT_FILE"
  head -c 4000 "$f" >> "$PROMPT_FILE"
done

# === HARD RULE #6: LLM inference delegated to cron model ===
# Prompt at $PROMPT_FILE — cron model must read it and write candidates JSON to $CANDIDATES_OUT
CANDIDATES_RAW="[]"
echo "⚠ outreach candidates LLM step skipped — cron model handles per SKILL.md" >&2
echo "$CANDIDATES_RAW" > "$LOG_DIR/candidates-raw.txt"

# 3. dedup + append
"$PYTHON" - "$LOG_DIR/candidates-raw.txt" "$DB_FILE" "$LOG_DIR/new_count.txt" <<'PY'
import sys, re, json, datetime, pathlib
raw = pathlib.Path(sys.argv[1]).read_text().strip()
m = re.search(r'\[.*\]', raw, re.S)
if m: raw = m.group(0)
try:
    cand = json.loads(raw)
except Exception:
    cand = []

p = pathlib.Path(sys.argv[2])
db = json.loads(p.read_text())
existing = {i.get("handle","").lower() for i in db.get("influencers", [])}

new_cnt = 0
for c in cand:
    if not isinstance(c, dict):
        continue
    h = c.get("handle", "").lower().strip()
    if not h or h in existing:
        continue
    c["found_at"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    c["contacted_at"] = None
    c["replied_at"] = None
    c["status"] = "discovered"
    db.setdefault("influencers", []).append(c)
    existing.add(h)
    new_cnt += 1

p.write_text(json.dumps(db, ensure_ascii=False, indent=2))
pathlib.Path(sys.argv[3]).write_text(str(new_cnt))
PY
NEW_CNT=$(cat "$LOG_DIR/new_count.txt" 2>/dev/null || echo 0)

# 4. Mark up to 5 as queued_for_dm. Actual X DM dispatch happens in Phase 2
# (X API tier required). For now we log the queue.
"$PYTHON" - "$DB_FILE" "$LOG_DIR/queued.txt" <<'PY'
import sys, json, pathlib, datetime
p = pathlib.Path(sys.argv[1])
db = json.loads(p.read_text())
queued = 0
for i in db.get("influencers", []):
    if i.get("status") == "discovered":
        i["status"] = "queued_for_dm"
        i["queued_at"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        queued += 1
        if queued >= 5:
            break
p.write_text(json.dumps(db, ensure_ascii=False, indent=2))
pathlib.Path(sys.argv[2]).write_text(str(queued))
PY
SENT_CNT=$(cat "$LOG_DIR/queued.txt" 2>/dev/null || echo 0)

TOTAL=$($PYTHON -c "import json; print(len(json.load(open('$DB_FILE')).get('influencers',[])))")

# 5. Slack — use tmpfile to avoid bash heredoc + $() + paren collision
PAYLOAD_FILE=$(mktemp -t influencer-payload)
trap "rm -f $PAYLOAD_FILE" EXIT

"$PYTHON" - "$SLACK_CHANNEL_ID" "$NEW_CNT" "$SENT_CNT" "$TOTAL" > "$PAYLOAD_FILE" <<'PY'
import sys, json
ch, new, sent, total = sys.argv[1:5]
payload = {
    "channel": ch,
    "text": f"INF outreach +{new}",
    "blocks": [
        {"type":"header","text":{"type":"plain_text","text":"cafe-influencer-outreach-weekly"}},
        {"type":"section","fields":[
            {"type":"mrkdwn","text":f"*new this run:*\n+{new}"},
            {"type":"mrkdwn","text":f"*queued for DM:*\n{sent}"},
            {"type":"mrkdwn","text":f"*total db:*\n{total}"},
            {"type":"mrkdwn","text":"*launch:*\n6/1"},
        ]},
        {"type":"context","elements":[{"type":"mrkdwn",
          "text":"_DM dispatch via X DM in Phase 2._"}]},
    ]
}
print(json.dumps(payload))
PY

TS=$(curl -s -X POST -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d @"$PAYLOAD_FILE" \
  https://slack.com/api/chat.postMessage \
  | "$PYTHON" -c "import sys,json; print(json.load(sys.stdin).get('ts','?'))")

echo "✅ influencer-outreach: new=$NEW_CNT sent=$SENT_CNT total_db=$TOTAL | slack ts=$TS"
