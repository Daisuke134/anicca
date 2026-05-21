# OpenClaw 実装ステータス

**最終更新**: 2026-02-05 15:45 JST

---

## 1.6.1 スコープ

| 機能 | 説明 |
|------|------|
| Slack ミーティングリマインダー | 日曜21:00、月曜11:25 に自動投稿 |
| @Anicca メンション応答 | #metrics で質問 → 自動返答 |
| Auto metrics 統合レポート | Mixpanel + RevenueCat + ASC を毎朝9:00に自動投稿 |

---

## 認証情報

### OpenAI

| 項目 | 値 |
|------|-----|
| API Key | `(see .env OPENAI_API_KEY)` |
| plist | ✅ 設定済み |

### Mixpanel

| 項目 | 値 |
|------|-----|
| Project ID | `3970220` |
| Token | `(see .env MIXPANEL_TOKEN)` |
| API Key | `(see .env MIXPANEL_API_KEY)` |
| API Secret | `(see .env MIXPANEL_API_SECRET)` |
| plist | ✅ 設定済み |

### RevenueCat

| 項目 | 値 |
|------|-----|
| Project ID | `projbb7b9d1b` |
| V2 Secret Key | `(see .env REVENUECAT_V2_SECRET_KEY)` |
| plist | 🔲 未設定 |

### App Store Connect (ASC)

| 項目 | 値 | 取得元 |
|------|-----|--------|
| Key ID | GitHub Secrets `ASC_KEY_ID` | ASC API Keys |
| Issuer ID | GitHub Secrets `ASC_ISSUER_ID` | ASC API Keys |
| Private Key | GitHub Secrets `ASC_PRIVATE_KEY` | ASC API Keys (.p8) |
| Vendor Number | GitHub Secrets `ASC_VENDOR_NUMBER` | ASC |
| plist | 🔲 未設定 |

### Slack

| 項目 | 値 |
|------|-----|
| Bot Token | `(see .env SLACK_BOT_TOKEN)` |
| App Token | `(see .env SLACK_APP_TOKEN)` |
| #metrics Channel ID | `C091G3PKHL2` |
| openclaw.json | ✅ 設定済み |

---

## 統合 Auto Metrics レポート

現在の GitHub Action (`daily-metrics.yml`) を OpenClaw に移行。全データを1つのレポートにまとめる。

### データソース

| ソース | データ | API |
|--------|--------|-----|
| **Mixpanel** | first_app_opened, onboarding_started, paywall_viewed, trial_started | REST API (Basic Auth) |
| **RevenueCat** | MRR, Active Subs, Active Trials, Churn Rate | REST API v2 |
| **ASC** | Downloads (7d), Impressions, Page Views, CVR | Sales Reports API |

### 出力フォーマット（統合版）

```
📊 Anicca Daily Metrics (2026-02-05)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 REVENUE (RevenueCat)
  MRR: $16
  Active Subs: 5
  Active Trials: 2
  Monthly Churn: 0.0%

📱 APP STORE (ASC - 過去7日)
  Downloads: 12
  Impressions: 156
  Page Views: 45
  CVR (View→DL): 26.7%

🔄 ONBOARDING FUNNEL (Mixpanel - 過去7日)
  first_app_opened:         12 (100.0%)
  onboarding_started:       10 (83.3%)
  onboarding_paywall_viewed: 8 (66.7%)
  rc_trial_started_event:    2 (16.7%)

📈 WEEK OVER WEEK
  Downloads: 10 → 12 (+20.0%)
  Trials: 1 → 2 (+100.0%)
```

---

## 完了済みタスク

| # | タスク | 詳細 |
|---|--------|------|
| 1 | OpenClaw CLI インストール | v2026.2.2-3 |
| 2 | Gateway LaunchAgent 設定 | port 18789, KeepAlive |
| 3 | openclaw.json 設定 | Slack, agents, cron |
| 4 | Skills ディレクトリ作成 | daily-metrics-reporter, slack-mention-handler |
| 5 | Cron Jobs 登録 | 3件 (daily, sunday, monday) |
| 6 | OpenAI API Key 設定 | plist 環境変数 |
| 7 | Mixpanel credentials 設定 | plist 環境変数 |

---

## 残りタスク

| # | タスク | 詳細 |
|---|--------|------|
| 1 | plist に RevenueCat 追加 | `REVENUECAT_V2_SECRET_KEY` |
| 2 | plist に ASC credentials 追加 | `ASC_KEY_ID`, `ASC_ISSUER_ID`, `ASC_PRIVATE_KEY`, `ASC_VENDOR_NUMBER` |
| 3 | SKILL.md を統合版に更新 | Mixpanel + RevenueCat + ASC |
| 4 | Gateway 再起動 | launchctl unload/load |
| 5 | 接続テスト | `openclaw gateway status` |
| 6 | Cron テスト実行 | `openclaw cron test daily-metrics-reporter` |
| 7 | Slack 投稿確認 | #metrics に統合レポート確認 |
| 8 | メンション応答テスト | `@Anicca hello` |
| 9 | MRR クエリテスト | `@Anicca MRRは？` |

---

## 解決済みの問題

| 問題 | 原因 | 解決 |
|------|------|------|
| OpenAI API Key エラー | auth-profiles.json だけでは不十分 | plist 環境変数に追加 |
| Skills "missing" 表示 | metadata に未設定の要件 | metadata 削除 |
| mcpServers エラー | OpenClaw 未対応 | curl で直接 API 呼び出し |
| Mixpanel MCP 未対応 | OpenClaw は Claude Code の MCP にアクセス不可 | curl で直接 API 呼び出し |

---

## ファイル一覧

| ファイル | パス |
|---------|------|
| LaunchAgent plist | `/Users/cbns03/Library/LaunchAgents/ai.openclaw.gateway.plist` |
| openclaw.json | `~/.openclaw/openclaw.json` |
| daily-metrics-reporter SKILL.md | `~/.openclaw/skills/daily-metrics-reporter/SKILL.md` |
| slack-mention-handler SKILL.md | `~/.openclaw/skills/slack-mention-handler/SKILL.md` |
| 本ドキュメント | `.cursor/plans/ios/1.6.1/openclaw/implementation-status.md` |
| 親 Spec | `.cursor/plans/ios/1.6.1/openclaw/spec-openclaw-implementation.md` |

---

## Cron Job IDs

| ジョブ名 | ID |
|---------|-----|
| daily-metrics-reporter | `9ea836ce-75cc-48b7-be70-89cfe0c0a958` |
| sunday-reminder | `5fa97054-022f-4da4-874a-7c0fc12900b0` |
| monday-reminder | `f6155e45-3aa8-4798-93ba-6a968da8cedc` |

---

## 1.6.2 スコープ（メモ）

| 機能 | 説明 |
|------|------|
| X 投稿スキル | メトリクスを X に自動投稿 |
| TikTok 投稿スキル | メトリクスを TikTok に自動投稿 |
| App Nudge スキル | プッシュ通知管理 |
