# Coming - スキル修正案・出力フォーマット仕様

## 全スキルの保存パス一覧

| スキル | JSON保存パス |
|---|---|
| app-metrics | workspace/app-metrics/metrics_YYYY-MM-DD_HHmm.json |
| app-reviews | workspace/app-reviews/reviews_YYYY-MM-DD.json |
| weather-report | workspace/weather-report/weather_YYYY-MM-DD.json |
| tech-news | workspace/tech-news/news_YYYY-MM-DD.json |
| latest-papers | workspace/latest-papers/papers_YYYY-MM-DD.json |
| openclaw-usecase | workspace/openclaw-usecase/usecases_YYYY-MM-DD.json |
| slack-digest | workspace/slack-digest/digest_YYYY-MM-DD.json |
| gmail-digest | workspace/gmail-digest/digest_YYYY-MM-DD.json |
| gcal-digest | workspace/gcal-digest/digest_YYYY-MM-DD.json |

全て ~/.openclaw/workspace/ 配下。SKILL.mdに書いてある。

---

## ASCデータについて

ASCキーは全部VPSの .env にある。VPSから直接curlでASC APIを叩ける（動作確認済み）。

- JWT生成OK
- VPSからASC API完全に動く（タイムアウトは前回だけの問題）
- アプリID: 6755129214
- レビューもVPSから直で動く（3件のレビュー取得）
- MixpanelもVPSから直で動く

Mixpanelの正しいクエリ: project_idパラメータを外して、MIXPANEL_API_SECRETでBasic認証するだけ。

Sales reportはgzip形式のTSV。

---

## 全スキルの修正案

### 📊 app-metrics

実行手順:
1. RevenueCat API → VPSから直接（動作確認済み）
2. Mixpanel Export API → VPSから直接、project_idなし、Basic認証（動作確認済み）
3. ASC Sales Reports → VPSから直接、gzip→TSVパース（動作確認済み）

Mixpanel修正: project_idパラメータを外す。正しいコマンド:

```bash
curl -s "https://data.mixpanel.com/api/2.0/export?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD&event=[\"onboarding_started\",\"onboarding_paywall_viewed\",\"rc_trial_started_event\"]" \
    -u "${MIXPANEL_API_SECRET}:"
```

結果はJSONL（1行1イベント）→ jq でカウント。

ASC修正: レスポンスはgzip圧縮TSV。7日分ループして取得→awk/cutでUnits列を合算。

```bash
curl -s -o /tmp/asc.gz "https://api.appstoreconnect.apple.com/v1/salesReports?filter[vendorNumber]=${ASC_VENDOR_NUMBER}&filter[reportType]=SALES&filter[reportSubType]=SUMMARY&filter[frequency]=DAILY&filter[reportDate]=YYYY-MM-DD" \
    -H "Authorization: Bearer $JWT" -H "Accept: application/a-gzip"
gunzip -c /tmp/asc.gz | tail -n +2 | awk -F'\t' '{sum+=$8} END {print sum}'
```

JSON出力:

```json
{
  "date": "YYYY-MM-DD",
  "executedAt": "YYYY-MM-DDThh:mm:ss+09:00",
  "status": "success",
  "errorMessage": null,
  "appstore": {
    "period": "7d",
    "downloads_total": 273,
    "downloads_by_country": {"JP": 243, "CZ": 1, "HR": 1, "RO": 2, "XK": 1},
    "sales_usd": 0.00,
    "report_dates": "2026-02-09 ~ 2026-02-15"
  },
  "revenuecat": {
    "mrr": 24.00,
    "revenue_28d": 24.00,
    "active_subscribers": 3,
    "active_trials": 1,
    "new_subscribers_28d": 0,
    "churned_28d": 0
  },
  "mixpanel": {
    "period": "7d",
    "onboarding_started": 108,
    "onboarding_paywall_viewed": 59,
    "rc_trial_started_event": 0,
    "funnel": {
      "onboard_to_paywall_pct": 54.6,
      "paywall_to_trial_pct": 0.0,
      "onboard_to_trial_pct": 0.0
    }
  },
  "summary": "MRR $24 | DL 273(7d) | トライアルCVR 0.0% | 目標進捗24%",
  "bottleneck": "Paywall→トライアル変換率 0.0%。直近7日でトライアル開始0件。",
  "nextAction": "ペイウォール画面の価値訴求強化 + クレカ必須化検討"
}
```

