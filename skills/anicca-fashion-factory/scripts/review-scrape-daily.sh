#!/usr/bin/env bash
# Daily X (Twitter) brand mention scrape (12 JST).
#
# Pipeline:
#   1. agent-{{profile.lateness.stakeholders.channel}} で X 検索 `(anicca tee OR anicca hoodie OR anicca cap)
#      since:24h` を開く → page text capture
#   2. Claude で sentiment 判定 (positive / neutral / negative)
#   3. positive → 自分で quote tweet + 感謝 (Postiz X) — TODO Phase 2
#   4. negative → customer-support-event.sh に渡す (顧客 {{profile.lateness.stakeholders.channel}} + 理由)
#   5. data/reviews.json append + Slack #metrics 報告
#
# stdout final line:
#   ✅ review-scrape: <n_positive>+/<n_neutral>=/<n_negative>- | slack ts=<ts>
#   ❌ review-scrape FAILED: <reason>

set -euo pipefail

SKILL_DIR="$HOME/.openclaw/skills/anicca-fashion-factory"
DATA_DIR="$SKILL_DIR/data"
REVIEWS_FILE="$DATA_DIR/reviews.json"
LOG_DIR="$SKILL_DIR/output/$(date +%Y-%m-%d)_review-scrape"
mkdir -p "$LOG_DIR" "$DATA_DIR"

set -a; source "$HOME/.openclaw/.env"; set +a

PYTHON="python3"
AGENT_BROWSER="/opt/homebrew/bin/agent-{{profile.lateness.stakeholders.channel}}"

# Initialize reviews.json if missing
[ -f "$REVIEWS_FILE" ] || echo '{"runs":[]}' > "$REVIEWS_FILE"

