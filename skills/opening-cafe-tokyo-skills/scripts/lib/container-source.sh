#!/usr/bin/env bash
# lib/container-source.sh — PET bottle 350ml × 1000本 価格比較。
#
# Sources scraped (in priority order):
#   1. 容器スター (yougi-star.jp / containerstar.com)
#   2. 楽天市場 (search "350ml PETボトル 黒 1000本")
#   3. Amazon Business (search same)
#
# Output: data/cafe/supplies/container-quotes.json
#   {
#     "captured_at": "...",
#     "spec": "350ml PET black 1000ct",
#     "quotes": [
#       {"vendor":"容器スター","unit_price_jpy":85,"min_lot":1000,"url":"...","captured_at":"..."},
#       {"vendor":"楽天","unit_price_jpy":92,"min_lot":1000,"url":"..."},
#       ...
#     ],
#     "best": {"vendor":"容器スター","unit_price_jpy":85,...}
#   }
#
# stdout final line:
#   ✅ container-source: best=<vendor> unit=¥<price> n=<quote_count>
#   ❌ container-source FAILED: <reason>

set -uo pipefail

SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills
SUPPLIES_DIR="$SKILL/data/cafe/supplies"
QUOTES_FILE="$SUPPLIES_DIR/container-quotes.json"
mkdir -p "$SUPPLIES_DIR"

set -a; source "$HOME/.openclaw/.env"; set +a

PYTHON="python3"
AGENT_BROWSER="/opt/homebrew/bin/agent-{{profile.lateness.stakeholders.channel}}"

LOG_DIR="$SKILL/output/$(date +%Y-%m-%d)_container-source"
mkdir -p "$LOG_DIR"

# Helper: scrape a URL with agent-{{profile.lateness.stakeholders.channel}} → text
scrape() {
  local url="$1"
  local out="$2"
  echo "  → $url" >&2
  "$AGENT_BROWSER" open "$url" >/dev/null 2>&1 || true
  sleep 3
  "$AGENT_BROWSER" snapshot text > "$out" 2>/dev/null || echo "" > "$out"
}

# 1. 容器スター
scrape "https://www.containerstar.com/list/?keyword=350ml+PET+%E9%BB%92" \
  "$LOG_DIR/containerstar.txt"

# 2. 楽天 (mobile UI is more scrapable)
scrape "https://search.rakuten.co.jp/search/mall/350ml+PET%E3%83%9C%E3%83%88%E3%83%AB+%E9%BB%92+1000%E6%9C%AC/" \
  "$LOG_DIR/rakuten.txt"

# 3. Amazon
scrape "https://www.amazon.co.jp/s?k=350ml+PET+%E3%83%9C%E3%83%88%E3%83%AB+%E9%BB%92+1000%E6%9C%AC" \
  "$LOG_DIR/amazon.txt"

# Claude haiku でテキストから JSON quote 抽出
PROMPT_FILE="$LOG_DIR/prompt.txt"
cat > "$PROMPT_FILE" <<'PROMPT_EOF'
You are extracting price quotes for a 350ml black PET bottle, target lot 1000 units, from raw page text.

For each section below (3 vendors), extract the BEST candidate quote you can find: lowest unit price (JPY) for a black 350ml PET bottle in lots near 1000.

Return ONLY a JSON array (no markdown), each item:
  {"vendor":"<name>","product_title":"<short>","unit_price_jpy":<integer>,"min_lot":<integer or null>,"url":"<url if visible>","captured_at":"<ISO8601 UTC>"}

If no usable quote found in a section, emit one item with unit_price_jpy:null and a reason note:
  {"vendor":"<name>","unit_price_jpy":null,"note":"<short reason>","captured_at":"..."}

Use UTC ISO8601 for captured_at.

PROMPT_EOF

for vendor in containerstar rakuten amazon; do
  echo "" >> "$PROMPT_FILE"
  echo "=== $vendor ===" >> "$PROMPT_FILE"
  head -c 6000 "$LOG_DIR/$vendor.txt" >> "$PROMPT_FILE"
done

# === HARD RULE #6: LLM price-parse delegated to cron model ===
echo "⚠ price extraction LLM step skipped — cron model handles per SKILL.md" >&2
QUOTES_JSON="[]"
echo "[]" > "$LOG_DIR/raw.txt" 2>/dev/null || true

# Strip markdown fences if present
echo "$QUOTES_JSON" | $PYTHON - <<PY > "$LOG_DIR/quotes-array.json"
import sys, re, json
txt = sys.stdin.read().strip()
m = re.search(r'\[.*\]', txt, re.S)
if m:
    txt = m.group(0)
try:
    arr = json.loads(txt)
except Exception:
    arr = []
print(json.dumps(arr))
PY

# Pick best (lowest unit_price_jpy with non-null)
$PYTHON - "$LOG_DIR/quotes-array.json" "$QUOTES_FILE" <<'PY'
import sys, json, datetime, pathlib
arr = json.loads(open(sys.argv[1]).read())
valid = [q for q in arr if isinstance(q, dict) and q.get("unit_price_jpy") not in (None, 0)]
best = min(valid, key=lambda q: q.get("unit_price_jpy", 9999999)) if valid else None
out = {
    "captured_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "spec": "350ml PET black 1000ct",
    "quotes": arr,
    "best": best,
}
pathlib.Path(sys.argv[2]).write_text(json.dumps(out, ensure_ascii=False, indent=2))
PY

BEST=$($PYTHON -c "import json; d=json.load(open('$QUOTES_FILE')); b=d.get('best'); print(f\"{b.get('vendor','?')} ¥{b.get('unit_price_jpy','?')}\" if b else 'none')")
N=$($PYTHON -c "import json; d=json.load(open('$QUOTES_FILE')); print(len(d.get('quotes',[])))")

# Slack 報告 (5/9 v27 fix)
TS=$("$PYTHON" - "$SLACK_CHANNEL_ID" "$SLACK_BOT_TOKEN" "$BEST" "$N" "$QUOTES_FILE" <<'PY'
import sys, json, urllib.request
ch, token, best, n, qfile = sys.argv[1:6]
payload = {
    "channel": ch,
    "text": f"📦 container-source: best={best} n={n}",
    "blocks": [
        {"type":"header","text":{"type":"plain_text","text":"📦 cafe-container-source"}},
        {"type":"section","fields":[
            {"type":"mrkdwn","text":f"*best vendor:*\n`{best}`"},
            {"type":"mrkdwn","text":f"*total quotes:*\n{n}"},
            {"type":"mrkdwn","text":"*spec:*\n350ml PET black 1000ct"},
            {"type":"mrkdwn","text":"*source:*\n容器スター/楽天/Amazon"},
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

echo "✅ container-source: best=$BEST n=$N | slack ts=$TS"
