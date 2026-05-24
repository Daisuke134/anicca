#!/usr/bin/env bash
# Daily SEO rank monitor via Brave Search API
set -uo pipefail

ROOT="$HOME/.openclaw/skills/anicca-seo-rank-monitor"
DATE=$(date +%Y-%m-%d)
OUT="$ROOT/state/ranks-$DATE.json"
mkdir -p "$ROOT/state"

set -a; . "$HOME/.openclaw/.env"; set +a 2>/dev/null

[ -z "${BRAVE_API_KEY:-}" ] && { echo "❌ BRAVE_API_KEY not set" >&2; exit 1; }

# write keyword list to tmp file (avoid shell array → python embedding issues)
TMP_KW=$(mktemp /tmp/anicca-seo-rank-kw.XXXXXX)
cat > "$TMP_KW" <<'KWEOF'
anicca
anicca ai
anicca app
{{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}
{{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}} アプリ
仏教 AI アプリ
behavior change app
proactive mindfulness app
anxiety relief app
mindfulness companion app
digital companion app
Calm alternative
Headspace alternative
行動変容 アプリ
マインドフルネス アプリ
不安 アプリ おすすめ
瞑想 アプリ おすすめ
Calm 代替アプリ
習慣化 アプリ
affirmation app
daily affirmations app
iam affirmation
アファメーション アプリ
毎日 アファメーション
anicca cafe
AI cafe Tokyo
AI run cafe
AI が運営する カフェ
東京 AI カフェ
ai grave
AI cemetery
digital cemetery
AI 墓
デジタル 墓
永代供養 AI
anicca fashion
impermanence fashion brand
無常 ファッション
{{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}} ファッション
anicca retreat
mindfulness retreat Tokyo
東京 瞑想 リトリート
リトリート 東京
anicca mantra
mantra meditation app
マントラ アプリ
autonomous AI organization
safe autonomous organization
AI that funds itself
AI agent business
agent economy
self-funding AI
BOND AI
Andon Labs
自律 AI エージェント
AI 自律 運営 会社
build in public AI
AI startup build in public
インディー AI 開発
デジタル ブッダ
KWEOF

# Domains to match (any substring in result URL)
TMP_DOM=$(mktemp /tmp/anicca-seo-rank-dom.XXXXXX)
cat > "$TMP_DOM" <<'DOMEOF'
aniccaai.com
daily-affirmations-anicca
com.appanicca
DOMEOF

# Pre-fetch all Brave results
RESULTS_DIR=$(mktemp -d /tmp/anicca-seo-rank.XXXXXX)
while IFS= read -r kw; do
  [ -z "$kw" ] && continue
  KW_ENC=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$kw")
  SAFE=$(echo "$kw" | tr ' /' '__')
  curl -sS "https://api.search.brave.com/res/v1/web/search?q=${KW_ENC}&count=20" \
    -H "X-Subscription-Token: $BRAVE_API_KEY" -o "$RESULTS_DIR/$SAFE.json" 2>/dev/null
  sleep 0.6
done < "$TMP_KW"

# Compute ranks via pure python
python3 - <<PYEOF > "$OUT"
import json, os, sys, datetime
results_dir = "$RESULTS_DIR"
kw_file = "$TMP_KW"
dom_file = "$TMP_DOM"

with open(dom_file) as f:
    domains = [d.strip().lower() for d in f if d.strip()]

snapshot = []
with open(kw_file) as f:
    for kw in (line.strip() for line in f):
        if not kw: continue
        safe = kw.replace(' ', '_').replace('/', '_')
        path = os.path.join(results_dir, f"{safe}.json")
        rank = None
        try:
            with open(path) as rf:
                d = json.load(rf)
            for i, r in enumerate(d.get('web', {}).get('results', [])[:20], 1):
                url = r.get('url', '').lower()
                if any(dom in url for dom in domains):
                    rank = i
                    break
        except Exception as e:
            pass
        snapshot.append({
            'keyword': kw,
            'rank': rank,
            'date': datetime.datetime.utcnow().isoformat() + 'Z'
        })
print(json.dumps(snapshot, indent=2))
PYEOF

# Cleanup tmp
rm -rf "$RESULTS_DIR" "$TMP_KW" "$TMP_DOM"

# Delta vs yesterday
YEST="$ROOT/state/ranks-$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d 'yesterday' +%Y-%m-%d 2>/dev/null).json"
DELTA=""
if [ -f "$YEST" ]; then
  DELTA=$(python3 -c "
import json
today = json.load(open('$OUT'))
yest = json.load(open('$YEST'))
y_map = {r['keyword']: r['rank'] for r in yest}
gains = losses = 0
for r in today:
    t, y = r['rank'], y_map.get(r['keyword'])
    if t is None and y is None: continue
    if y is None and t is not None: gains += 1
    elif t is None and y is not None: losses += 1
    elif t < y: gains += 1
    elif t > y: losses += 1
print(f'+{gains}/-{losses}')
" 2>/dev/null || echo "")
fi

# Build summary
SUMMARY=$(python3 -c "
import json
d = json.load(open('$OUT'))
parts = [f\"{r['keyword']}={r['rank']}\" for r in d]
print(', '.join(parts))
")

KW_COUNT=$(python3 -c "import json; print(len(json.load(open('$OUT'))))")
echo "📊 SEO rank snapshot $DATE | aniccaai tracked: $KW_COUNT kw | $SUMMARY${DELTA:+ | $DELTA}"