Slack出力:

```
📊 app-metrics (HH:mm JST)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📱 APP STORE CONNECT（直近7日）
ダウンロード: 273件
国別: JP 243 / CZ 1 / HR 1 / RO 2 / XK 1
売上: $0.00

💰 REVENUECAT（1ヶ月）
MRR: $24.00
月間売上（28日）: $24.00
アクティブ購読: 3名
アクティブトライアル: 1名
新規購読: 0名 / 解約: 0名

📈 ファネル（Mixpanel 直近7日合計）
onboarding_started: 108
onboarding_paywall_viewed: 59
rc_trial_started_event: 0 ← トライアル開始

📊 変換率
オンボ→Paywall: 54.6%
Paywall→トライアル: 0.0%
オンボ→トライアル: 0.0%

🎯 目標: MRR $100 by 2/28 — 進捗 24%
⚠️ ボトルネック: 直近7日でトライアル開始0件。Paywall→トライアル変換率0%。
🔧 次のアクション: ペイウォール画面の価値訴求強化 + クレカ必須化検討
```

保存先: workspace/app-metrics/metrics_YYYY-MM-DD_HHmm.json

---

### ⭐ app-reviews

実行手順: VPSから直接ASC API（動作確認済み）

JSON出力:

```json
{
  "date": "YYYY-MM-DD",
  "executedAt": "YYYY-MM-DDThh:mm:ss+09:00",
  "status": "success",
  "errorMessage": null,
  "totalReviews": 3,
  "newReviews": 0,
  "averageRating": 5.0,
  "reviews": [
    {
      "id": "00000192-a317-7e03-275c-672200000000",
      "rating": 5,
      "title": "革新的",
      "body": "AI音声を活用した養成プランは、これまでの習慣管理アプリの常識を大きく覆しました...",
      "author": "ttdd*su",
      "createdDate": "2025-12-23T00:25:52-08:00",
      "territory": "JPN",
      "isNew": false
    }
  ],
  "sentiment": "positive",
  "keyThemes": ["AI音声コーチが好評", "習慣化支援の価値", "通知タイミングが絶妙"],
  "actionItems": ["高評価レビューのキーワード（AI音声、習慣化）をASO最適化に活用"]
}
```

Slack出力:

```
⭐ app-reviews (HH:mm JST)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 レビュー概要: 全3件 | 新着0件 | 平均 ★5.0
━━━
★★★★★ 「革新的」— ttdd*su (JP, 2025-12-23)
AI音声を活用した養成プランが従来の習慣管理アプリの常識を覆した。
AI音声による声かけが伴走者のような感覚。三日坊主だった私でも
自然と行動に移し、習慣を継続できるようになった。

★★★★★ 「最高！！」— agk925& (JP, 2025-12-01)
通知だけでなく、やれるように誘導してくれるのがいい。

★★★★★ 「Great」— anicca ai (JP, 2025-11-28)
AI voice coachが習慣達成に導いてくれる。人生が変わるかも。
━━━
🔑 キーテーマ: AI音声コーチ / 習慣化支援 / 伴走感
💡 アクション: 「AI音声」「習慣化」「伴走」をASO(App Store最適化)の
キーワードとして強化。App Store説明文にレビュー内容を反映。
🎯 MRR影響: 高評価レビュー→ASO改善→オーガニックDL増→トライアル増
```

保存先: workspace/app-reviews/reviews_YYYY-MM-DD.json

---

### 📰 tech-news

JSON出力:

