# 日次メトリクス自動化 Spec

## 概要（What & Why）

毎朝5:15 JSTにSlack通知で、MRR・DL数・CVR・Trial転換率・チャーンを自動レポート。
手動でApp Store Connect / RevenueCatを毎日見に行く作業を排除する。

**なぜ必要か:**
- 現在は手動でASC/RevenueCatを確認 → 忘れる、遅れる
- 変更（タイトル変更、KW追加）と結果の因果関係を追跡できない
- ASO/ASAの最適化サイクルが遅い（週1→日次に短縮したい）

## アーキテクチャ決定

### 実行環境: GitHub Actions（Railway Cronではない）

| 判断基準 | GitHub Actions | Railway Cron |
|---------|---------------|-------------|
| DB必要？ | ❌ 不要（外部APIのみ） | ✅ 本来DB用 |
| コスト | **$0** | 従量課金 |
| 障害分離 | マーケ自動化 ≠ ユーザー機能 | API障害 → メトリクスも死ぬ |
| 既存実績 | TikTok投稿/メトリクスで安定稼働 | - |

**ルール: DB必要 → Railway。外部APIのみ → GitHub Actions。**

### なぜRailwayではないか

このタスクは App Store Connect API + RevenueCat API + Slack Webhook しか使わない。
PostgreSQLもAPIサーバーも不要。Railwayの環境変数に置くのは「たまたまそこにあるから」で、アーキテクチャとして間違い。

### Cronジョブ全体の分離方針

| ジョブ | DB必要？ | 実行環境 |
|--------|---------|---------|
| Nudge生成 | ✅ PostgreSQL直接接続 | Railway Cron |
| Type Stats集計 | ✅ PostgreSQL直接接続 | Railway Cron |
| TikTok投稿 | ❌ 外部APIのみ | GitHub Actions |
| TikTokメトリクス | ❌ 外部APIのみ | GitHub Actions |
| **日次メトリクス（NEW）** | ❌ 外部APIのみ | **GitHub Actions** |

### 将来の移行先検討（不要。現時点で移行しない）

| プラットフォーム | 検討結果 | 却下理由 |
|-----------------|---------|---------|
| Cloudflare Workers Cron | Plan B（GH Actionsが不安定になった場合のみ） | 現状困ってない |
| AWS Lambda + EventBridge | 信頼性★5だが学習コスト高 | ソロ開発に不向き |
| Clawd.bot / Moltbot | AIアシスタント。面白いがcronには$10-25/月かかる | Phase 2でAI分析用に検討 |
| VPS | $4/月〜 + メンテ2-4時間/月 | $0のGH Actionsが動いてるのに金払う理由なし |
| Lindy AI | AIエージェント型。$49/月〜 | 20x高い。知能不要なタスクにAIは不要 |

## Phase分割

### Phase 1（今回実装）: コアメトリクス

| # | メトリクス | ソース | なぜ重要か |
|---|-----------|--------|-----------|
| 1 | **MRR** | RevenueCat API v2 | ビジネスの健康状態 |
| 2 | **インストール数（直近7日）** | App Store Connect API | ファネルの入口。目標70/週 |
| 3 | **CVR（ページ閲覧→DL）** | App Store Connect API | 目標3%。ASO最適化の成果 |
| 4 | **Trial→Paid転換率** | RevenueCat API v2 | B2Cアプリ中央値40-50%。収益の生命線 |
| 5 | **月次チャーン率** | RevenueCat API v2 | 初月30%離脱。ここを下げるのが最優先 |
| 6 | **アクティブサブスク数** | RevenueCat API v2 | MRRの裏付け |
| 7 | **DL数（国別）** | App Store Connect API | 地域別パフォーマンス |

### Phase 2（後日）: 拡張

| # | メトリクス | ソース |
|---|-----------|--------|
| 1 | ASA支出・CPA・勝ちKW | Apple Search Ads API |
| 2 | DAU・オンボ完了率 | Mixpanel API |
| 3 | メトリクスDB保存 | JSON → DB（AIエージェントの将来入力用） |
| 4 | AI分析・改善提案 | Claude Code / Moltbot |
| 5 | 自動Bid調整 | Apple Search Ads API |

### 将来ビジョン（V2.0+）: 自律型プロダクト改善

**70%リアル、30%ハイプ。** 段階的に実現可能。

| Phase | 時期 | できること |
|-------|------|-----------|
| V1 | 今 | メトリクス収集 → Slack通知 → 人間が判断 |
| V2 | 3-6ヶ月後 | AIがメトリクス分析 → 改善提案を生成 → 人間が承認 |
| V3 | 6-12ヶ月後 | AIがA/Bテストバリアント生成 → TestFlightに自動デプロイ → 48時間計測 → 自動ロールバック |
| V4 | 12ヶ月+ | 低リスク変更は本番自動デプロイ（Paywall最適化、Nudgeコンテンツ等） |

