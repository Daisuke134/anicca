# US-010: Build Report (Token Usage + Slack + X Post)

依存: US-009（App Store提出完了）

## Step 1: Token Usage 集計

logs/iteration-*.log の全ファイルから usage を集計する。

```python
import json, glob

total_tokens = 0
total_duration_ms = 0
iteration_count = 0

for f in sorted(glob.glob('logs/iteration-*.log')):
    with open(f) as fh:
        for line in fh:
            try:
                d = json.loads(line.strip())
                if d.get('type') == 'result':
                    u = d.get('usage', {})
                    tokens = (u.get('input_tokens', 0) +
                              u.get('cache_creation_input_tokens', 0) +
                              u.get('cache_read_input_tokens', 0) +
                              u.get('output_tokens', 0))
                    total_tokens += tokens
                    total_duration_ms += d.get('duration_ms', 0)
                    iteration_count += 1
            except:
                pass

# Model-specific pricing (per million tokens)
# Source: https://docs.anthropic.com/en/docs/about-claude/models
# Sonnet: input=$3, output=$15, cache_create=$3.75, cache_read=$0.30
# Opus:   input=$15, output=$75, cache_create=$18.75, cache_read=$1.50
if 'opus' in model_name.lower():
    cost_usd = input_tokens*15/1e6 + output_tokens*75/1e6 + cache_create*18.75/1e6 + cache_read*1.50/1e6
else:  # sonnet (default)
    cost_usd = input_tokens*3/1e6 + output_tokens*15/1e6 + cache_create*3.75/1e6 + cache_read*0.30/1e6

# Budget: Max $200/month plan
WINDOW_BUDGET = 200 / 30 / 4.8  # $1.39 per 5h window
WEEKLY_BUDGET = 200 / 4.3        # $46.51 per week
window_pct = (cost_usd / WINDOW_BUDGET) * 100
weekly_pct = (cost_usd / WEEKLY_BUDGET) * 100
duration_min = total_duration_ms / 60000
```

## Step 2: アプリ情報取得

prd.json から以下を読む:
- `appName` — アプリ名（例: FrostDip）
- `description` — 1行説明（例: Cold plunge timer & breathing guide）

これらは毎アプリ異なる。ハードコードしない。

## Step 3: build-report.json 保存

アプリディレクトリ直下に保存する。

```json
{
  "appName": "<prd.jsonから>",
  "description": "<prd.jsonから>",
  "totalTokens": 50000000,
  "costInPlan": 4.46,
  "iterationCount": 18,
  "durationMinutes": 130,
  "weeklyUsagePercent": 8.9,
  "windowUsagePercent": 55.6,
  "buildDate": "2026-03-08"
}
```

## Step 4: スクショ取得

US-008a で ASC にアップロードした製品ページスクショを使う。

パス: `screenshots/raw-65/en-US/*.png`（CWD = アプリディレクトリ）

最大4枚。ファイルが5枚以上あれば先頭4枚。

## Step 5: Slack 投稿

```bash
source ~/.config/mobileapp-builder/.env

REPORT="build-report.json"
APP_NAME=$(python3 -c "import json; print(json.load(open('$REPORT'))['appName'])")
DESC=$(python3 -c "import json; print(json.load(open('$REPORT'))['description'])")
COST=$(python3 -c "import json; print(f\"{json.load(open('$REPORT'))['costInPlan']:.2f}\")")
ITERS=$(python3 -c "import json; print(json.load(open('$REPORT'))['iterationCount'])")
DURATION=$(python3 -c "import json; print(f\"{json.load(open('$REPORT'))['durationMinutes']:.0f}\")")
TOKENS=$(python3 -c "import json; d=json.load(open('$REPORT')); print(f\"{d['totalTokens']/1_000_000:.0f}M\")")
W5=$(python3 -c "import json; print(f\"{json.load(open('$REPORT'))['windowUsagePercent']:.0f}\")")
WK=$(python3 -c "import json; print(f\"{json.load(open('$REPORT'))['weeklyUsagePercent']:.1f}\")")

TEXT="🏭 ${APP_NAME} → App Store\n\n📱 ${DESC}\n💰 \$${COST} / \$200 plan\n⏱️ ${ITERS} iterations | ${DURATION}min\n📊 ${TOKENS} tokens | 5h: ${W5}% | weekly: ${WK}%\n\n#BuildInPublic"

curl -s -X POST "$SLACK_WEBHOOK_AGENTS" \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"$TEXT\"}"
```