```json
{
  "date": "YYYY-MM-DD",
  "executedAt": "YYYY-MM-DDThh:mm:ss+09:00",
  "status": "success",
  "errorMessage": null,
  "queries": [
    "AI app subscription revenue OR LLM mobile app",
    "iOS behavioral change app OR mindfulness app growth",
    "RevenueCat paywall optimization OR trial conversion rate"
  ],
  "articles": [
    {
      "title": "フリートライアルにクレカ必須化でCVR 6倍",
      "url": "https://x.com/FilipPanoski/status/xxx",
      "author": "@FilipPanoski",
      "likes": 13,
      "retweets": 2,
      "summary": "フリートライアルにクレジットカードを要求することで、CVRが2.5%から14.6%に向上した事例報告。クレカ入力がqualification filterとして機能し、本気のユーザーだけが残る。ただしトライアル開始数自体は減るため、十分なトラフィック（DAU 50+）が前提条件。",
      "mrrImpact": "Aniccaに即適用可能。現在のPaywall→トライアルCVR 0%の改善に直結。RevenueCatのtrial設定でクレカ必須化可能。ただしAniccaのDAUが低い（推定10-20）ため、まずDAU向上施策（ASO最適化）を並行すべき。",
      "implementation": "1. RevenueCat Dashboard → Products → Trial設定 → 'Require payment method' を有効化\n2. Superwall ペイウォール画面に「7日間無料、いつでもキャンセル可能」の文言追加\n3. aniccaios/Services/SubscriptionManager.swift のtrial開始フロー確認\n4. Mixpanelで rc_trial_started_event を1週間計測→効果検証",
      "category": "revenue"
    }
  ],
  "topInsight": "クレカ必須化でCVR 6倍。Aniccaの現在のPaywall→トライアルCVR 0%に即適用可能。"
}
```

Slack出力:

```
📰 tech-news (HH:mm JST)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔝 今日の最重要インサイト:
フリートライアルにクレカ必須化でCVR 2.5%→14.6%（6倍改善）。
Aniccaの現在のPaywall→トライアルCVR 0%に即適用可能。

━━━ 記事詳細 ━━━

📌 [1] クレカ必須化でトライアルCVR 6倍
@FilipPanoski (❤️13 🔁2) — https://x.com/FilipPanoski/status/xxx

詳細: フリートライアルにクレジットカードを要求することで、
CVRが2.5%から14.6%に向上。クレカ入力がqualification filterと
して機能し、「試すだけ」のユーザーを除外。ただしトライアル
開始の絶対数は減るため、DAU 50+が前提。

🎯 MRR影響: Aniccaに即適用可能。現在CVR 0%からの改善。
RevenueCatのtrial設定でクレカ必須化可能。DAUが低い
（推定10-20/日）ため、ASO最適化と並行実施が必要。

🔧 実装:
1. RevenueCat Dashboard → Products → Trial → 'Require payment method' ON
2. Superwall: ペイウォールに「7日間無料、いつでもキャンセル」追加
3. aniccaios/Services/SubscriptionManager.swift 確認
4. Mixpanelで rc_trial_started_event を1週間計測→効果検証

━━━

📌 [2] アプリトライアル驚異的指標: 開始率32%, CVR 41%
@BusDownBonnor (❤️92 🔁18) — https://x.com/BusDownBonnor/status/xxx

詳細: 開発者がファネル指標を公開。トライアル開始率32%、
トライアル→有料転換率41%。業界平均の3-5倍。要因は
オンボーディング中の「あなたの問題をXX日で解決」という
具体的約束をペイウォール前に提示。

🎯 MRR影響: Aniccaのオンボ→Paywall 54.6%は良い。
Paywall画面での具体的価値訴求を強化すべき。
「7日間で苦しみの感覚が30%減る」等の数値入り約束。

🔧 実装:
1. aniccaios/Views/PaywallView.swift に具体的数値訴求を追加
2. A/Bテスト: Superwall で variant 作成
3. 「苦しみスコア30%低減」等のコピーテスト
```

保存先: workspace/tech-news/news_YYYY-MM-DD.json

---

### 📚 latest-papers

JSON出力:

```json
{
  "date": "YYYY-MM-DD",
  "executedAt": "YYYY-MM-DDThh:mm:ss+09:00",
  "status": "success",
  "errorMessage": null,
  "papers": [
    {
      "title": "Intelligent AI Delegation: Multi-Agent Coordination Framework",
      "url": "https://arxiv.org/abs/xxxx.xxxxx",
      "tweetUrl": "https://x.com/user/status/xxx",
      "authors": "Google DeepMind et al.",
      "sharedBy": "@xxx",
      "likes": 200,
      "retweets": 45,
      "summary": "複数のAIエージェントが協調してタスクを委任・実行するフレームワーク。従来の単一エージェント方式と比較して、タスク完了率が23%向上。エージェント間の「信頼度スコア」に基づく動的委任と、失敗時の自動フォールバック機構を実装。人間の介入ポイントの最適化も含む。",
      "relevance": "both",
      "aniccaApplication": "suffering-detector→nudge-generator→posterパイプラインに信頼度ベースの委任を導入。精度低のNudgeは人間レビュー（Slack承認フロー）に回す。",
      "researchApplication": "マルチモーダル入力（EEG+瞳孔径+RT）の統合判断にこのフレームワークを適用。各モダリティの信頼度に応じた重み付け。",
      "implementation": "1. workspace/ops/steps.json に信頼度スコアフィールド追加\n2. apps/api/src/services/nudge/ にconfidence threshold設定\n3. Slack承認フローをE1として実装（trend-hunterと共用）"
    }
  ],
  "topPaper": "Google DeepMind 多エージェント協調 — タスク完了率23%向上のフレームワーク",
  "researchNote": "CHI 2026論文は「OpenClawによる研究の自動化」発表で引用すべき重要知見"
}
```

