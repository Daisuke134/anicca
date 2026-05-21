# OpenClaw実装仕様書

**作成日**: 2026-02-05
**ステータス**: ✅ 承認済み (Iteration 5)
**親Spec**: `spec-mixpanel-openclaw-onboarding-paywall.md` (Patch C/D)

---

## 開発環境

| 項目 | 値 |
|------|-----|
| **デプロイ先** | Phase 1: ローカルMac（テスト）→ Phase 2: Hetzner VPS（本番） |
| **OpenClaw バージョン** | 2026.2.2-3 |
| **ベースブランチ** | `dev` |

---

## 概要（What & Why）

### What
OpenClawをローカルMacにセットアップし、以下の自動化を実現:
1. 毎朝9:00 JSTに#metricsチャンネルへ日次メトリクス投稿
2. @Aniccaメンションへのリアルタイム応答（#metricsチャンネルのみ）
3. 日曜21:00と月曜11:25のミーティングリマインダー

### Why
- GitHub Actions (`daily-metrics.yml`) からOpenClawへ移行し、より柔軟なスケジュール管理
- Slackでのインタラクティブなメトリクス照会を可能に
- 手動だったリマインダーを自動化

### 親Specとの関係

親Spec (Patch C/D) は「設計仕様のみ。詳細実装はVPSセットアップ時に確定」としている。本Specは**ローカルMacでのテスト実装**として、親Specの設計を具体化する。本番VPSデプロイ時は別途実装Specを作成する。

---

## 受け入れ条件

| # | 条件 | テスト方法 | 期待結果 |
|---|------|-----------|---------|
| AC-1 | OpenClaw gatewayが起動する | `openclaw gateway status` | `running` と表示 |
| AC-2 | Slack接続が成功する | `openclaw channels test slack` | `connected` と表示 |
| AC-3 | DMに返信できる | SlackでDM送信「hello」 | Aniccaから返信が来る（デフォルトエージェントが応答） |
| AC-4 | #metricsに投稿できる | `openclaw cron test daily-metrics-reporter` | #metricsにメトリクスが投稿される |
| AC-5 | #metricsでの@Aniccaメンションに応答する | `@Anicca 昨日のトライアル数は？` | スレッド返信でデータが表示される |
| AC-6 | 日曜リマインダー動作 | `openclaw cron test sunday-reminder` | リマインダーが投稿される |
| AC-7 | 月曜リマインダー動作 | `openclaw cron test monday-reminder` | リマインダーが投稿される |

---

## As-Is / To-Be

### As-Is（現状）

| 機能 | 現状 |
|------|------|
| 日次メトリクス | GitHub Actions `daily-metrics.yml` (5:15 JST) |
| @Aniccaメンション応答 | なし |
| ミーティングリマインダー | 手動投稿 |

### To-Be（変更後）