**Phase 1でDB保存の土台だけ用意しておく**: 将来AIが過去データを分析するために必要。
フォーマット: `.github/metrics/YYYY-MM-DD.json` にGitHub Actionsのartifactとして保存。

## 受け入れ条件

| # | 条件 | テスト可能か |
|---|------|-------------|
| 1 | 毎朝5:15 JSTにSlack通知が届く | YES: GH Actions実行ログ確認 |
| 2 | MRR・アクティブサブスク数が含まれる | YES: Slack投稿内容確認 |
| 3 | DL数（国別・7日間合計）が含まれる | YES: 同上 |
| 4 | CVR（ページ閲覧→DL）が含まれる | YES: 同上 |
| 5 | Trial→Paid転換率が含まれる | YES: 同上 |
| 6 | 月次チャーン率が含まれる | YES: 同上 |
| 7 | 前日比が表示される | YES: 同上 |
| 8 | エラー時はSlackにエラー通知が届く | YES: 意図的にAPIキー無効化して確認 |
| 9 | 1つのAPI失敗でも他のデータは送信される | YES: 部分障害テスト |

## ユーザーGUI作業（実装前に必須）

| # | タスク | 手順 | 取得するもの | 所要時間 |
|---|--------|------|-------------|---------|
| 1 | **Slack Webhook URL取得** | https://api.slack.com/apps → Create New App → From scratch → App名: `Anicca Metrics Bot` → ワークスペース選択 → 左メニュー「Incoming Webhooks」→ Activate On → 「Add New Webhook to Workspace」→ チャンネル `#anicca-metrics` 選択 → **Webhook URLをコピー** | Webhook URL | 2分 |
| 2 | **ASC API Key取得** | https://appstoreconnect.apple.com → Users and Access → Integrations → App Store Connect API → 「+」Generate API Key → Name: `Metrics Bot` → Access: `App Manager` → **Key IDとIssuer IDをメモ** → **.p8ファイルをDL**（1回しかDLできない） | Key ID, Issuer ID, .p8ファイル | 3分 |
| 3 | **RevenueCat Secret Key取得** | RevenueCat Dashboard → Project Settings → API Keys → 「+ New」→ Secret API key (v2) → **キーをコピー** | Secret API Key | 1分 |

**合計: 約5-10分。** 値を取得したらチャットに貼る → エージェントが `gh secret set` でGitHub Secretsに登録。

**注意:**
- ASC_PRIVATE_KEYは.p8ファイルの中身を改行→`\n`に変換して1行にする
- Railway環境変数は**不要**（GitHub Secretsのみ使用）
- ASA（Apple Search Ads）はPhase 2で追加

## As-Is / To-Be

### As-Is

```
毎日手動で2つのダッシュボードを確認:
- App Store Connect → DL数、インプレッション、CVR
- RevenueCat → MRR、トライアル、チャーン
→ 忘れる、遅れる、因果関係追跡できない
```

### To-Be

```
GitHub Actions Cron ('15 20 * * *' UTC = 5:15 JST)
    ↓
.github/workflows/daily-metrics.yml
    → scripts/daily-metrics/main.py
    ↓ 並列API呼び出し
    ├── App Store Connect API → DL数(国別)、インプレッション、CVR
    └── RevenueCat API v2 → MRR、Trial→Paid、チャーン率、アクティブサブスク
    ↓
Slack Webhook POST (Block Kit format)
    ↓
#anicca-metrics チャンネルに投稿
    ↓
(オプション) .github/metrics/YYYY-MM-DD.json にartifact保存
```

### Slack通知フォーマット

```
📊 Anicca Daily Report (2026-01-28)

💰 REVENUE
  MRR: $149.85 (+$9.99)
  Active Subs: 15 (+1)
  Trial→Paid: 1/3 (33%)
  Monthly Churn: 6.7%

📥 INSTALLS (7日間)
  合計: 12 (目標: 70)
  US: 5 | JP: 4 | EU: 3
  CVR (閲覧→DL): 1.8% (目標: 3%)

📈 FUNNEL
  Imp → Page View → DL
  900/日 → 13 (1.4%) → 2 (15%)

⚠️ ALERTS
  - CVR 1.8% → 目標3%に未達
  - 7日間インストール12 → 目標70に未達
```

**エラー時:**

```
🚨 Anicca Metrics Error (2026-01-28)

❌ App Store Connect API: 認証エラー (401)
✅ RevenueCat API: 正常

取得できたデータのみ送信しました。
ASC API Keyの有効期限を確認してください。
```