Slack出力:

```
📚 latest-papers (HH:mm JST)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔝 今日の最重要論文:
"Intelligent AI Delegation" (Google DeepMind)
多エージェント協調フレームワーク。タスク完了率23%向上。

━━━ 論文詳細 ━━━

📄 [1] Intelligent AI Delegation
Google DeepMind | @xxx (❤️200 🔁45)
https://arxiv.org/abs/xxxx.xxxxx

概要: 複数AIエージェントが協調してタスクを委任・実行する
フレームワーク。エージェント間の「信頼度スコア」に基づく
動的委任。失敗時の自動フォールバック。人間介入ポイントの最適化。
従来の単一エージェントと比較してタスク完了率23%向上。

🧪 Anicca応用:
suffering-detector→nudge-generator→posterパイプラインに
信頼度ベース委任を導入。精度低Nudgeは人間レビューへ。

📖 Dais研究:
EEG+瞳孔径+RTのマルチモーダル統合判断に適用可能。
各モダリティの信頼度に応じた動的重み付け。

🔧 実装:
1. workspace/ops/steps.json に confidence_score フィールド追加
2. apps/api/src/services/nudge/ に閾値設定
3. Slack承認フロー（E1）で低信頼度Nudgeをレビュー

━━━

📄 [2] CHI 2026: 人間-AI感情的結びつき
Syracuse大 | @xxx (❤️251 🔁38)
https://doi.org/xxx

概要: AIとの対話が感情的結びつきを形成するメカニズムをRCTで実証。
3ヶ月のRCT（N=420）でパーソナライズAI対話群のウェルビーイング
スコアが統制群より18%高い。週3回以上で依存傾向上昇のリスク。

🧪 Anicca応用:
Nudge頻度最適化に直結。現在3回/日（朝昼晩）は適切だが、
回数より品質を上げてLTV最大化。依存リスク回避のため
週3-4日のNudge休息日を設けることを検討。

📖 Dais研究:
「OpenClawによる研究の自動化」発表で必ず引用。
HCI分野でAIエージェント×行動変容の研究が注目されている証拠。

🔧 実装:
1. apps/api/src/services/nudge/scheduler.js に休息日ロジック追加
2. Mixpanelで「Nudge無し日」のretention比較テスト

━━━

🔬 研究メモ: CHI 2026はDais発表の必須引用文献。
```

保存先: workspace/latest-papers/papers_YYYY-MM-DD.json

---

### 🐾 openclaw-usecase

JSON出力:

```json
{
  "date": "YYYY-MM-DD",
  "executedAt": "YYYY-MM-DDThh:mm:ss+09:00",
  "status": "success",
  "errorMessage": null,
  "usecases": [
    {
      "title": "Slack承認フローでcronコンテンツを品質管理",
      "url": "https://x.com/xxx/status/xxx",
      "author": "@xxx",
      "likes": 45,
      "retweets": 12,
      "summary": "OpenClawのcronで生成したコンテンツをSlackに投稿し、チーム全員がリアクションで承認/却下する仕組み。cron→isolated session→Slack投稿→メインセッションでリアクション監視→承認なら次のcronで投稿。却下理由はメモリに保存し、次回生成に反映。",
      "applicability": "trend-hunter→hook生成→Slack承認→x-poster/tiktok-posterの承認フローに直接使える。コンテンツ品質向上→エンゲージメント増→フォロワー増→DL増→MRR増。",
      "implementation": "1. ~/.openclaw/skills/trend-hunter/SKILL.md に承認ステップ追加\n2. Slack message tool でhook内容を#metricsに投稿\n3. cron: リアクション確認→投稿 or スキップ\n4. 却下理由をworkspace/feedback/rejected.jsonに保存\n5. trend-hunterが次回rejected.jsonを参照して改善",
      "category": "automation",
      "priority": "high"
    }
  ],
  "topUsecase": "Slack承認フロー — コンテンツ品質管理の自動化"
}
```