| 機能 | 変更後 |
|------|--------|
| 日次メトリクス | OpenClaw `daily-metrics-reporter` skill (9:00 JST) |
| @Aniccaメンション応答 | OpenClaw `slack-mention-handler` skill (#metricsのみ) |
| ミーティングリマインダー | OpenClaw cron (日曜21:00 JST, 月曜11:25 JST) |

---

## 環境変数・認証情報

### 必要な環境変数

| 変数名 | 取得元 | 用途 |
|--------|--------|------|
| `SLACK_BOT_TOKEN` | プロジェクト `.env` ファイル | Slack Bot操作 |
| `SLACK_APP_TOKEN` | プロジェクト `.env` ファイル | Socket Mode |
| `OPENAI_API_KEY` | Railway Staging環境変数 | AIモデル |

> **セキュリティ注意**: 実際のトークン値はSpecファイルに記載しない。`.env`ファイル（gitignored）または環境変数から取得する。

### 固定値

| 項目 | 値 |
|------|-----|
| `MIXPANEL_PROJECT_ID` | `3970220` |
| `REVENUECAT_PROJECT_ID` | `projbb7b9d1b` |
| `SLACK_METRICS_CHANNEL_ID` | `C091G3PKHL2` |

---

## 設定ファイル構造

### ファイル: `~/.openclaw/openclaw.json`

設定ファイルの構造を示す。実際のトークン値は環境変数から注入する。

```json
{
  "gateway": {
    "mode": "local",
    "port": 18789,
    "bind": "loopback",
    "auth": {
      "mode": "token"
    },
    "controlUi": {
      "enabled": true
    }
  },
  "channels": {
    "slack": {
      "enabled": true,
      "botToken": "${SLACK_BOT_TOKEN}",
      "appToken": "${SLACK_APP_TOKEN}",
      "dm": {
        "enabled": true,
        "policy": "open",
        "allowFrom": ["*"]
      },
      "channels": {
        "C091G3PKHL2": {
          "allow": true,
          "requireMention": false
        }
      },
      "historyLimit": 50,
      "allowBots": false,
      "actions": {
        "reactions": true,
        "messages": true
      }
    }
  },
  "agents": {
    "defaults": {
      "workspace": "/Users/cbns03/Downloads/anicca-project",
      "userTimezone": "Asia/Tokyo",
      "timeFormat": "24",
      "model": {
        "primary": "openai/gpt-4o"
      }
    },
    "list": [
      {
        "id": "anicca",
        "default": true,
        "name": "Anicca Bot",
        "workspace": "/Users/cbns03/Downloads/anicca-project",
        "identity": {
          "name": "Anicca",
          "emoji": "🧘"
        }
      }
    ]
  },
  "cron": {
    "enabled": true,
    "maxConcurrentRuns": 2
  }
}
```

---

## Skill 1: daily-metrics-reporter

### 要件

| 項目 | 値 |
|------|-----|
| **実行タイミング** | 毎朝9:00 JST |
| **cron式** | `0 9 * * *` (timezone: Asia/Tokyo) |
| **投稿先** | Slack #metrics (C091G3PKHL2) |

### データ取得元

| データ | 取得方法 | エンドポイント/ツール |
|--------|---------|---------------------|
| MRR, Active Subs, Trials | RevenueCat REST API v2 | `GET https://api.revenuecat.com/v2/projects/projbb7b9d1b/metrics/overview` |
| ファネルイベントカウント | Mixpanel Segmentation Query | `mcp__mixpanel__run_segmentation_query` |
| インストール数 | Mixpanel `first_app_opened` | `mcp__mixpanel__run_segmentation_query` |

### RevenueCat REST API v2 詳細

| 項目 | 値 |
|------|-----|
| **エンドポイント** | `https://api.revenuecat.com/v2/projects/{project_id}/metrics/overview` |
| **認証** | `Authorization: Bearer {REVENUECAT_V2_SECRET_KEY}` |
| **REVENUECAT_V2_SECRET_KEY** | GitHub Secretsに登録済み（sk_で始まる） |

**レスポンス例:**
```json
{
  "metrics": [
    {"id": "mrr", "name": "MRR", "value": 16, "unit": "USD"},
    {"id": "active_subscriptions", "name": "Active Subscriptions", "value": 5},
    {"id": "active_trials", "name": "Active Trials", "value": 2}
  ]
}
```

> **注意**: RevenueCat MCPの`list_offerings`はOffering構成を返すAPIであり、MRR等のメトリクスは返さない。メトリクス取得にはRevenueCat REST API v2を直接呼び出す。

> **ASCダウンロード数について**: 親SpecではASCダウンロード数を含めるとしているが、ASC Sales Reports APIは複雑な認証と日次バッチ処理が必要。1.6.1ではMixpanelの`first_app_opened`イベントで初回インストール数を代替する。正確なASCダウンロード数は1.7.0で対応予定。

### SKILL.md ファイル内容

ファイルパス: `~/.openclaw/skills/daily-metrics-reporter/SKILL.md`

```markdown
---
name: daily-metrics-reporter
description: 毎朝Anicca日次メトリクスをSlack #metricsに投稿
metadata: {"openclaw":{"requires":{"env":["OPENAI_API_KEY","REVENUECAT_V2_SECRET_KEY"],"mcp":["mixpanel"]}}}
---

## Instructions

あなたはAniccaプロジェクトの日次メトリクスレポーターです。

### タスク
1. RevenueCat REST API v2からMRR、アクティブサブスク、アクティブトライアルを取得
2. Mixpanel MCPから過去7日間のファネルイベントを取得
3. 結果をフォーマットしてSlack #metricsに投稿

### RevenueCat API呼び出し

\`\`\`bash
curl -X GET "https://api.revenuecat.com/v2/projects/projbb7b9d1b/metrics/overview" \
  -H "Authorization: Bearer $REVENUECAT_V2_SECRET_KEY"
\`\`\`

### Mixpanelクエリ

以下のイベントを`run_segmentation_query`で取得（過去7日間）:
- `onboarding_started`
- `onboarding_welcome_completed`
- `onboarding_value_completed`
- `onboarding_struggles_completed`
- `onboarding_notifications_completed`
- `onboarding_paywall_viewed`
- `rc_trial_started_event`
- `first_app_opened`

### 出力フォーマット

以下のフォーマットでSlackに投稿:

📊 Anicca Daily Metrics ({date})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 REVENUE (RevenueCat)
  MRR: ${mrr}
  Active Subs: {active_subs}
  Active Trials: {active_trials}

📥 INSTALLS (過去7日)
  first_app_opened: {count}

🔄 ONBOARDING FUNNEL (過去7日)
  期間: {start_date} 〜 {end_date}
  onboarding_started:           {count} (100.0%)
  onboarding_welcome_completed: {count} ({rate}%)
  onboarding_value_completed:   {count} ({rate}%)
  onboarding_struggles_completed: {count} ({rate}%)
  onboarding_notifications_completed: {count} ({rate}%)
  onboarding_paywall_viewed:    {count} ({rate}%)
  rc_trial_started_event:       {count} ({rate}%) ← ★要改善

📈 WEEK OVER WEEK
  Trial Starts: {last_week} → {this_week} ({change}%)
  Paywall Views: {last_week} → {this_week} ({change}%)

⚠️ ALERTS
  {alerts_if_any}

### 投稿先
Slack #metrics (C091G3PKHL2)
\`\`\`

---

## Skill 2: slack-mention-handler

### 要件

| 項目 | 値 |
|------|-----|
| **トリガー** | Slack `app_mention` イベント |
| **対応チャンネル** | #metrics (C091G3PKHL2) のみ |
| **応答形式** | スレッド返信 |

> **チャンネル制限の理由**: 全チャンネルでの応答は`openclaw.json`のchannels設定と矛盾するため、#metricsのみに限定する。他チャンネルでの応答が必要な場合は設定を拡張する。

### 対応クエリパターン

| ユーザー入力例 | アクション | 使用API |
|---------------|-----------|---------|
| 「昨日のPaywall変換率は？」 | Mixpanelで昨日のfunnel取得 | Mixpanel MCP |
| 「今週のトライアル数は？」 | Mixpanelで過去7日のrc_trial_started_event | Mixpanel MCP |
| 「MRRは？」 | RevenueCat REST APIでMRR取得 | HTTP直接 |
| 「ダウンロード数は？」 | Mixpanelでfirst_app_opened取得 | Mixpanel MCP |
| 「hello」「テスト」 | 挨拶で応答 | なし |

### SKILL.md ファイル内容

ファイルパス: `~/.openclaw/skills/slack-mention-handler/SKILL.md`

```markdown
---
name: slack-mention-handler
description: Slack #metricsでの@Aniccaメンションに応答してメトリクスを返す
metadata: {"openclaw":{"requires":{"env":["OPENAI_API_KEY","REVENUECAT_V2_SECRET_KEY"],"mcp":["mixpanel"]},"triggers":[{"type":"slack_mention","channels":["C091G3PKHL2"]}]}}
---

## Instructions

あなたはAniccaプロジェクトのメトリクスアシスタントです。
Slack #metricsチャンネルでメンションされたら、クエリを解析して適切なデータを返します。

### 対応クエリ

1. **トライアル関連**
   - 「トライアル数は？」「昨日のトライアル」
   - → Mixpanel `rc_trial_started_event` を取得

2. **MRR関連**
   - 「MRRは？」「売上は？」
   - → RevenueCat REST API v2でMRRを取得

3. **ファネル関連**
   - 「変換率は？」「Paywall」「オンボーディング」
   - → Mixpanel ファネルイベントを取得

4. **インストール関連**
   - 「ダウンロード数」「インストール」
   - → Mixpanel `first_app_opened` を取得

5. **挨拶**
   - 「hello」「テスト」
   - → 簡単な挨拶で応答

### RevenueCat API呼び出し

\`\`\`bash
curl -X GET "https://api.revenuecat.com/v2/projects/projbb7b9d1b/metrics/overview" \
  -H "Authorization: Bearer $REVENUECAT_V2_SECRET_KEY"
\`\`\`

### Mixpanelクエリ

project_id: 3970220 で `run_segmentation_query` を使用。

### 応答フォーマット

- 簡潔に、要点のみ
- 絵文字を使って視覚的に
- スレッド返信で応答
\`\`\`

### 応答例

**クエリ:** `@Anicca 昨日のトライアル数は？`

**応答:**
```
📊 昨日 (2026-02-04) のトライアル開始数:

rc_trial_started_event: 0件

過去7日間: 0件
過去30日間: 1件
```

---

## Cron ジョブ設定

### ジョブ一覧

| ジョブ名 | cron式 | timezone | 実行時刻 |
|---------|--------|----------|---------|
| `daily-metrics-reporter` | `0 9 * * *` | Asia/Tokyo | 毎朝9:00 JST |
| `sunday-reminder` | `0 21 * * 0` | Asia/Tokyo | 日曜21:00 JST |
| `monday-reminder` | `25 11 * * 1` | Asia/Tokyo | 月曜11:25 JST |

> **タイムゾーン統一**: すべてのcronジョブはAsia/Tokyoタイムゾーンで設定する（UTC変換しない）。

### リマインダー内容

**日曜21:00:**
```
📅 明日の予定リマインダー

明日は月曜日です。
12:00からラボミーティングがあります。
準備をお忘れなく。
```

**月曜11:25:**
```
📢 ミーティングリマインダー

12:00からのラボミーティングまであと35分です。
出席できない方は事前にご連絡ください。
```

---

## 実行手順

### ユーザー作業（実装前）

| # | タスク | 手順 | 取得するもの |
|---|--------|------|-------------|
| 1 | RevenueCat Secret Key確認 | RevenueCat Dashboard → Project Settings → API Keys → Secret API keys | `sk_`で始まるキー（GitHub Secretsに登録済み） |
| 2 | OPENAI_API_KEY取得 | Railway Dashboard → Staging → API → Variables | `sk-proj-`で始まるキー |

> **注意**: REVENUECAT_V2_SECRET_KEY, OPENAI_API_KEY は既にRailway/GitHub Secretsに登録済み。エージェントがMCP経由で取得してローカル環境変数に設定する。

### Step 1: 環境変数を設定

```bash
# .env から読み込み、OpenClaw設定に注入
source /Users/cbns03/Downloads/anicca-project/.env
openclaw config set channels.slack.botToken "$SLACK_BOT_TOKEN"
openclaw config set channels.slack.appToken "$SLACK_APP_TOKEN"

# OpenAI API Key（Railway環境変数から取得した値を使用）
openclaw config set agents.defaults.apiKeys.openai "$OPENAI_API_KEY"

# RevenueCat API Key（GitHub Secretsから取得）
# REVENUECAT_V2_SECRET_KEY は sk_ で始まるシークレットキー
export REVENUECAT_V2_SECRET_KEY="取得したシークレットキー"
```

> **REVENUECAT_V2_SECRET_KEY 取得方法**: RevenueCat Dashboard → Project Settings → API Keys → Secret API keys → sk_で始まるキーをコピー

### Step 2: Skillディレクトリ作成

```bash
mkdir -p ~/.openclaw/skills/daily-metrics-reporter
mkdir -p ~/.openclaw/skills/slack-mention-handler
```

### Step 3: SKILL.mdファイル作成

本Specの「Skill 1」「Skill 2」セクションの内容を各ディレクトリにSKILL.mdとして保存。

### Step 4: Gateway起動

```bash
openclaw gateway start
```

### Step 5: 接続テスト

```bash
openclaw gateway status
openclaw channels test slack
```

### Step 6: Cronジョブ登録

> **CLIオプション (確認済み)**: `openclaw cron add --help` で確認
> - `--cron <expr>`: 5フィールドcron式
> - `--tz <iana>`: タイムゾーン (IANA形式)
> - `--message <text>`: エージェントへのメッセージ
> - `--channel <channel>`: 配信チャンネル
> - `--to <dest>`: 配信先

```bash
# 日次メトリクス (9:00 JST)
openclaw cron add daily-metrics-reporter \
  --cron "0 9 * * *" \
  --tz "Asia/Tokyo" \
  --message "daily-metrics-reporterスキルを実行して#metricsに投稿してください" \
  --channel slack \
  --to channel:C091G3PKHL2

# 日曜リマインダー (21:00 JST)
openclaw cron add sunday-reminder \
  --cron "0 21 * * 0" \
  --tz "Asia/Tokyo" \
  --message "📅 明日の予定リマインダー\n\n明日は月曜日です。\n12:00からラボミーティングがあります。\n準備をお忘れなく。" \
  --channel slack \
  --to channel:C091G3PKHL2

# 月曜リマインダー (11:25 JST)
openclaw cron add monday-reminder \
  --cron "25 11 * * 1" \
  --tz "Asia/Tokyo" \
  --message "📢 ミーティングリマインダー\n\n12:00からのラボミーティングまであと35分です。\n出席できない方は事前にご連絡ください。" \
  --channel slack \
  --to channel:C091G3PKHL2
```

### Step 7: 動作テスト

```bash
# 日次メトリクス即時実行
openclaw cron test daily-metrics-reporter

# 日曜リマインダー即時実行
openclaw cron test sunday-reminder

# 月曜リマインダー即時実行
openclaw cron test monday-reminder
```

### Step 8: Slackでインタラクティブテスト

1. #metricsチャンネルで `@Anicca hello` を送信 → 応答確認
2. #metricsチャンネルで `@Anicca MRRは？` を送信 → データ返答確認

---

## テストマトリックス

| # | To-Be | テスト名 | 方法 | 種別 |
|---|-------|---------|------|------|
| 1 | Gateway起動 | `test_gateway_start` | `openclaw gateway status` | CLI |
| 2 | Slack接続 | `test_slack_connection` | `openclaw channels test slack` | CLI |
| 3 | DM応答 | `test_dm_response` | DMで「hello」送信 | 手動 |
| 4 | 日次メトリクス投稿 | `test_daily_metrics` | `openclaw cron test daily-metrics-reporter` | CLI |
| 5 | #metricsでメンション応答 | `test_mention_response` | #metricsで`@Anicca test` | 手動 |
| 6 | MRRクエリ | `test_mrr_query` | #metricsで`@Anicca MRRは？` | 手動 |
| 7 | トライアルクエリ | `test_trial_query` | #metricsで`@Anicca トライアル数は？` | 手動 |
| 8 | 日曜リマインダー | `test_sunday_reminder` | `openclaw cron test sunday-reminder` | CLI |
| 9 | 月曜リマインダー | `test_monday_reminder` | `openclaw cron test monday-reminder` | CLI |

> **テスト種別**: CLI = コマンド実行で自動確認可能, 手動 = Slack UIで確認が必要

---

## 境界（やらないこと）

| やらないこと | 理由 |
|-------------|------|
| Hetzner VPSへのデプロイ | Phase 2で実施。別途実装Spec作成 |
| GitHub Actions `daily-metrics.yml` の削除 | OpenClaw 1週間安定稼働確認後 |
| カスタムTypeScript実装 | OpenClaw標準機能で実現 |
| ASC Sales Reports API直接呼び出し | 複雑な認証・バッチ処理が必要。1.7.0で対応予定。Mixpanel `first_app_opened` で代替 |
| #metrics以外でのメンション応答 | channels設定との整合性維持。必要時は設定拡張 |

---

## E2E判定

| 項目 | 値 |
|------|-----|
| UI変更 | なし（バックエンドのみ） |
| 新画面 | なし |
| 新ボタン | なし |
| 結論 | **Maestro E2E不要** |

---

## 移行完了後のクリーンアップ

OpenClaw動作確認後（1週間安定稼働を確認後）:

1. `.github/workflows/daily-metrics.yml` を無効化
2. GitHub Actions の TikTok/X 投稿も必要に応じてOpenClawに移行検討

---

## リスクと対策

| リスク | 対策 |
|--------|------|
| Mac再起動でGateway停止 | `launchd` でデーモン化、または Hetzner VPS移行 |
| API Rate Limit | クエリ間隔を調整、キャッシュ活用 |
| Slackトークン失効 | 定期的な再認証、エラー通知設定 |

---

## 参考リンク

- [OpenClaw Docs](https://docs.openclaw.ai)
- [親Spec: spec-mixpanel-openclaw-onboarding-paywall.md](./spec-mixpanel-openclaw-onboarding-paywall.md)
- [Mixpanel Project](https://mixpanel.com/project/3970220)
- [RevenueCat Project](https://app.revenuecat.com/projects/projbb7b9d1b)
