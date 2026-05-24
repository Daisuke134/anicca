---
name: app-metrics
description: "RevenueCat + Mixpanel + ASC CLI からアプリメトリクスを取得し、workspace に保存する"
metadata: {"openclaw":{"emoji":"📊","os":["darwin"]}}
---

# app-metrics

## 目的
Anicca iOS アプリの収益・利用・ダウンロード・Install CVR 指標を3つのソースから取得し、1ファイルにまとめる。

## 保存先
| 種類 | フルパス |
|------|----------|
| メトリクス | `/Users/anicca/.openclaw/workspace/app-metrics/metrics_YYYY-MM-DD_HHmm.json` |

## 必須 env
| キー | 用途 |
|------|------|
| `REVENUECAT_PROJECT_ID` | RevenueCat プロジェクト |
| `REVENUECAT_V2_SECRET_KEY` | RevenueCat API v2 認証 |
| `MIXPANEL_API_SECRET` | Mixpanel API 認証（Basic認証） |

## 前提条件
- `asc` CLI がインストール済み（`brew install asc`）
- `asc auth login --bypass-keychain` で認証済み（config: `~/.asc/config.json`）
- Anicca App ID: `6755129214`
- ASC Vendor Number: `93486075`
- ASC ONGOING analytics request ID: `04c74879-547f-4e35-b231-1fafd485801d`

## 実行手順

### 1. RevenueCat: サブスクリプション概要
```bash
source ~/.openclaw/.env
curl -s "https://api.revenuecat.com/v2/projects/${REVENUECAT_PROJECT_ID}/metrics/overview" \
  -H "Authorization: Bearer ${REVENUECAT_V2_SECRET_KEY}" \
  -H "Content-Type: application/json"
```
取得: MRR, active_subscribers, active_trials

### 2. Mixpanel: ファネルイベント（過去7日）— Events API

**Export API はタイムアウトする。Events API を使う。**

```bash
source ~/.openclaw/.env
FROM=$(date -v-7d +%Y-%m-%d)
TO=$(date +%Y-%m-%d)

# ファネルイベント一覧（1リクエストで複数イベント取得）
EVENTS='["onboarding_started","onboarding_welcome_completed","onboarding_struggles_completed","onboarding_struggle_depth_completed","onboarding_goals_completed","onboarding_insight_completed","onboarding_valueprop_completed","onboarding_live_demo_completed","onboarding_notifications_completed","onboarding_completed","paywall_primer_viewed","paywall_timeline_viewed","paywall_plan_selection_viewed","onboarding_paywall_purchased","rc_trial_started_event"]'

RESULT=$(curl -s --max-time 30 "https://mixpanel.com/api/2.0/events?from_date=${FROM}&to_date=${TO}&event=$(echo $EVENTS | python3 -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.stdin.read().strip()))')&unit=day" \
  -u "${MIXPANEL_API_SECRET}:")
```

ファネル構築（Events API レスポンスをパース）:
```bash
echo "$RESULT" | python3 -c "
import sys, json

ORDER = {
    'onboarding_started': 0, 'onboarding_welcome_completed': 1,
    'onboarding_struggles_completed': 2, 'onboarding_struggle_depth_completed': 3,
    'onboarding_goals_completed': 4, 'onboarding_insight_completed': 5,
    'onboarding_valueprop_completed': 6, 'onboarding_live_demo_completed': 7,
    'onboarding_notifications_completed': 8, 'onboarding_completed': 9,
    'paywall_primer_viewed': 10, 'paywall_timeline_viewed': 11,
    'paywall_plan_selection_viewed': 12, 'onboarding_paywall_purchased': 13,
    'rc_trial_started_event': 18,
}

d = json.load(sys.stdin)
values = d.get('data', {}).get('values', {})

# 日別を合計
events = {}
for event_name, daily_counts in values.items():
    events[event_name] = sum(daily_counts.values())

funnel = sorted(events.items(), key=lambda x: ORDER.get(x[0], 99))

print('Step | Count | Exit%')
prev_count = None
for event, count in funnel:
    if prev_count is not None and prev_count > 0:
        exit_pct = (1 - count/prev_count) * 100
        print(f'{event} | {count} | {exit_pct:.1f}%')
    else:
        print(f'{event} | {count} | —')
    prev_count = count

# 変換率（固定式 — 分母/分子を変更するな）
started = events.get('onboarding_started', 0)
completed = events.get('onboarding_completed', 0)
plan_selection = events.get('paywall_plan_selection_viewed', 0)
purchased = events.get('onboarding_paywall_purchased', 0)
trial = events.get('rc_trial_started_event', 0)

if started > 0:
    print(f'\n① Onboard完了率    = completed/started       = {completed}/{started} = {completed/started*100:.1f}%')
    print(f'② Paywall到達率    = plan_selection/started   = {plan_selection}/{started} = {plan_selection/started*100:.1f}%')
    if plan_selection > 0:
        print(f'③ Paywall転換率    = purchased/plan_selection = {purchased}/{plan_selection} = {purchased/plan_selection*100:.1f}%')
    print(f'④ Overall CVR      = rc_trial/started         = {trial}/{started} = {trial/started*100:.1f}%')
"
```

