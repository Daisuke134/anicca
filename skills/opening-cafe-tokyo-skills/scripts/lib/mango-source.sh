#!/usr/bin/env bash
# lib/mango-source.sh — Mexican mango 仕入れ価格 scrape (kg 単価)。
#
# Sources scraped:
#   1. 豊洲市場 web / 豊洲場外 (search Mexican mango)
#   2. 楽天市場 (mexican mango wholesale)
#   3. 業務スーパー (mango bulk)
#   4. アメ横 / OK ストア (delivery options)
#
# Output: data/cafe/supplies/mango-quotes.json
#
# stdout final line:
#   ✅ mango-source: best=<vendor> per_kg=¥<price> n=<quote_count>
#   ❌ mango-source FAILED: <reason>

set -uo pipefail

SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills
SUPPLIES_DIR="$SKILL/data/cafe/supplies"
QUOTES_FILE="$SUPPLIES_DIR/mango-quotes.json"
mkdir -p "$SUPPLIES_DIR"

set -a; source "$HOME/.openclaw/.env"; set +a

PYTHON="python3"
AGENT_BROWSER="/opt/homebrew/bin/agent-{{profile.lateness.stakeholders.channel}}"

LOG_DIR="$SKILL/output/$(date +%Y-%m-%d)_mango-source"
mkdir -p "$LOG_DIR"

scrape() {
  local url="$1"; local out="$2"
  echo "  → $url" >&2
  "$AGENT_BROWSER" open "$url" >/dev/null 2>&1 || true
  sleep 3
  "$AGENT_BROWSER" snapshot text > "$out" 2>/dev/null || echo "" > "$out"
}

scrape "https://search.rakuten.co.jp/search/mall/%E3%83%A1%E3%82%AD%E3%82%B7%E3%82%B3%E7%94%A3+%E3%83%9E%E3%83%B3%E3%82%B4%E3%83%BC+%E6%A5%AD%E5%8B%99%E7%94%A8/" \
  "$LOG_DIR/rakuten.txt"

scrape "https://www.amazon.co.jp/s?k=%E3%83%A1%E3%82%AD%E3%82%B7%E3%82%B3%E7%94%A3+%E3%83%9E%E3%83%B3%E3%82%B4%E3%83%BC+%E5%8D%B8%E3%83%9C%E3%82%AD%E3%82%B9" \
  "$LOG_DIR/amazon.txt"

scrape "https://www.toyosu-market.or.jp/search/?q=%E3%83%9E%E3%83%B3%E3%82%B4%E3%83%BC" \
  "$LOG_DIR/toyosu.txt"

PROMPT_FILE="$LOG_DIR/prompt.txt"
cat > "$PROMPT_FILE" <<'PROMPT_EOF'
You are extracting wholesale price quotes for Mexican-origin mangoes (Tommy Atkins, Ataulfo, or generic Mexican mango), bulk lot or per-kg, from raw page text.

For each section below, extract the best candidate quote: lowest per-kg JPY price for fresh Mexican mango in business-quantity lots (kg or case basis). Convert "1 case (約Xkg) ¥Y" to per-kg = Y/X.

Return ONLY a JSON array (no markdown), each item:
  {"vendor":"<name>","product_title":"<short>","per_kg_jpy":<integer>,"min_lot_kg":<integer or null>,"url":"<url if visible>","captured_at":"<ISO8601 UTC>"}

If no usable quote found, emit one item:
  {"vendor":"<name>","per_kg_jpy":null,"note":"<short reason>","captured_at":"..."}

PROMPT_EOF

for vendor in rakuten amazon toyosu; do
  echo "" >> "$PROMPT_FILE"
  echo "=== $vendor ===" >> "$PROMPT_FILE"
  head -c 6000 "$LOG_DIR/$vendor.txt" >> "$PROMPT_FILE"
done

# === HARD RULE #6: LLM price-parse delegated to cron model ===
echo "⚠ price extraction LLM step skipped — cron model handles per SKILL.md" >&2
QUOTES_JSON="[]"
echo "[]" > "$LOG_DIR/raw.txt" 2>/dev/null || true

$PYTHON - "$LOG_DIR/raw.txt" "$QUOTES_FILE" <<'PY'
import sys, re, json, datetime, pathlib
txt = pathlib.Path(sys.argv[1]).read_text().strip()
m = re.search(r'\[.*\]', txt, re.S)
if m: txt = m.group(0)
try:
    arr = json.loads(txt)
except Exception:
    arr = []
valid = [q for q in arr if isinstance(q, dict) and q.get("per_kg_jpy") not in (None, 0)]
best = min(valid, key=lambda q: q.get("per_kg_jpy", 9999999)) if valid else None
out = {
    "captured_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "spec": "Mexican mango wholesale per-kg",
    "quotes": arr,
    "best": best,
}
pathlib.Path(sys.argv[2]).write_text(json.dumps(out, ensure_ascii=False, indent=2))
PY

BEST=$($PYTHON -c "import json; d=json.load(open('$QUOTES_FILE')); b=d.get('best'); print(f\"{b.get('vendor','?')} ¥{b.get('per_kg_jpy','?')}/kg\" if b else 'none')")
N=$($PYTHON -c "import json; d=json.load(open('$QUOTES_FILE')); print(len(d.get('quotes',[])))")

# Slack 報告 (5/9 v27 fix)
TS=$("$PYTHON" - "$SLACK_CHANNEL_ID" "$SLACK_BOT_TOKEN" "$BEST" "$N" "$QUOTES_FILE" <<'PY'
import sys, json, urllib.request
ch, token, best, n, qfile = sys.argv[1:6]
payload = {
    "channel": ch,
    "text": f"🥭 mango-source: best={best} n={n}",
    "blocks": [
        {"type":"header","text":{"type":"plain_text","text":"🥭 cafe-mango-source"}},
        {"type":"section","fields":[
            {"type":"mrkdwn","text":f"*best vendor:*\n`{best}`"},
            {"type":"mrkdwn","text":f"*total quotes:*\n{n}"},
            {"type":"mrkdwn","text":"*spec:*\nMexican mango wholesale per-kg"},
            {"type":"mrkdwn","text":"*source:*\n楽天/Amazon/豊洲"},
        ]},
        {"type":"context","elements":[{"type":"mrkdwn","text":f"data: `{qfile}`"}]},
    ]
}
req = urllib.request.Request(
    "https://slack.com/api/chat.postMessage",
    data=json.dumps(payload).encode(),
    headers={"Authorization":f"Bearer {token}","Content-Type":"application/json; charset=utf-8"},
    method="POST")
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        print(json.loads(r.read().decode()).get("ts","?"))
except Exception:
    print("?")
PY
)

echo "✅ mango-source: best=$BEST n=$N | slack ts=$TS"