### ファイル構成

```
.github/
├── workflows/
│   └── daily-metrics.yml        ← GitHub Actions workflow
scripts/
└── daily-metrics/
    ├── main.py                  ← メインスクリプト
    ├── asc_client.py            ← App Store Connect API
    ├── revenuecat_client.py     ← RevenueCat API v2
    ├── slack_sender.py          ← Slack Webhook送信（Block Kit）
    ├── models.py                ← データモデル
    ├── requirements.txt         ← Python依存関係
    └── tests/
        ├── test_asc_client.py
        ├── test_revenuecat_client.py
        ├── test_slack_sender.py
        └── test_main.py
```

### GitHub Secrets（エージェントが `gh secret set` で登録）

| Secret Name | 用途 |
|-------------|------|
| `SLACK_METRICS_WEBHOOK_URL` | Slack通知先 |
| `ASC_KEY_ID` | App Store Connect API Key ID |
| `ASC_ISSUER_ID` | App Store Connect API Issuer ID |
| `ASC_PRIVATE_KEY` | App Store Connect API .p8ファイル内容 |
| `REVENUECAT_V2_SECRET_KEY` | RevenueCat API v2 Secret Key |

## テストマトリックス

| # | To-Be | テスト名 | カバー |
|---|-------|----------|--------|
| 1 | ASC APIからDL数・CVR取得 | `test_fetch_app_store_metrics()` | ✅ |
| 2 | RevenueCat APIからMRR・Trial・チャーン取得 | `test_fetch_revenuecat_metrics()` | ✅ |
| 3 | Slack Block Kit フォーマット生成 | `test_format_slack_message()` | ✅ |
| 4 | 前日比計算 | `test_calculate_day_over_day()` | ✅ |
| 5 | アラート条件判定（CVR < 3%, DL < 10/日） | `test_alert_conditions()` | ✅ |
| 6 | API エラー時のフォールバック（部分送信） | `test_api_error_handling()` | ✅ |
| 7 | Trial→Paid転換率計算 | `test_trial_to_paid_conversion()` | ✅ |
| 8 | 月次チャーン率計算 | `test_monthly_churn_rate()` | ✅ |

## 境界

### やること
- 2つのAPIからメトリクス取得（ASC + RevenueCat）
- Slackに日次レポート送信（Block Kit format）
- 前日比の計算
- アラート条件判定
- エラーハンドリング（1つのAPI失敗でも他は送信）
- メトリクスJSONをGitHub Actions artifactとして保存（将来AI分析用）

### やらないこと
- ダッシュボードUI作成
- ASA（Apple Search Ads）連携（Phase 2）
- Mixpanel連携（Phase 2）
- メトリクスのDB保存（Phase 2、artifactで代替）
- 自動Bid調整（Phase 2）
- A/Bテスト自動判定（Phase 2）
- AI分析・改善提案（Phase 2）

### 触るファイル
- `.github/workflows/daily-metrics.yml`（新規作成）
- `scripts/daily-metrics/`（新規ディレクトリ）

### 触らないファイル
- `apps/api/`（APIサーバーに一切変更なし）
- `aniccaios/`（iOSアプリに変更なし）
- 既存のGitHub Actions workflows

## 実行手順

```bash
# 開発・テスト
cd scripts/daily-metrics && pip install -r requirements.txt && pytest tests/

# 手動実行（テスト用）
cd scripts/daily-metrics && python main.py

# GitHub Actions手動トリガー（workflow_dispatch）
gh workflow run daily-metrics.yml

# GitHub Secrets登録（エージェントが実行）
echo "VALUE" | gh secret set SECRET_NAME --repo Daisuke134/anicca.ai
```

## 技術決定ログ

| 決定 | 選択 | 却下した選択肢 | 理由 |
|------|------|---------------|------|
| 実行環境 | GitHub Actions | Railway Cron, Cloudflare Workers, AWS Lambda, VPS, Lindy AI, Clawd.bot | DB不要・$0・既存実績・TikTok系と統一 |
| 言語 | Python | TypeScript | TikTok系と統一。ASC APIのPythonライブラリが豊富 |
| スケジュール | `'15 20 * * *'` (5:15 JST) | `:00` 指定 | GH Actionsは毎時:00に混雑。:15で信頼性向上 |
| Phase 1 指標 | MRR, DL, CVR, Trial→Paid, チャーン, Active Subs | ASA, DAU, オンボ完了率 | コアKPIに集中。Phase 2で拡張 |
| Slack形式 | Block Kit | プレーンテキスト | 色分け・セクション分け・リッチ表示 |
| データ保存 | GitHub Actions artifact (JSON) | DB保存 | Phase 1は表示+保存。DB保存はPhase 2 |