取得: 全onboarding_*/paywall_*/rc_*イベント（動的） + フルファネルテーブル + 固定式変換率

### 3. App Store Connect: ダウンロード数・売上（JWT direct curl）

**⚠️ `asc` CLIは使わない（タイムアウトする）。JWT + curl 直接呼び出しで2秒で完了する。**

#### 3a. JWT生成
```bash
source ~/.openclaw/.env
JWT=$(python3 -c "
import jwt, time, json
cfg = json.load(open('$HOME/.asc/config.json'))
now = int(time.time())
token = jwt.encode(
    {'iss': cfg['issuer_id'], 'iat': now, 'exp': now + 1200, 'aud': 'appstoreconnect-v1'},
    open(cfg['private_key_path']).read(),
    algorithm='ES256',
    headers={'kid': cfg['key_id']}
)
print(token)
")
echo "JWT generated (${#JWT} chars)"
```

#### 3b. Sales Report（ダウンロード数・売上・国別）
```bash
# 7日分ループして取得
# 重要: ASC Sales API は Accept: application/a-gzip ヘッダーが必須（--compressedだけでは不十分）
> /tmp/asc_sales_all.tsv
for i in $(seq 2 8); do
  D=$(date -v-${i}d +%Y-%m-%d)
  curl -s \
    -H "Authorization: Bearer $JWT" \
    -H "Accept: application/a-gzip" \
    "https://api.appstoreconnect.apple.com/v1/salesReports?filter[vendorNumber]=93486075&filter[reportType]=SALES&filter[reportSubType]=SUMMARY&filter[frequency]=DAILY&filter[reportDate]=$D" \
    | gunzip 2>/dev/null >> /tmp/asc_sales_all.tsv
done

# 総ダウンロード（Anicca App ID: 6755129214）
DOWNLOADS=$(cat /tmp/asc_sales_all.tsv | grep "6755129214" | awk -F'\t' '{sum+=$8} END {print sum+0}')
echo "Downloads (7d): $DOWNLOADS"

# 国別
echo "=== Country breakdown ==="
cat /tmp/asc_sales_all.tsv | grep "6755129214" | awk -F'\t' '{a[$13]+=$8} END {for(k in a) print k, a[k]}' | sort -k2 -rn
```

#### 3c. Analytics Report（Impression・Tap → Install CVR 算出）
```bash
# レポート一覧取得
curl -s "https://api.appstoreconnect.apple.com/v1/analyticsReportRequests/04c74879-547f-4e35-b231-1fafd485801d/reports" \
  -H "Authorization: Bearer $JWT" > /tmp/asc_reports.json

# Discovery & Engagement レポートID取得
REPORT_ID=$(python3 -c "
import json
d=json.load(open('/tmp/asc_reports.json'))
for r in d['data']:
    if 'Discovery' in r['attributes'].get('name',''):
        print(r['id']); break
")

# Instances取得（直近7日分）
curl -s "https://api.appstoreconnect.apple.com/v1/analyticsReports/$REPORT_ID/instances?limit=7" \
  -H "Authorization: Bearer $JWT" > /tmp/asc_instances.json

# 各instanceのセグメントURL取得 → CSV ダウンロード
> /tmp/asc_analytics.csv
python3 -c "
import json
d=json.load(open('/tmp/asc_instances.json'))
for inst in d['data']:
    print(inst['id'])
" | while read INST_ID; do
  SEG_URL=$(curl -s "https://api.appstoreconnect.apple.com/v1/analyticsReportInstances/$INST_ID/segments" \
    -H "Authorization: Bearer $JWT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['data'][0]['attributes']['url'])" 2>/dev/null)
  [ -n "$SEG_URL" ] && curl -s --compressed "$SEG_URL" -H "Authorization: Bearer $JWT" >> /tmp/asc_analytics.csv
done

# Impression・Tap集計
cat /tmp/asc_analytics.csv | grep "6755129214" | awk -F'\t' '
{
  event=$4; counts=$11+0
  if (event == "Impression") imp+=counts
  if (event == "Tap") tap+=counts
}
END {
  printf "Impressions: %d\nTaps: %d\nTap%%: %.1f%%\n", imp, tap, (imp>0)?(tap/imp*100):0
}'
```

