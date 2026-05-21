# 日次メトリクス自動化 Spec

## 概要（What & Why）

毎朝5:00 JSTにSlack通知で、DL数・MRR・ASAパフォーマンス・DAUを自動レポート。
手動でApp Store Connect / RevenueCat / Apple Ads を毎日見に行く作業を排除する。

**なぜ必要か:**
- 現在は手動でASC/RevenueCat/Apple Adsを確認 → 忘れる、遅れる
- 変更（タイトル変更、KW追加）と結果の因果関係を追跡できない
- ASO/ASAの最適化サイクルが遅い（週1→日次に短縮したい）

## 受け入れ条件

| # | 条件 | テスト可能か |
|---|------|-------------|
| 1 | 毎朝5:00 JSTにSlack通知が届く | YES: Cron実行ログ確認 |
| 2 | DL数（国別）が含まれる | YES: Slack投稿内容確認 |
| 3 | MRR・トライアル開始数が含まれる | YES: 同上 |
| 4 | ASA支出・CPA・勝ちKWが含まれる | YES: 同上 |
| 5 | DAU・オンボ完了率が含まれる | YES: 同上 |
| 6 | 前日比が表示される | YES: 同上 |
| 7 | エラー時はSlackにエラー通知が届く | YES: 意図的にAPIキー無効化して確認 |

## ユーザーGUI作業（実装前に必須）

| # | タスク | 手順 | 取得するもの |
|---|--------|------|-------------|
| 1 | **Slack App作成 + Webhook URL取得** | https://api.slack.com/apps → Create New App → From scratch → App名: `Anicca Metrics Bot` → ワークスペース選択 → Incoming Webhooks → Activate → Add New Webhook to Workspace → チャンネル選択（#anicca-metrics 推奨） | Webhook URL |
| 2 | **App Store Connect API Key取得** | https://appstoreconnect.apple.com → Users and Access → Integrations → App Store Connect API → Generate API Key → Name: `Metrics Bot` → Access: `App Manager` → Download .p8 file | Key ID, Issuer ID, .p8 file |
| 3 | **Apple Search Ads API セットアップ** | https://app.searchads.apple.com → Settings → API → Create API Certificate → Download証明書 | Client ID, Client Secret, Org ID |
| 4 | **Railway環境変数に追加** | Railway Dashboard → anicca-api → Variables → 以下を追加 | - |

### Railway環境変数（タスク4で追加するもの）

```
SLACK_METRICS_WEBHOOK_URL=https://hooks.slack.com/services/xxx
ASC_KEY_ID=xxxx
ASC_ISSUER_ID=xxxx
ASC_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\nxxxx\n-----END PRIVATE KEY-----
ASA_CLIENT_ID=xxxx
ASA_CLIENT_SECRET=xxxx
ASA_ORG_ID=xxxx
```

**注意:** ASC_PRIVATE_KEYは.p8ファイルの中身を改行→`\n`に変換して1行にする。

## As-Is / To-Be

### As-Is

```
毎日手動で4つのダッシュボードを確認:
- App Store Connect → DL数、インプレッション
- RevenueCat → MRR、トライアル
- Apple Ads → 支出、CPA
- Mixpanel → DAU
→ 忘れる、遅れる、因果関係追跡できない
```

### To-Be

```
Railway Cron (0 20 * * * UTC = 5:00 JST)
    ↓
apps/api/src/scripts/daily-metrics.ts
    ↓ 並列API呼び出し
    ├── App Store Connect API → DL数(国別)、インプレッション、CVR
    ├── RevenueCat API → MRR、トライアル開始数、課金転換率
    ├── Apple Search Ads API → 支出、CPA、Top 3 KW
    └── Mixpanel API → DAU、オンボ完了率
    ↓
Slack Webhook POST
    ↓
#anicca-metrics チャンネルに投稿
```

### Slack通知フォーマット

```
📊 Anicca Daily Report (2026-01-28)

【DL】 4 (+1) | US: 2, JP: 1, EU: 1
【MRR】 $XX (+$X)
【トライアル】 2 started, 0 converted
【セッション/DAU】 3.46

【ASA JP】 ¥380 spent | 1 install | CPA ¥380
  勝ちKW: 集中アプリ (CPA ¥89)
【ASA EU】 ¥200 spent | 0 install
  —

【前日の変更メモ】
- Title変更: 能動的セルフケア → セルフケア・習慣改善
- KW 5個追加（無料系）

【ファネル】
Imp: 900/日 → ページ: 13 (1.4%) → DL: 4 (21%)
```

### ファイル構成

```
apps/api/src/scripts/
├── daily-metrics.ts          ← メインスクリプト
├── metrics/
│   ├── asc-client.ts         ← App Store Connect API
│   ├── asa-client.ts         ← Apple Search Ads API
│   ├── revenuecat-client.ts  ← RevenueCat API
│   ├── mixpanel-client.ts    ← Mixpanel API
│   └── slack-sender.ts       ← Slack Webhook送信
└── types/
    └── metrics.ts            ← 型定義
```

## テストマトリックス

| # | To-Be | テスト名 | カバー |
|---|-------|----------|--------|
| 1 | ASC APIからDL数取得 | `test_fetchAppStoreMetrics()` | ✅ |
| 2 | RevenueCat APIからMRR取得 | `test_fetchRevenueCatMetrics()` | ✅ |
| 3 | ASA APIから支出・CPA取得 | `test_fetchSearchAdsMetrics()` | ✅ |
| 4 | Mixpanel APIからDAU取得 | `test_fetchMixpanelMetrics()` | ✅ |
| 5 | Slack投稿フォーマット生成 | `test_formatSlackMessage()` | ✅ |
| 6 | 前日比計算 | `test_calculateDayOverDay()` | ✅ |
| 7 | API エラー時のフォールバック | `test_apiErrorHandling()` | ✅ |
| 8 | Cron実行（統合テスト） | `test_cronExecution()` | ✅ |

## 境界

### やること
- 4つのAPIからメトリクス取得
- Slackに日次レポート送信
- 前日比の計算
- エラーハンドリング（1つのAPI失敗でも他は送信）

### やらないこと
- ダッシュボードUI作成
- メトリクスのDB保存（Phase 2）
- 自動Bid調整（Phase 2）
- A/Bテスト自動判定（Phase 2）

## 実行手順

```bash
# 開発・テスト
cd apps/api && npm run test -- --grep "daily-metrics"

# 手動実行（テスト用）
cd apps/api && npx ts-node src/scripts/daily-metrics.ts

# Railway Cron設定
# Railway Dashboard → anicca-api → Settings → Cron → Add
# Schedule: 0 20 * * * (UTC = 5:00 JST)
# Command: npx ts-node src/scripts/daily-metrics.ts
```