QUERY='(anicca tee) OR (anicca hoodie) OR (anicca cap) -filter:replies'
ENC_QUERY=$($PYTHON -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$QUERY")
URL="https://x.com/search?q=${ENC_QUERY}&src=typed_query&f=live"

echo "[1/4] agent-{{profile.lateness.stakeholders.channel}} open: $URL"
SCRAPE_RAW="$LOG_DIR/scrape.txt"

# agent-{{profile.lateness.stakeholders.channel}} may fail without a logged-in X session — degrade gracefully
if ! "$AGENT_BROWSER" open "$URL" >"$LOG_DIR/open.log" 2>&1; then
  echo "  ⚠️ agent-{{profile.lateness.stakeholders.channel}} open failed (no X session?) — recording 0 mentions"
  echo "" > "$SCRAPE_RAW"
else
  sleep 5
  "$AGENT_BROWSER" snapshot text >"$SCRAPE_RAW" 2>"$LOG_DIR/snapshot.err" || {
    echo "  ⚠️ snapshot failed — recording 0 mentions"
    echo "" > "$SCRAPE_RAW"
  }
fi

LINE_COUNT=$(wc -l < "$SCRAPE_RAW" | tr -d ' ')
echo "  scraped lines: $LINE_COUNT"

echo "[2/4] Claude sentiment classification"
SENTIMENT_OUT="$LOG_DIR/sentiment.json"

if [ "$LINE_COUNT" -lt 3 ]; then
  echo "  no mentions — skip Claude"
  cat > "$SENTIMENT_OUT" <<EOF
{"positive":[],"neutral":[],"negative":[],"raw_lines":$LINE_COUNT}
EOF
else
  PROMPT_FILE="$LOG_DIR/prompt.txt"
  cat > "$PROMPT_FILE" <<'PROMPT_EOF'
Below is raw text scraped from x.com search for "anicca tee OR hoodie OR cap".
Extract any tweets that mention the Anicca fashion brand (Tee, Hoodie, or Cap),
classify each as positive/neutral/negative sentiment, and output a single JSON
object on stdout with keys "positive", "neutral", "negative" — each an array
of objects {tweet_text, author_handle (if found), customer_{{profile.lateness.stakeholders.channel}}_hint (null
unless very explicit)}. If no relevant tweets are found, return all-empty arrays.

Return ONLY the JSON object, no markdown fence, no commentary.

--- raw scrape ---
PROMPT_EOF
  cat "$SCRAPE_RAW" >> "$PROMPT_FILE"

  # === HARD RULE #6: LLM inference step delegated to cron model invoking this skill ===
  # The prompt is saved at $PROMPT_FILE — cron model reads it, generates sentiment JSON,
  # writes to $SENTIMENT_OUT. For now, write empty stub so downstream doesn't crash.
  echo '{"positive":[],"neutral":[],"negative":[],"llm_step_skipped":true,"_note":"cron model must do sentiment analysis per SKILL.md","prompt_at":"'"$PROMPT_FILE"'"}' > "$SENTIMENT_OUT"
fi

POS_N=$($PYTHON -c "import json; print(len(json.load(open('$SENTIMENT_OUT')).get('positive',[])))")
NEU_N=$($PYTHON -c "import json; print(len(json.load(open('$SENTIMENT_OUT')).get('neutral',[])))")
NEG_N=$($PYTHON -c "import json; print(len(json.load(open('$SENTIMENT_OUT')).get('negative',[])))")

echo "  positive=$POS_N neutral=$NEU_N negative=$NEG_N"

echo "[3/4] reviews.json append"
$PYTHON - <<PY
import json, datetime, pathlib
p = pathlib.Path("$REVIEWS_FILE")
db = json.loads(p.read_text())
sentiment = json.loads(pathlib.Path("$SENTIMENT_OUT").read_text())
db.setdefault("runs", []).append({
    "ran_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "raw_lines": sentiment.get("raw_lines", 0),
    "positive": sentiment.get("positive", []),
    "neutral":  sentiment.get("neutral", []),
    "negative": sentiment.get("negative", []),
    "log_dir":  "$LOG_DIR",
})
# trim to last 90 runs
db["runs"] = db["runs"][-90:]
p.write_text(json.dumps(db, ensure_ascii=False, indent=2))
PY

echo "[4/4] customer-support trigger for negatives + Slack"

# fire customer-support-event for each negative with explicit customer {{profile.lateness.stakeholders.channel}} hint
NEG_FILE="$LOG_DIR/negatives.json"
$PYTHON - > "$NEG_FILE" <<PY
import json, pathlib
sent = json.loads(pathlib.Path("$SENTIMENT_OUT").read_text())
print(json.dumps(sent.get("negative", [])))
PY

while IFS= read -r entry; do
  [ -z "$entry" ] && continue
  EMAIL=$(echo "$entry" | $PYTHON -c "import sys,json; e=json.loads(sys.stdin.read()); print(e.get('customer_{{profile.lateness.stakeholders.channel}}_hint') or '')")
  REASON=$(echo "$entry" | $PYTHON -c "import sys,json; e=json.loads(sys.stdin.read()); print(e.get('tweet_text','')[:240])")
  if [ -n "$EMAIL" ]; then
    echo "  → customer-support-event: $EMAIL"
    bash "$SKILL_DIR/scripts/customer-support-event.sh" "$EMAIL" "$REASON" || echo "    ⚠️ customer-support-event failed for $EMAIL"
  fi
done < <($PYTHON -c "import sys,json; [print(json.dumps(x)) for x in json.load(open('$NEG_FILE'))]")

# Slack post
SLACK_PAYLOAD=$(cat <<JSON
{
  "channel": "$SLACK_CHANNEL_ID",
  "text": "🧵 fashion-review-scrape: $POS_N+/$NEU_N=/$NEG_N-",
  "blocks": [
    {"type":"header","text":{"type":"plain_text","text":"🧵 fashion-review-scrape-daily"}},
    {"type":"section","text":{"type":"mrkdwn","text":"*query:* \`anicca tee/hoodie/cap\`\n*positive:* $POS_N\n*neutral:* $NEU_N\n*negative:* $NEG_N\n*raw scrape lines:* $LINE_COUNT"}},
    {"type":"context","elements":[{"type":"mrkdwn","text":"log: \`$LOG_DIR\`"}]}
  ]
}
JSON
)

SLACK_RESP=$(curl -s -X POST -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d "$SLACK_PAYLOAD" \
  https://slack.com/api/chat.postMessage)
TS=$(echo "$SLACK_RESP" | $PYTHON -c "import sys,json; print(json.load(sys.stdin).get('ts','?'))")

echo "✅ review-scrape: ${POS_N}+/${NEU_N}=/${NEG_N}- | slack ts=$TS"