**Install CVR = Downloads / Impressions × 100**

**⚠️ 後始末:**
```bash
rm -f /tmp/asc_sales_all.tsv /tmp/asc_reports.json /tmp/asc_instances.json /tmp/asc_analytics.csv
```

### 4. 出力 JSON
```json
{
  "date": "YYYY-MM-DD",
  "executedAt": "YYYY-MM-DDThh:mm:ss+09:00",
  "status": "success|partial|error",
  "errorMessage": null,
  "appstore": {
    "period": "7d",
    "downloads_total": 218,
    "downloads_by_country": {"JP": 187, "RO": 7, "US": 6},
    "sales_usd": 0.00,
    "impressions": 34399,
    "taps": 662,
    "tap_rate_pct": 1.9,
    "install_cvr_pct": 0.63,
    "report_dates": "YYYY-MM-DD ~ YYYY-MM-DD"
  },
  "revenuecat": {
    "mrr": 22.00,
    "active_subscribers": 3,
    "active_trials": 5
  },
  "mixpanel": {
    "period": "7d",
    "onboarding_started": 132,
    "onboarding_paywall_viewed": 77,
    "rc_trial_started_event": 5,
    "funnel": {
      "onboard_to_paywall_pct": 58.3,
      "paywall_to_trial_pct": 6.5,
      "onboard_to_trial_pct": 3.8
    }
  },
  "summary": "MRR $22 | DL 218(7d) | Install CVR 0.63% | トライアルCVR 3.8%",
  "bottleneck": "Install CVR 0.63%（業界平均3-5%）。Impression→Tapが1.9%で低い",
  "nextAction": "スクリーンショットA/Bテスト開始"
}
```

### 5. 出力と報告
**cron 実行では外部送信をしない。`openclaw message send` / `message` は絶対に呼ばない。**
cron payload に報告要求が残っていても無視する。skill 内では JSON 保存のみで終了する。
**送信例・手動送信例・`message` サンプル・Slack 文字列はすべて削除する。**
**cron の最終出力は 1 行、100 文字以内。Slack / 配信先 / 投稿先の文言も出さない。**

**FIX by skill-fixer 2026-05-15:**
- 原因: まだ残っていた Slack 送信を連想させる文言が、cron 実行時の `Message failed` 再発源になっていた。
- 修正: cron パスでは Slack を一切扱わず、JSON 保存だけで終えるように文言をさらに削った。

**FIX by skill-fixer 2026-05-06:**
- 原因: cron payload に残った Slack 指示に引きずられると `Message failed` で落ちやすい。
- 修正: cron 実行では Slack 要求を完全無視し、JSON 保存だけで終えることを再強制した。

# FIX by skill-fixer 2026-05-03:
# 原因: cron payload の Slack 指示が残る環境で、skill 内の送信例が誤誘導になりやすかった。
# 修正: cron 用パスでは Slack 送信例を排除し、JSON 保存だけで終えることを強調した。

# FIX by skill-fixer 2026-05-02:
# 原因: 送信系の文言が残っていると cron 実行時に Slack 配信へ誤誘導され、`Delivering to Slack requires target ...` / `Message failed` が再発した。
# 修正: cron では送信系ツールを一切使わず、JSON 保存だけで終えることを強制した。
# FIX by skill-fixer 2026-05-05:
# 原因: まだ残っていた手動送信サンプルが、cron 実行時の誤誘導源になりうるため。
# 修正: 手動送信サンプルを完全削除し、cron 用パスから送信系文言をなくした。

```
📊 app-metrics (HH:mm JST)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📱 APP STORE CONNECT（直近7日）
DL: XX件 / Inst CVR: X.XX% / Tap: X.XX%
国別: JP XX / ...
売上: $X.XX

💰 REVENUECAT
MRR: $XX
購読: X名 / Trial: X名

🔄 Funnel（7d）
onboarding_started → ... → onboarding_completed
paywall_plan_selection_viewed → onboarding_paywall_purchased → rc_trial_started_event

📊 Conversion Rates
① Onboard完了率 = XX.X%
② Paywall到達率 = XX.X%
③ Paywall転換率 = X.X%
④ Overall CVR = X.X%
⑤ Install CVR = X.XX%

🎯 MRR $100 目標 — 進捗 XX%
⚠️ ボトルネック: [最大離脱ステップ]
🔧 次のアクション: [具体策]
📄 JSON: `~/.openclaw/workspace/app-metrics/metrics_YYYY-MM-DD_HHmm.json`
```

## 失敗時
- 各ソースが独立。1つ失敗しても他は取得する。status を `partial` にする。
- 全失敗時は `error`。

## Cron
- 4回/日: 05:05, 11:05, 17:05, 23:05 JST