Slack出力:

```
🐾 openclaw-usecase (HH:mm JST)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔝 今日の最重要ユースケース:
Slack承認フローでcronコンテンツを品質管理。
品質向上→エンゲージメント増→フォロワー増→DL増→MRR増。

━━━ ユースケース詳細 ━━━

🔧 [1] Slack承認フロー実装例 [HIGH]
@xxx (❤️45 🔁12) — https://x.com/xxx/status/xxx

詳細: OpenClawのcronで生成したコンテンツをSlackに投稿し、
リアクションで承認/却下。却下理由はメモリに保存して
次回生成に反映するフィードバックループ。

💡 Anicca適用:
trend-hunter→hook生成→Slack#metricsに投稿→
リアクション承認→x-poster/tiktok-posterが投稿。

🔧 実装:
1. ~/.openclaw/skills/trend-hunter/SKILL.md に承認ステップ追加
2. Slack message tool で hook内容を #metrics に投稿
3. cron: リアクション確認 → 投稿 or スキップ
4. 却下理由を workspace/feedback/rejected.json に保存
5. trend-hunter が次回 rejected.json を参照して改善
```

保存先: workspace/openclaw-usecase/usecases_YYYY-MM-DD.json

---

### 😣 suffering-detector 修正ポイント

現在JSONをそのままSlackに貼ってる → 以下のSlack形式に変更:

```
😣 suffering-detector (HH:mm JST)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 検知結果: 4件 | 最大severity: 0.7 | SAFE-T発動: なし

━━━ 検知詳細 ━━━

⚠️ [severity 0.7] SNSと若年層の自殺リスク相関
ソーシャルメディア使用時間と若年層の鬱・自殺リスクの
相関を示す新たなエビデンス。特にTikTokの短尺動画による
注意散漫化が問題視。Aniccaのマインドフルネス介入が
このリスク軽減に貢献できる可能性。

⚠️ [severity 0.6] AI/気候不安によるメンタルヘルス危機
AI職場ストレス + 気候変動不安の複合的メンタルヘルス影響。
2026年特有のストレッサーパターン。

⚠️ [severity 0.5] 2026年の警戒サイン
現在の社会環境における精神的健康の警戒指標。

ℹ️ [severity 0.4] デジタル社会化のパラドックス
デジタルファースト社会化による孤立感の増大。

━━━
📊 全体評価: 急性危機なし。継続監視。
🎯 Anicca対応: SNS×メンタルヘルスのコンテンツを
次回trend-hunterのhookテーマに追加検討。
```

保存先: workspace/suffering/findings_YYYY-MM-DD.json

---

## TODO

### 1. app-metrics SKILL.md パッチ
- ファイル: `~/.openclaw/skills/app-metrics/SKILL.md`
- 修正: Mixpanelのproject_idパラメータ削除、Basic認証に修正。ASCのgzip→TSVパース手順を正確に記載。

### 2. app-reviews SKILL.md パッチ
- ファイル: `~/.openclaw/skills/app-reviews/SKILL.md`
- 修正: VPSから直接ASC APIで動く手順に更新（Mac SSH経由不要）。

### 3. suffering-detector
- ❌ JSONをそのままSlackに貼ってる → 詳細要約を書くべき
- ファイル: `~/.openclaw/skills/suffering-detector/SKILL.md`

### 4. latest-papers / tech-news / openclaw-usecase
- ❌ 決めたJSON/Slackフォーマットに従ってない
- ❌ 詳細要約がない（1行だけ）
- ❌ MRR直結の分析が浅い
- ❌ todayActionとimplementationが分離してた → 統合済み（上記参照）
- ファイル: 各 `~/.openclaw/skills/{latest-papers,tech-news,openclaw-usecase}/SKILL.md`

### 5. .env にGOG情報保存
- `~/.openclaw/.env` に `GOG_KEYRING_PASSWORD` と `GOG_ACCOUNT` を追加

### 6. MEMORYに記録
- 「ローカルでコマンド実行できない」と言うの禁止