## Step 6: X 投稿（@aniccaxxx のみ、英語、Postiz API）

POSTIZ_API_KEY 未設定時は X 投稿をスキップし、Slack で報告する。

```bash
source ~/.config/mobileapp-builder/.env

if [ -z "$POSTIZ_API_KEY" ] || [ -z "$POSTIZ_X_INTEGRATION_ID" ]; then
  echo "⚠️ POSTIZ_API_KEY or POSTIZ_X_INTEGRATION_ID not set, skipping X post"
  curl -s -X POST "$SLACK_WEBHOOK_AGENTS" \
    -H "Content-Type: application/json" \
    -d '{"text":"⚠️ US-010: POSTIZ_API_KEY 未設定のため X 投稿スキップ"}'
  exit 0
fi

# Step 6a: スクショを Postiz upload API でアップロード（最大4枚）
SCREENSHOTS=$(ls screenshots/raw-65/en-US/*.png 2>/dev/null | head -4)
IMAGE_JSON="[]"

if [ -n "$SCREENSHOTS" ]; then
  IMAGE_ITEMS=""
  for IMG in $SCREENSHOTS; do
    UPLOAD=$(curl -s -X POST "https://api.postiz.com/public/v1/upload" \
      -H "Authorization: $POSTIZ_API_KEY" \
      -F "file=@$IMG")
    IMG_ID=$(echo "$UPLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
    IMG_PATH=$(echo "$UPLOAD" | python3 -c "import json,sys; print(json.load(sys.stdin)['path'])")
    IMAGE_ITEMS="${IMAGE_ITEMS}{\"id\":\"$IMG_ID\",\"path\":\"$IMG_PATH\"},"
  done
  IMAGE_JSON="[${IMAGE_ITEMS%,}]"
fi

# Step 6b: 投稿テキスト生成
REPORT="build-report.json"
APP_NAME=$(python3 -c "import json; print(json.load(open('$REPORT'))['appName'])")
DESC=$(python3 -c "import json; print(json.load(open('$REPORT'))['description'])")
COST=$(python3 -c "import json; print(f\"{json.load(open('$REPORT'))['costInPlan']:.2f}\")")
TOKENS=$(python3 -c "import json; d=json.load(open('$REPORT')); print(f\"{d['totalTokens']/1_000_000:.0f}M\")")
W5=$(python3 -c "import json; print(f\"{json.load(open('$REPORT'))['windowUsagePercent']:.0f}\")")
WK=$(python3 -c "import json; print(f\"{json.load(open('$REPORT'))['weeklyUsagePercent']:.1f}\")")

TEXT="🏭 ${APP_NAME} → App Store\n\n${DESC}\n\n💰 ~\$${COST} / \$200 plan\n📊 ${TOKENS} tokens\n⏱️ 5h: ${W5}% | weekly: ${WK}%\n\n#BuildInPublic"

# Step 6c: Postiz API で @aniccaxxx に投稿
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
RESULT=$(curl -s -w "\n%{http_code}" -X POST "https://api.postiz.com/public/v1/posts" \
  -H "Authorization: $POSTIZ_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"type\":\"now\",
    \"date\":\"$NOW\",
    \"shortLink\":false,
    \"tags\":[],
    \"posts\":[{
      \"integration\":{\"id\":\"$POSTIZ_X_INTEGRATION_ID\"},
      \"value\":[{\"content\":\"$TEXT\",\"image\":$IMAGE_JSON}],
      \"settings\":{\"__type\":\"x\",\"who_can_reply_post\":\"everyone\"}
    }]
  }")

HTTP_CODE=$(echo "$RESULT" | tail -1)
if [ "$HTTP_CODE" = "201" ]; then
  echo "✅ X posted successfully"
else
  echo "❌ X post failed: $RESULT"
fi
```

## Acceptance Criteria

| Criteria | Evidence |
|----------|----------|
| build-report.json saved | `test -f build-report.json` |
| Slack posted | curl response 200/ok |
| X posted (@aniccaxxx) | Postiz response 201 + postId |
