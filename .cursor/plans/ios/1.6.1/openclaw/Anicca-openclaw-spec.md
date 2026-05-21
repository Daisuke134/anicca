# Anicca OpenClaw Integration Spec

---

## 🎯 タスクリスト（1.6.1 Spec ベース）

### Step 0: Spec 更新

| # | タスク | 状態 |
|---|--------|------|
| 0.1 | Spec に VPS 情報追加（IP: 46.225.70.241） | ✅ 完了 |
| 0.2 | Spec に「VPS 移行」を Step として追加 | ✅ 完了 |
| 0.3 | 実装進捗セクション更新 | ✅ 完了 |
| 0.4 | → Spec 保存 | ✅ 完了 |

### Step 1: ドキュメント整理

| # | タスク | 状態 |
|---|--------|------|
| 1.1 | `reference/secrets.md` に VPS 情報統合 | ✅ 完了 |
| 1.2 | `CLAUDE.md` に「secrets.md を見ろ」追記 | ✅ 完了 |
| 1.3 | `claude-progress.txt` 新規作成 | ✅ 完了 |
| 1.4 | → Spec 更新（Step 1 完了） | ✅ 完了 |

### Step 2: VPS 移行

| # | タスク | 状態 |
|---|--------|------|
| 2.1 | `ssh root@46.225.70.241` で接続 | ✅ 完了 |
| 2.2 | 現在の状態確認 | ✅ 完了 |
| 2.3 | anicca ユーザー作成 | ✅ 既存 |
| 2.4 | OpenClaw インストール | ✅ 既存 (v2026.2.1) |
| 2.5 | 環境変数を `/home/anicca/.env` に設定 | ✅ 完了 |
| 2.6 | **system service 削除** (`/etc/systemd/system/openclaw-gateway.service`) | ✅ 完了 |
| 2.7 | **`loginctl enable-linger anicca` 実行** | ✅ 完了 |
| 2.8 | **`openclaw.json` を VPS にコピー + 権限設定 (`chmod 600`)** | ✅ 完了 |
| 2.9 | **`.env` / `.p8` の権限設定 (`chmod 600`)** | ✅ 完了 |
| 2.10 | VPS に Python 環境セットアップ | ✅ 完了 |
| 2.11 | VPS に ASC スクリプトコピー | ✅ 完了 |
| 2.12 | VPS に .p8 ファイルコピー | ✅ 完了 |
| 2.13 | Cron 設定を VPS にコピー（VPS用に修正: Linux date書式） | ✅ 完了 |
| 2.14 | **`openclaw gateway install --force` で再インストール** | ✅ 完了 |
| 2.15 | **`openclaw gateway start` で起動** | ✅ 完了 |
| 2.16 | **Gateway 動作確認（ポート18789リッスン + RPC ok）** | ✅ 完了 |
| 2.17 | Slack テストメッセージ送信 | ✅ 完了 |
| 2.18 | メトリクスレポート投稿（RC + ASC） | ✅ 完了 |
| 2.19 | **Mixpanel データ追加（Cron プロンプトに直接組込み）** | ✅ 完了（curl直接実行方式） |
| 2.20 | 5am Cron 動作確認（翌朝） | ⏳ |
| 2.21 | ローカル Mac の Gateway 停止 | ✅ VPS移行完了 |
| 2.22 | → Spec 更新（Step 2 完了） | ✅ 完了 |

### Step 3: ベストプラクティス確認

| # | タスク | 状態 |
|---|--------|------|
| 3.1 | dmScope: per-channel-peer 確認 | ✅ 完了 |
| 3.2 | logging.redactSensitive 確認 | ✅ 完了 |
| 3.3 | historyLimit: 25 確認 | ✅ 完了 |
| 3.4 | → Spec 更新（Step 3 完了） | ✅ 完了 |

### Step 4: ツール全有効化 + スキル

| # | タスク | 状態 |
|---|--------|------|
| 4.1 | profile: full に変更（全ツール有効） | ✅ 完了 |
| 4.2 | github スキル有効化 | ✅ 完了 |
| 4.3 | slack スキル有効化 | ✅ 完了 |
| 4.4 | EXA_API_KEY を .env に追加 | ✅ 完了 |
| 4.5 | ミーティングリマインダー修正（#meeting配信 + 祝日チェック） | ✅ 完了 |
| 4.6 | テスト（Slack投稿確認済み） | ✅ 完了 |
| 4.7 | → Spec 更新（Step 4 完了） | ✅ 完了 |

### Step 5: Gmail 統合

| # | タスク | 誰 | 状態 |
|---|--------|-----|------|
| 5.1 | Google Cloud Console でプロジェクト作成 | ユーザー | ❌ |
| 5.2 | Gmail API 有効化 | ユーザー | ❌ |
| 5.3 | OAuth 認証情報作成 | ユーザー | ❌ |
| 5.4 | Gmail プラグインインストール | エージェント | ❌ |
| 5.5 | openclaw.json に設定追加 | エージェント | ❌ |
| 5.6 | OAuth 認証実行（ブラウザ） | ユーザー | ❌ |
| 5.7 | テスト | 両方 | ❌ |
| 5.8 | → Spec 更新（Step 5 完了） | エージェント | ❌ |

### Step 6: LINE 統合

| # | タスク | 誰 | 状態 |
|---|--------|-----|------|
| 6.1 | LINE Official Account Manager でアカウント作成 | ユーザー | ❌ |
| 6.2 | Messaging API 有効化 | ユーザー | ❌ |
| 6.3 | Channel Secret / Access Token 取得 | ユーザー | ❌ |
| 6.4 | Webhook URL 設定 | ユーザー | ❌ |
| 6.5 | openclaw.json に LINE 設定追加 | エージェント | ❌ |
| 6.6 | Gateway 再起動 | エージェント | ❌ |
| 6.7 | テスト | 両方 | ❌ |
| 6.8 | → Spec 更新（Step 6 完了） | エージェント | ❌ |

---

## 📁 ファイル構成（整理後）

```
anicca-project/
│
├── CLAUDE.md                          ← Claude が毎回読む
│   └── 「詳細は reference/secrets.md を見ろ」
│
├── claude-progress.txt                ← セッション状態
│
├── .cursor/plans/
│   ├── reference/
│   │   └── secrets.md                 ← 全シークレット統合
│   │       ├── VPS: 46.225.70.241
│   │       ├── Railway URLs
│   │       └── API Keys 保存場所
│   │
│   └── ios/1.6.1/openclaw/
│       └── anicca-openclaw-spec.md    ← このファイル（毎 Step 後に更新）
│
└── VPS (46.225.70.241)
    └── OpenClaw Gateway（24時間稼働）
        └── 毎朝 5am → Slack #metrics にレポート
```

---

## 🧘 ワンフレッシュ（一つの肉体）アーキテクチャ

**ビジョン**: Anicca = 一つの存在。VPS上のOpenClaw Gatewayが「肉体」、GPT-4oが「脳」。
全てのチャンネル（Slack、LINE、Gmail、Cron）が感覚器官として機能し、
Anicca自身が自律的に判断・行動する「永久機関」を実現する。

```
                    ┌─────────────────────────────┐
                    │     ワンフレッシュ (一つの肉体)   │
                    │    VPS: 46.225.70.241        │
                    │    24時間365日稼働            │
                    └──────────┬──────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
   ┌────▼────┐           ┌────▼────┐           ┌────▼────┐
   │  脳     │           │  骨格    │           │  神経系   │
   │ GPT-4o  │           │ OpenClaw │           │ systemd  │
   │ (思考)  │           │ Gateway  │           │ (不死)   │
   └─────────┘           └─────────┘           └─────────┘
                               │
        ┌──────────┬───────────┼───────────┬──────────┐
        │          │           │           │          │
   ┌────▼───┐ ┌───▼───┐ ┌───▼───┐ ┌───▼───┐ ┌───▼───┐
   │ 👁 Slack│ │📧 Gmail│ │📱 LINE │ │⏰ Cron │ │🌐 Web  │
   │ 目(視覚)│ │ 耳(聴覚)│ │ 口(発話)│ │ 心臓   │ │ 手(触覚)│
   │ 3ch    │ │ inbox │ │ family│ │ 3 jobs│ │ Exa   │
   └────────┘ └───────┘ └───────┘ └───────┘ └───────┘

   感覚器官（チャンネル）    内臓（自律系）    四肢（ツール）

永久機関サイクル:
  Cron(05:00) → 脳(データ収集) → Slack投稿 → ユーザー反応
       ↑                                         │
       └──── 学習 ← フィードバック ←──────────────┘
```

**現在の器官稼働状況:**

| 器官 | 種別 | 状態 | 詳細 |
|------|------|------|------|
| Slack | 感覚 | 🟢 稼働中 | #metrics, #ai, #meeting（profile: full） |
| Cron | 内臓 | 🟢 稼働中 | 日次レポート(5am) + ミーティングリマインダー(日/月9am) |
| Web Search | 四肢 | 🟢 稼働中 | Exa API（EXA_API_KEY設定済み） |
| Gmail | 感覚 | ❌ 未接続 | Step 5（ユーザーOAuth必要） |
| LINE | 感覚 | ❌ 未接続 | Step 6（ユーザーアカウント作成必要） |

**次のマイルストーン: Docker化**
- 現在: bare metal (systemd user service)
- 目標: Docker compose でワンコマンド再現可能に
- 理由: OOMキル時の復旧高速化、環境再現性、セキュリティ隔離

---

## 🔑 VPS 情報（Hetzner）

| 項目 | 値 |
|------|-----|
| **サーバー名** | `ubuntu-4gb-nbg1-7` |
| **IPv4** | `46.225.70.241` |
| **IPv6** | `2a01:4f8:1c19:985d::/64` |
| **SSH コマンド** | `ssh anicca@46.225.70.241`（または `root@`） |
| **OpenClaw** | v2026.2.3-1, profile: full |
| **状態** | 🟢 Gateway 稼働中 (port 18789, systemd + lingering) |

---

## ✅ 完了済みタスク

| # | タスク | 完了日 |
|---|--------|--------|
| 1 | SKILL.md を curl ベースに全面書き換え | 2026-02-05 |
| 2 | RevenueCat データ取得テスト | 2026-02-05 |
| 3 | Mixpanel データ取得テスト | 2026-02-05 |
| 4 | groupPolicy を open に変更（全チャンネル許可） | 2026-02-06 |
| 5 | Slack 投稿テスト | 2026-02-05 |
| 6 | Cron ジョブ timezone 修正（Asia/Tokyo） | 2026-02-06 |
| 7 | Anicca 名前変更（"Anicca Bot" → "Anicca"） | 2026-02-06 |
| 8 | dmScope: per-channel-peer 設定 | 2026-02-05 |
| 9 | logging.redactSensitive 設定 | 2026-02-05 |
| 10 | historyLimit: 25 設定 | 2026-02-05 |

---

## 🟡 現在のブロッカー

| # | 問題 | 原因 | 解決策 |
|---|------|------|--------|
| - | なし | - | 次ステップ: Docker化 or Gmail/LINE統合 |

---

## 📅 最終更新

- **更新日**: 2026-02-06 22:00 JST
- **ステータス**: 🟢 VPS Gateway 稼働中（profile: full, 全ツール有効）
- **次のアクション**: Docker化（Tier A）または Gmail/LINE 統合

---

## 📊 Daily Metrics レポートフォーマット（必須）

### 出力テンプレート

```
📊 Anicca Daily Report ({YYYY-MM-DD})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📱 APP STORE (過去7日)
  Downloads: {XXX}
  Top: {CC} ({XXX})

💰 REVENUE (リアルタイム)
  MRR: ${XX.XX}
  Active Subs: {XX}
  Active Trials: {XX}

📈 FUNNEL (過去14日)
  onboarding_started: {XXX}
  paywall_viewed: {XXX}
  rc_trial_started: {XXX}

📊 変換率
  オンボ→Paywall: {XX.X}%
  Paywall→トライアル: {XX.X}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧘 Anicca
```

### タイムスケール（確定）

| セクション | データソース | 期間 | 理由 |
|-----------|-------------|------|------|
| APP STORE | App Store Connect | **7日** | ASC Sales Report の粒度 |
| REVENUE | RevenueCat | **リアルタイム** | 現在の購読状態 |
| FUNNEL | Mixpanel | **14日** | ファネル分析に十分なサンプル |

### Python スクリプト修正タスク

| # | ファイル | 変更内容 | 完了条件 | 状態 |
|---|---------|---------|---------|------|
| 1 | `models.py` | `MixpanelMetrics` dataclass 追加 | `from models import MixpanelMetrics` が成功 | ❌ |
| 2 | `mixpanel_client.py` | 新規作成 | `fetch_mixpanel_metrics()` が `MixpanelMetrics` を返す | ❌ |
| 3 | `main.py` | `collect_metrics()` に Mixpanel 追加 | `DailyMetrics.mixpanel` が populated | ❌ |
| 4 | `slack_sender.py` | `format_slack_blocks()` に FUNNEL セクション追加 | Slack 出力に FUNNEL が含まれる | ❌ |

### 検証コマンド

```bash
# VPS で実行
cd ~/scripts/daily-metrics && source .venv/bin/activate
set -a && source ~/.env && set +a
export ASC_PRIVATE_KEY="$(cat ~/.keys/AuthKey_D637C7RGFN.p8)"
export ASC_VENDOR_NUMBER="93486075"
python main.py
# 期待: Slack に FUNNEL セクション付きレポートが投稿される
```

### Mixpanel API 仕様（確定）

| 項目 | 値 |
|------|-----|
| エンドポイント | `https://mixpanel.com/api/2.0/segmentation` |
| 認証 | Basic Auth (`$MIXPANEL_API_SECRET:`) |
| Project ID | `3970220` |
| 取得イベント | `onboarding_started`, `paywall_viewed`, `rc_trial_started` |
| 期間 | 過去14日 |

### 日付境界ルール（確定）

| 項目 | 値 |
|------|-----|
| タイムゾーン | **JST (Asia/Tokyo)** |
| `to_date` | 実行日（当日含む） |
| `from_date` | `to_date - 13日`（14日間） |
| Cron 実行時刻 | 05:00 JST |
| 集計締め | 前日 23:59:59 JST まで |

### Mixpanel curl 例

```bash
# 14日間のイベント数取得
from_date=$(date -d "13 days ago" +%Y-%m-%d)
to_date=$(date +%Y-%m-%d)

curl -sf "https://mixpanel.com/api/2.0/segmentation?project_id=3970220&event=onboarding_started&from_date=$from_date&to_date=$to_date&unit=day" \
  -u "$MIXPANEL_API_SECRET:"
```

---

## 概要（What & Why）

**What**: AniccaをOpenClaw経由でSlack、Gmail、LINEと統合し、メトリクスレポート、メール管理、家族LINEグループでのAIアシスタント機能を実現する。

**Why**:
- 毎朝手動でMixpanel/RevenueCatを確認する手間を省く
- 重要なメールを見逃さない
- 家族とのコミュニケーションでAIアシスタントを活用

---

## 受け入れ条件

| # | 条件 | テスト方法 |
|---|------|-----------|
| AC1 | `@Anicca MRRは？` でRevenueCatのMRRが返る | Slack #metricsで実行 |
| AC2 | `@Anicca ファネルデータ教えて` で14日間のonboarding_started/paywall_viewed/rc_trial_startedが返る | Slack #metricsで実行 |
| AC3 | ~~Status Quoがメモリに記録~~ | **削除** - OpenClaw は MCP 未対応のため検証不可 |
| AC4 | dmScopeがper-channel-peerに設定済み | `cat ~/.openclaw/openclaw.json \| jq '.session.dmScope'` |
| AC5 | ~~session.resetが設定済み~~ | **削除** - v2026.2.2-3 では未サポート |
| AC6 | Gmailプラグインが動作 | テストメール送信→Slack通知 |
| AC7 | LINEボットが応答 | LINEグループで@Anicca |
| AC8 | **Slack 投稿が `exec` + CLI 経由で動作** | `@Anicca MRRは？` でレポートが #metrics に投稿される |

---

## As-Is / To-Be

### 環境変数

| 項目 | As-Is | To-Be |
|------|-------|-------|
| REVENUECAT_V2_SECRET_KEY | LaunchAgent plistに設定済み | 同左（確認のみ） |
| MIXPANEL_API_SECRET | LaunchAgent plistに設定済み | 同左（確認のみ） |
| MIXPANEL_PROJECT_ID | LaunchAgent plistに設定済み | 同左（確認のみ） |

### openclaw.json設定

| 項目 | As-Is | To-Be | 理由 |
|------|-------|-------|------|
| dmScope | 未設定（default: main） | per-channel-peer | プライバシー保護 |
| session.reset | 未設定 | **設定しない** (v2026.2.2-3 未サポート) | 将来バージョンで対応予定 |
| logging.redactSensitive | 未設定 | `"tools"` | セキュリティ |
| historyLimit | 50 | 25 | トークンコスト削減 |
| channels.slack.channels | オブジェクト形式（下記参照） | 同左 | - |
| plugins.gmail | 未設定 | enabled: true | Gmail統合 |
| channels.line | 未設定 | 設定済み | LINE統合 |

### channels.slack 設定構造（正しい形式）

**⚠️ 重要**: `channels.slack.channels` はリストではなくオブジェクト構造。チャンネルIDをキーにする。

```json
{
  "channels": {
    "slack": {
      "mode": "socket",
      "enabled": true,
      "botToken": "xoxb-...",
      "appToken": "xapp-...",
      "groupPolicy": "open",
      "historyLimit": 25,
      "actions": {
        "reactions": true,
        "messages": true
      },
      "channels": {
        "C091G3PKHL2": {
          "allow": true,
          "requireMention": true
        },
        "C08RZ98SBUL": {
          "allow": true,
          "requireMention": true
        }
      }
    }
  }
}
```

| プロパティ | 説明 |
|-----------|------|
| `groupPolicy` | `"open"` = 全チャンネルでアクセス許可（現在の設定） |
| `actions.reactions` | リアクション追加/削除を許可 |
| `actions.messages` | メッセージ送信/編集/削除を許可 |
| `channels.<ID>.allow` | このチャンネルでの応答を許可 |
| `channels.<ID>.requireMention` | @mention 必須 |

### スキル

| スキル | As-Is | To-Be | 備考 |
|--------|-------|-------|------|
| daily-metrics-reporter | ユーザー版（RC Part 2欠落） | OpenClaw bundled版に統一 | **🔴 重要: ユーザー版削除** |
| github | 未使用 | 有効化 | - |
| gmail | 未インストール | インストール＆設定 | ユーザーOAuth必要 |

**⚠️ 重要: Slack はスキルではなくチャンネル設定**
- `slack` は `skills.entries` ではなく `channels.slack` で設定
- Slack 投稿/リアクション等は `channels.slack.actions` で制御
- 詳細は「channels.slack 設定構造」セクション参照

**⚠️ スキルバージョン問題:**
- 現在: `~/.openclaw/workspace/skills/daily-metrics-reporter/` に古いバージョンが存在
- 問題: RevenueCat Part 2 が欠落している
- 解決: ユーザー版を削除し、OpenClaw bundled版（`/opt/homebrew/lib/node_modules/openclaw/skills/`）を使用

---

## テストマトリックス

### 正常系

| # | To-Be | テスト名 | 実行タイミング |
|---|-------|----------|---------------|
| 1 | RevenueCat API動作 | test_revenuecat_api_direct | Step 2完了後 |
| 2 | Mixpanel API動作 | test_mixpanel_api_direct | Step 2完了後 |
| 3 | Slack mention応答 | test_slack_mention_response | Step 2完了後 |
| 4 | ~~メモリ記録~~ | ~~test_memory_written~~ | **削除** - MCP 未対応 |
| 5 | dmScope設定 | test_dmscope_config | Step 3完了後 |
| 6 | Gmail通知 | test_gmail_notification | Step 5完了後 |
| 7 | LINE応答 | test_line_response | Step 6完了後 |
| 8 | **Slack exec投稿** | test_slack_exec_post | Step 4完了後 |

### 異常系・エラーハンドリング

| # | シナリオ | テスト名 | 期待動作 |
|---|---------|----------|---------|
| E1 | RevenueCat レート制限 (5 req/min) | test_rc_rate_limit | エラーメッセージ + リトライ案内 |
| E2 | Mixpanel レート制限 (60 req/hour) | test_mp_rate_limit | エラーメッセージ + 待機時間案内 |
| E3 | 無効な API トークン | test_invalid_token | 「認証エラー」メッセージ |
| E4 | OAuth トークン期限切れ (Gmail) | test_oauth_expired | 再認証案内 |
| E5 | Gateway 未起動 | test_gateway_down | 接続エラーメッセージ |

---

## 境界（やらないこと）

| やらないこと | 理由 |
|-------------|------|
| WhatsApp統合 | 今回のスコープ外 |
| Discord統合 | 今回のスコープ外 |
| Browser自動化 | 今回のスコープ外 |
| マルチモデルルーティング | 別タスクで実施 |

---

## セキュリティ注意事項

### 機密ファイルの権限設定

| ファイル | 推奨権限 | コマンド |
|---------|---------|---------|
| `~/.openclaw/openclaw.json` | 600 | `chmod 600 ~/.openclaw/openclaw.json` |
| `~/Library/LaunchAgents/ai.openclaw.gateway.plist` | 600 | `chmod 600 ~/Library/LaunchAgents/ai.openclaw.gateway.plist` |

### バックアップ・ログからの除外

| 対象 | 理由 | 対策 |
|------|------|------|
| `openclaw.json` | Slack/API トークン含む | Time Machine から除外、git 追跡しない |
| LaunchAgent plist | 環境変数に API キー | Time Machine から除外 |
| Gateway ログ | ツール実行履歴 | `logging.redactSensitive: "tools"` を設定 |

### 将来検討事項

- macOS Keychain への移行（API キーの平文保存を回避）
- 1Password CLI 連携（`op read` でシークレット取得）

---

## 🔴 根本原因分析（調査結果 - 2026-02-05 22:30 更新）

### 🚨 本当の根本原因（エラーログから特定）

**Gateway エラーログ (`~/.openclaw/logs/gateway.err.log`) より:**

```
[tools] tools.allow allowlist contains unknown entries (slack). These entries won't match any tool unless the plugin is enabled.
[tools] agents.anicca.tools.allow allowlist contains unknown entries (slack). These entries won't match any tool unless the plugin is enabled.
```

| 問題 | 原因 | 影響 |
|------|------|------|
| **🔴 slack ツールが認識されない** | `slack` がツールとして登録されていない | Slack 投稿不可 |
| **🔴 MCP ツール呼び出し** | `mcp__*` は OpenClaw 未対応 | `command not found` エラー |
| ✅ 環境変数 | 正常に設定済み（確認済み） | - |
| ✅ Slack 接続 | Socket Mode 接続成功 | - |

### エージェントの応答（ログより）

```
"I'm currently unable to directly use the Slack tool for sending messages."
"現在直接Slackへの投稿はサポートされていません。"
```

**これは認証エラーではなく、`slack` ツールがプラグインとして認識されていないため。**

### 修正方法

**問題**: `openclaw.json` で `tools.allow: ["slack"]` と指定しているが、`slack` はツールではなくチャンネルプラグインとして動作する。

**解決策**:
1. `slack` をツールとして有効化するには、OpenClaw の slack スキルが `slack` ツールを提供する必要がある
2. または、`exec` ツール経由で `openclaw message send` CLI を使用する
3. または、OpenClaw の内部 API を直接呼び出す

### 診断コマンド

```bash
# 1. エラーログを確認（本当の原因がここにある）
tail -50 ~/.openclaw/logs/gateway.err.log

# 2. 利用可能なツール一覧を確認
openclaw tools list

# 3. Gateway の状態を確認
launchctl print gui/$(id -u)/ai.openclaw.gateway | head -60
```

### 旧分析（参考）

| 問題領域 | 根本原因 | 影響 |
|---------|---------|------|
| ~~環境変数スコープ~~ | ✅ 確認済み - 正常に設定 | - |
| ~~スキルバージョン不整合~~ | ✅ 修正済み - curl ベースに書き換え | - |
| **MCP ツール呼び出し** | OpenClaw は MCP 未対応 | `exec failed: command not found: mcp__*` |
| **slack ツール未認識** | プラグイン未有効化 | Slack 投稿不可 |

---

## 🟢 ベストプラクティス差分（調査結果）

### 現在の設定 vs 推奨設定

| 項目 | 現在値 | 推奨値 | 変更要否 | 理由 |
|------|--------|--------|---------|------|
| **dmScope** | 未設定（default: main） | `per-channel-peer` | 🔴 必須 | プライバシー保護 |
| **session.reset** | 未設定 | - | ❌ スキップ | **v2026.2.2-3 では未サポート** |
| **historyLimit** | 50 | 25 | 🟡 推奨 | トークンコスト削減 |
| **maxConcurrent** | 4 | 1 | 🟡 推奨 | 予測可能な動作 |
| **subagents.maxConcurrent** | 8 | 3-5 | ✅ OK | 範囲内 |
| **logging.redactSensitive** | 未設定 | `"tools"` | 🔴 必須 | セキュリティ |
| **model.primary** | `openai/gpt-4o` | `anthropic/claude-sonnet-4` | 🟡 推奨 | Opus 4.5の90%の能力で20%のコスト |

### 推奨openclaw.json追加設定

```json
{
  "session": {
    "dmScope": "per-channel-peer"
  },
  "logging": {
    "redactSensitive": "tools"
  },
  "agents": {
    "defaults": {
      "maxConcurrent": 1,
      "model": {
        "primary": "anthropic/claude-sonnet-4"
      }
    }
  },
  "channels": {
    "slack": {
      "historyLimit": 25
    }
  }
}
```

**⚠️ session.reset について:** v2026.2.2-3 では未サポート。将来バージョンで対応予定。

---

## 実行手順

### Step 1: Status Quo記録（エージェント作業）

**作業者**: エージェント
**所要時間**: 5分

1. Serenaメモリに `openclaw-anicca-setup.md` を作成
2. 以下の内容を記録:
   - Slack Manifest修正内容（Event Subscriptions必須）
   - 環境変数の場所（LaunchAgent plist）
   - チャンネル設定（#metrics: C091G3PKHL2, #ai: C08RZ98SBUL）
   - スキルパス（workspace + bundled両方必要）

**テスト（即時実行）**:
```bash
# メモリファイルが存在することを確認（MCP は OpenClaw 未対応のため直接ファイル確認）
ls -la ~/.serena/memories/openclaw-anicca-setup.md
cat ~/.serena/memories/openclaw-anicca-setup.md | head -20
```

**⚠️ 注意**: `mcp__serena__read_memory` は OpenClaw では使用不可。Claude Code からのみ使用可能。

---

### Step 2: RevenueCat/Mixpanel問題解決

**作業者**: エージェント
**所要時間**: 20分

#### Step 2.0: スキルバージョン統一（重要！）

**問題**: ユーザー版スキル（`.openclaw/workspace/skills/`）とOpenClaw bundled版が不整合
- ユーザー版: RevenueCat Part 2 が欠落
- OpenClaw版: 完全実装

```bash
# ユーザー版スキルを削除（OpenClaw bundled版を使用）
rm -rf ~/.openclaw/workspace/skills/daily-metrics-reporter

# 確認
ls -la ~/.openclaw/workspace/skills/
# daily-metrics-reporter がないことを確認
```

#### Step 2.1: 環境変数診断（根本原因特定）

```bash
# 1. Gatewayプロセスに環境変数が渡っているか確認
launchctl print gui/$(id -u)/ai.openclaw.gateway | grep -E "REVENUECAT|MIXPANEL|OPENAI"

# 2. 環境変数が表示されない場合 → LaunchAgent plistを確認
cat ~/Library/LaunchAgents/ai.openclaw.gateway.plist | grep -A 30 "EnvironmentVariables"

# 3. 環境変数がplistにない場合 → 追加が必要（下記参照）
```

**⚠️ 環境変数がGatewayに渡っていない場合の対処:**

```bash
# LaunchAgent plistを編集
nano ~/Library/LaunchAgents/ai.openclaw.gateway.plist

# 以下を<dict>直下に追加:
# <key>EnvironmentVariables</key>
# <dict>
#   <key>REVENUECAT_V2_SECRET_KEY</key>
#   <string>sk_...</string>
#   <key>MIXPANEL_API_SECRET</key>
#   <string>...</string>
#   <key>MIXPANEL_PROJECT_ID</key>
#   <string>3970220</string>
# </dict>

# Gateway再起動
launchctl kickstart -k gui/$(id -u)/ai.openclaw.gateway
```

#### Step 2.2: API直接テスト（テスト即時実行）

**⚠️ 重要: APIシークレットは絶対にハードコードしない。環境変数を使用する。**

```bash
# RevenueCat API直接テスト（環境変数から読み込み）
curl -s "https://api.revenuecat.com/v2/projects/projbb7b9d1b/metrics/overview" \
  -H "Authorization: Bearer $REVENUECAT_V2_SECRET_KEY" \
  -H "Content-Type: application/json"

# Mixpanel API直接テスト（環境変数から読み込み）
curl -s "https://mixpanel.com/api/2.0/segmentation?project_id=$MIXPANEL_PROJECT_ID&event=onboarding_started&from_date=$(date -d '13 days ago' +%Y-%m-%d)&to_date=$(date +%Y-%m-%d)&unit=day" \
  -u "$MIXPANEL_API_SECRET:"
```

**📝 注意: RevenueCat APIはMRRを整数で返す（例: 17 = $17）。小数点なし。**

#### Step 2.3: SKILL.md の Slack 投稿方法を修正（🔴 最重要）

**問題**: 現在の SKILL.md は `slack` ツールを JSON で呼び出すよう指示しているが、`slack` はツールとして認識されない。

**修正**: `exec` ツールで `openclaw message send` CLI を使用する。

**旧（動かない）:**
```json
{
  "action": "sendMessage",
  "to": "channel:C091G3PKHL2",
  "content": "レポート内容"
}
```

**新（正しい — `openclaw message send --help` で検証済み）:**
```bash
# exec ツールで以下を実行
openclaw message send --channel slack --target "C091G3PKHL2" --message "レポート内容"
```

**CLI オプション（`--help` より）:**
| オプション | 説明 |
|-----------|------|
| `--channel slack` | チャンネル種別（slack/telegram/discord 等） |
| `--target <dest>` | 宛先（Slack の場合はチャンネル ID またはユーザー ID） |
| `--message <text>` | メッセージ本文 |
| `--dry-run` | 送信せずにペイロードを表示（デバッグ用） |

**SKILL.md の修正箇所:**

```markdown
## Slack 投稿方法

**`exec` ツールで以下のコマンドを実行（`openclaw message send --help` で検証済み）:**

\`\`\`bash
openclaw message send --channel slack --target "C091G3PKHL2" --message "{作成したレポート内容}"
\`\`\`

**重要:**
- `slack` ツールは使用不可（プラグイン未登録エラー）
- `exec` ツール + `openclaw message send` CLI を使用
- メッセージ内の改行は `\n` でエスケープ
```

#### Step 2.4: Slack経由テスト（テスト即時実行）

**テスト方法**: Slack #metricsで以下を送信
```
@Anicca MRRを教えて
```

**期待結果**: RevenueCatのMRR値が返る（例: MRR: $17）

---

### Step 3: ベストプラクティス設定適用

**作業者**: エージェント
**所要時間**: 10分

#### 変更内容（調査結果反映）

openclaw.jsonに以下を追加/変更:

```json
{
  "session": {
    "dmScope": "per-channel-peer"
  },
  "logging": {
    "redactSensitive": "tools"
  },
  "channels": {
    "slack": {
      "historyLimit": 25
    }
  }
}
```

**📝 変更理由:**
| 設定 | 旧値 | 新値 | 理由 |
|------|------|------|------|
| session.dmScope | 未設定 | `per-channel-peer` | プライバシー保護（送信者ごとにDM分離） |
| logging.redactSensitive | 未設定 | `"tools"` | ログにAPIキーが漏れない |
| historyLimit | 50 | 25 | トークンコスト削減（10-15%節約） |

**⚠️ 注意**: `session.reset.idle` は v2026.2.2-3 では未サポート（`openclaw doctor` でエラー）。将来バージョンで対応予定。

#### Gateway再起動

```bash
launchctl kickstart -k gui/$(id -u)/ai.openclaw.gateway
```

**テスト（即時実行）**:
```bash
# 設定が反映されたか確認
cat ~/.openclaw/openclaw.json | jq '.session, .logging, .channels.slack.historyLimit'

# 設定検証
openclaw doctor
```

---

### Step 4: exec approvals 設定 + github スキル有効化

**作業者**: エージェント
**所要時間**: 10分

**⚠️ 重要**: `slack` ツールは未認識のため使用しない。Slack 投稿は `exec` + `openclaw message send` CLI で行う。

#### 4.1 exec ツール有効化確認

```bash
cat ~/.openclaw/openclaw.json | jq '.tools.allow'
# 期待: ["read", "write", "exec", ...]
```

#### 4.2 exec approvals 設定（🔴 必須）

**問題**: `exec` が allowlist に登録されていないと、コマンド実行が拒否される。

**解決策**: `openclaw` CLI を allowlist に追加する。

```json
// ~/.openclaw/openclaw.json に追加
{
  "tools": {
    "exec": {
      "security": "allowlist",
      "allowlist": [
        "/opt/homebrew/bin/openclaw"
      ]
    }
  }
}
```

**⚠️ セキュリティ注意**: `curl` を allowlist に入れると任意のURLへのリクエストが可能になるため、追加しない。API 呼び出しは SKILL.md 内のスクリプトで直接実行する。

**または、Auto-allow skill CLIs を有効化:**
```json
{
  "tools": {
    "exec": {
      "autoAllowSkillClis": true
    }
  }
}
```

参考: https://docs.openclaw.ai/tools/exec-approvals

#### 4.3 github スキル有効化

```json
{
  "skills": {
    "entries": {
      "github": { "enabled": true }
    }
  }
}
```

#### 4.4 Gateway再起動

```bash
launchctl kickstart -k gui/$(id -u)/ai.openclaw.gateway
```

**テスト（即時実行）**:
Slack #metrics で以下を送信:
```
@Anicca MRRを教えて、そして結果を #metrics に投稿して
```

**期待結果**: Anicca が `exec` ツールで `openclaw message send` を実行し、#metrics にレポートが投稿される

---

### Step 5: Gmail統合

#### ユーザー作業（実装前）

| # | タスク | 手順 | 取得するもの |
|---|--------|------|-------------|
| 1 | Google Cloud Console でプロジェクト作成 | https://console.cloud.google.com/ → 新規プロジェクト | Project ID |
| 2 | Gmail API有効化 | APIs & Services → Enable APIs → Gmail API | - |
| 3 | OAuth同意画面設定 | OAuth consent screen → External → 必要情報入力 | - |
| 4 | OAuth認証情報作成 | Credentials → Create → OAuth client ID → Desktop app | Client ID, Client Secret |

**🛑 STOP: ユーザーは上記4ステップを完了してから続行**

**完了確認**: ユーザーが以下を提供する
- Google Cloud Project ID
- OAuth Client ID
- OAuth Client Secret

#### エージェント作業（ユーザー完了後）

1. Gmailプラグインインストール
```bash
npm install -g @mcinteerj/openclaw-gmail@1.2.7
```

2. openclaw.jsonに設定追加
```json
{
  "plugins": {
    "entries": {
      "gmail": {
        "enabled": true,
        "clientId": "{{USER_PROVIDED_CLIENT_ID}}",
        "clientSecret": "{{USER_PROVIDED_CLIENT_SECRET}}"
      }
    }
  }
}
```

3. OAuth認証実行
```bash
openclaw gmail login
```

#### ユーザー作業（実装中）

| # | タイミング | タスク | 理由 |
|---|-----------|--------|------|
| 1 | OAuth認証実行後 | ブラウザでGoogle認証を完了 | 自動テスト不可 |

**🛑 STOP: ユーザーはブラウザでGoogle認証を完了してから続行**

**テスト（即時実行）**:
1. 自分宛にテストメール送信
2. Slack #metricsで確認:
```
@Anicca 最新のメール教えて
```

---

### Step 6: LINE統合

**⚠️ 重要: 2024年9月以降、LINE Messaging APIの設定手順が変更されました。**

旧手順（❌ 非推奨）: LINE Developers Console → Create Channel
新手順（✅ 正しい）: LINE Official Account Manager → アカウント作成 → Messaging API有効化

#### ユーザー作業（実装前）

| # | タスク | 手順 | 取得するもの |
|---|--------|------|-------------|
| 1 | LINE Official Account Manager にアクセス | https://manager.line.biz/ → LINEログイン | - |
| 2 | 公式アカウント作成 | 「アカウント作成」→ アカウント名入力 → 業種選択 | - |
| 3 | Messaging API有効化 | 設定 → Messaging API → 「Messaging APIを利用する」 | - |
| 4 | LINE Developers Console確認 | https://developers.line.biz/ → 自動作成されたチャンネルを確認 | Channel ID |
| 5 | Channel Secret取得 | Basic settings → Channel secret | Channel Secret |
| 6 | Channel Access Token発行 | Messaging API → Issue (long-lived) | Channel Access Token |
| 7 | Webhook URL設定 | Messaging API → Webhook URL → `https://your-server/line/webhook` | - |
| 8 | Webhook利用をON | 「Use webhook」をONに切り替え | - |

**🛑 STOP: ユーザーは上記8ステップを完了してから続行**

**完了確認**: ユーザーが以下を提供する
- LINE Channel ID
- LINE Channel Secret
- LINE Channel Access Token (long-lived)

#### エージェント作業（ユーザー完了後）

1. openclaw.jsonに設定追加
```json
{
  "channels": {
    "line": {
      "enabled": true,
      "channelId": "{{USER_PROVIDED_CHANNEL_ID}}",
      "channelSecret": "{{USER_PROVIDED_CHANNEL_SECRET}}",
      "channelAccessToken": "{{USER_PROVIDED_ACCESS_TOKEN}}"
    }
  }
}
```

2. Gateway再起動

#### ユーザー作業（実装後）

| # | タスク | 確認項目 |
|---|--------|---------|
| 1 | LINEグループにボットを招待 | グループ設定 → メンバー招待 |
| 2 | テストメッセージ送信 | `@Anicca こんにちは` |

**🛑 STOP: ユーザーはボット招待とテストメッセージを完了してから続行**

**テスト（即時実行）**:
LINEグループで:
```
@Anicca 今日の天気は？
```

**期待結果**: Aniccaが天気情報を返す

---

## E2E判定

| 項目 | 値 |
|------|-----|
| UI変更 | なし（Slack/LINE/Gmailは外部サービス） |
| 新画面 | なし |
| 結論 | Maestro E2Eシナリオ: 不要（外部サービステストはcurl/Slack直接テスト） |

---

## アーキテクチャ（Anicca OpenClaw完成形）

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER TOUCHPOINTS                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐      │
│   │  Slack  │    │  Gmail  │    │  LINE   │    │  Cron   │      │
│   │#metrics │    │ Inbox   │    │ Family  │    │ Daily   │      │
│   │  #ai    │    │         │    │ Group   │    │ Report  │      │
│   └────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘      │
│        │              │              │              │            │
│        └──────────────┴──────────────┴──────────────┘            │
│                              │                                    │
│                              ▼                                    │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                  OpenClaw Gateway                        │   │
│   │                  (port 18789)                            │   │
│   │  ┌─────────────────────────────────────────────────┐    │   │
│   │  │ Session Management                               │    │   │
│   │  │ - dmScope: per-channel-peer (privacy)           │    │   │
│   │  │ - reset: 未設定 (v2026.2.2-3未サポート)          │    │   │
│   │  └─────────────────────────────────────────────────┘    │   │
│   └─────────────────────────────────────────────────────────┘   │
│                              │                                    │
│                              ▼                                    │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    Anicca Agent                          │   │
│   │                    (id: anicca)                          │   │
│   │  ┌────────────────────────────────────────────────┐     │   │
│   │  │ Skills                                          │     │   │
│   │  │ ├── daily-metrics-reporter (Mixpanel+RC)       │     │   │
│   │  │ ├── github (issues, PRs)                       │     │   │
│   │  │ ├── gmail (email management)                   │     │   │
│   │  │ └── weather (no API key needed)                │     │   │
│   │  └────────────────────────────────────────────────┘     │   │
│   │  ┌────────────────────────────────────────────────┐     │   │
│   │  │ Tools (exec allowlist)                         │     │   │
│   │  │ └── openclaw message send (Slack投稿用)       │     │   │
│   │  └────────────────────────────────────────────────┘     │   │
│   └─────────────────────────────────────────────────────────┘   │
│                              │                                    │
│                              ▼                                    │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                  External APIs                           │   │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐               │   │
│   │  │ RevenueCat│  │ Mixpanel │  │ OpenAI   │               │   │
│   │  │ MRR, Subs │  │ Events   │  │ GPT-4o   │               │   │
│   │  └──────────┘  └──────────┘  └──────────┘               │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        DATA FLOW                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  [Slack @mention] ──► Gateway ──► Anicca ──► Skill(API呼び出し) │
│                                      │                           │
│                                      ▼                           │
│                    exec: openclaw message send ──► Slack         │
│                                                                   │
│  [Cron 05:00 JST] ──► Gateway ──► daily-metrics-reporter        │
│                                      │                           │
│                                      ├──► curl: Mixpanel API     │
│                                      ├──► curl: RevenueCat API   │
│                                      ▼                           │
│                    exec: openclaw message send ──► #metrics      │
│                                                                   │
│  [Gmail New Email] ──► Pub/Sub ──► Gateway ──► Anicca           │
│                                      │                           │
│                                      ▼                           │
│                               [Notify Slack or Auto-reply]       │
│                                                                   │
│  [LINE @Anicca] ──► Webhook ──► Gateway ──► Anicca              │
│                                      │                           │
│                                      ▼                           │
│                               [Response to LINE]                 │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    ENVIRONMENT VARIABLES                         │
├─────────────────────────────────────────────────────────────────┤
│  Location: ~/Library/LaunchAgents/ai.openclaw.gateway.plist     │
│                                                                   │
│  OPENAI_API_KEY          = (設定済み)                            │
│  MIXPANEL_PROJECT_ID     = (設定済み: 3970220)                   │
│  MIXPANEL_API_SECRET     = (設定済み)                            │
│  REVENUECAT_V2_SECRET_KEY = (設定済み)                           │
│  SLACK_BOT_TOKEN         = (openclaw.jsonに設定済み)             │
│  SLACK_APP_TOKEN         = (openclaw.jsonに設定済み)             │
│  LINE_CHANNEL_ID         = (Step 6で追加予定)                    │
│  LINE_CHANNEL_SECRET     = (Step 6で追加予定)                    │
│  LINE_ACCESS_TOKEN       = (Step 6で追加予定)                    │
│  GMAIL_CLIENT_ID         = (Step 5で追加予定)                    │
│  GMAIL_CLIENT_SECRET     = (Step 5で追加予定)                    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Aniccaの機能一覧（完成後）

```
🧘 Anicca（プロアクティブ AI エージェント）
│
├── 📊 自動で毎朝やること（Cron 05:00 JST）
│   ├── RevenueCat から MRR/Subs/Trials 取得
│   ├── Mixpanel からファネルデータ取得
│   └── Slack #metrics に日次レポート投稿
│
├── 📧 メールを自動監視（gmail スキル）
│   ├── 新着メール検知 → 重要なら Slack に通知
│   ├── 特定の送信者 → 自動で要約して報告
│   └── 返信が必要 → リマインド
│
├── 💬 Slack で聞かれたら答える
│   ├── @Anicca MRRは？ → RevenueCat から取得して回答
│   ├── @Anicca インストール数は？ → Mixpanel から取得して回答
│   ├── @Anicca 天気は？ → 天気情報を回答
│   ├── @Anicca issue作って → GitHub に issue 作成
│   └── @Anicca リアクションつけて → Slack メッセージにリアクション
│
├── 📱 LINE で家族と会話
│   ├── @Anicca こんにちは → 会話
│   ├── @Anicca 今日の予定は？ → カレンダー確認して回答
│   └── @Anicca 買い物リスト → リスト管理
│
├── 🔧 開発を手伝う（coding-agent）
│   ├── Claude Code / Codex を起動してコード書く
│   ├── PR レビュー依頼 → レビューして報告
│   └── ビルドエラー → 自動で調査
│
└── 🛡️ 信頼性評価（molt-trust）
    └── 情報の信頼性をチェック
```

**普通のエージェントとの違い：**

```
普通のエージェント        Anicca（プロアクティブ）
        │                         │
        ▼                         ▼
  聞かれたら答える         自分から動く
        │                         │
        │                    ┌────┴────┐
        │                    │         │
        ▼                    ▼         ▼
    受動的               Cron      イベント監視
                          │         │
                          ▼         ▼
                    毎朝レポート   メール来たら通知
                    自動投稿      重要なら即報告
```

---

## レビューチェックリスト（サブエージェント用）

### Tech Researcher Review

| # | チェック項目 | 判定 |
|---|-------------|------|
| 1 | RevenueCat V2 APIのエンドポイントは正しいか | |
| 2 | Gmailプラグイン(@mcinteerj/openclaw-gmail)は最新か | |
| 3 | LINE Messaging APIの設定手順は正確か | |
| 4 | dmScope: per-channel-peerはベストプラクティスか | |
| 5 | session.reset設定は推奨値か | |

### Coder Review

| # | チェック項目 | 判定 |
|---|-------------|------|
| 1 | SKILL.mdのmetadata.requires.envは正しい形式か | |
| 2 | openclaw.jsonの設定は正しいJSON構文か | |
| 3 | 環境変数の受け渡しパターンは正しいか | |
| 4 | Gateway再起動コマンドは正しいか | |
| 5 | テストコマンドは実行可能か | |

---

## レビュー結果

### Round 1: 初回レビュー

| レビュアー | 結果 | 修正内容 |
|-----------|------|---------|
| Tech Researcher | 2 FAIL, 1 WARN | LINE手順更新、RevenueCat MRR整数注記 |
| Coder | 1 FAIL, 2 WARN | APIシークレット環境変数化、SKILL.md形式明記、session.reset検証追加 |

### Round 2: 深堀り調査

| 調査 | 主な発見 |
|------|---------|
| **RC/Mixpanel問題根本原因** | (1) 環境変数がGatewayに渡っていない可能性、(2) ユーザー版スキルにRC Part 2欠落、(3) レート制限 5 req/min |
| **ベストプラクティス** | session.reset は **v2026.2.2-3 未サポート**（スキップ）、historyLimit は 25 推奨、logging.redactSensitive 必須 |
| **ローカル調査** | 2つのスキルバージョン存在（OpenClaw版 vs ユーザー版）、ユーザー版削除が必要 |

### 修正済み項目

| # | 問題 | 修正 |
|---|------|------|
| 1 | ハードコードAPIシークレット（FAIL） | ✅ 環境変数参照に置換 |
| 2 | LINE手順が2024年以前の古い手順（FAIL） | ✅ LINE Official Account Manager経由に更新 |
| 3 | SKILL.md metadata非標準（WARN） | ✅ ドキュメント専用と明記 |
| 4 | session.reset構文未検証（WARN） | ✅ **削除** - v2026.2.2-3 未サポートのため設定しない |
| 5 | RevenueCat MRR整数形式（WARN） | ✅ 注記追加 |
| 6 | スキルバージョン不整合（NEW） | ✅ Step 2.0 にユーザー版削除手順追加 |
| 7 | 環境変数診断なし（NEW） | ✅ Step 2.1 に診断コマンド追加 |
| 8 | セキュリティ設定なし（NEW） | ✅ logging.redactSensitive 追加 |
| 9 | historyLimit過大（NEW） | ✅ 50 → 25 に変更 |

---

## 実装進捗（2026-02-06 22:00 JST 更新）

### 完了したタスク

| # | タスク | ステータス | 備考 |
|---|--------|-----------|------|
| 1 | SKILL.md を curl ベースに全面書き換え | ✅ 完了 | RC: curl, MP: curl |
| 2 | CLAUDE.md に OpenClaw VPS運用ルール追加 | ✅ 完了 | Gateway再起動方法、指示方法2種類 |
| 3 | VPS に OpenClaw 移行 | ✅ 完了 | systemd user service + lingering |
| 4 | RevenueCat データ取得テスト | ✅ 完了 | MRR: $17, Subs: 2, Trials: 1 |
| 5 | Mixpanel 3イベント取得 | ✅ 完了 | onboarding: 215, paywall: 92, trial: 1 |
| 6 | profile: full 全ツール有効化 | ✅ 完了 | slack, cron, web_search, browser等 |
| 7 | Slack投稿テスト | ✅ 完了 | slackツール + exec CLI 両方動作 |
| 8 | Cron（日次レポート 5am + ミーティングリマインダー 日/月9am） | ✅ 完了 | #meeting配信 + 祝日チェック付き |
| 9 | EXA_API_KEY 設定 | ✅ 完了 | VPS .env に追加 |
| 10 | EnvironmentFile systemd設定 | ✅ 完了 | .env → Gateway プロセスに環境変数渡す |
| 11 | ワンフレッシュアーキテクチャ Spec追記 | ✅ 完了 | 永久機関ビジョン |

### 未完了タスク

| # | タスク | ステータス | ブロッカー |
|---|--------|-----------|-----------|
| 12 | 05:00 JST Cron 実行確認 | ⏳ 翌朝確認 | 自動実行待ち |
| 13 | Docker化 | ❌ 未着手 | 次のマイルストーン |
| 14 | Gmail 統合 | ❌ 未着手 | Step 5（ユーザーOAuth必要） |
| 15 | LINE 統合 | ❌ 未着手 | Step 6（ユーザーアカウント作成必要） |

---

## VPS 情報（Hetzner）

| 項目 | 値 |
|------|-----|
| **サーバー名** | `ubuntu-4gb-nbg1-7` |
| **IPv4** | `46.225.70.241` |
| **IPv6** | `2a01:4f8:1c19:985d::/64` |
| **SSH コマンド** | `ssh root@46.225.70.241` |
| **SSH ユーザー** | `root`（初期）→ `anicca`（作成後） |
| **状態** | ✅ Gateway 稼働中 (port 18789) |

---

## 残りの実装手順

### Step 1: ドキュメント整理 ✅ 完了

| # | タスク | 状態 |
|---|--------|------|
| 1.1 | reference/secrets.md に VPS 情報統合 | ✅ |
| 1.2 | CLAUDE.md に参照リンク追記 | ✅ |
| 1.3 | claude-progress.txt 新規作成 | ✅ |

### Step 2: VPS 移行 ✅ Gateway 稼働中

| # | タスク | 状態 | 備考 |
|---|--------|------|------|
| 2.1 | VPS に SSH して状態確認 | ✅ | Node v22.22.0, OpenClaw 2026.2.3-1 |
| 2.2 | anicca ユーザー作成 | ✅ | 既存（/home/anicca） |
| 2.3 | OpenClaw インストール | ✅ | 既存（/usr/bin/openclaw） |
| 2.4 | 環境変数を VPS に設定 | ✅ | /home/anicca/.env |
| 2.5 | `openclaw gateway install --force` | ✅ | user service 自動作成 |
| 2.6 | `openclaw gateway start` | ✅ | pid 165017, port 18789 |
| 2.7 | Slack テストメッセージ送信 | ✅ | `openclaw message send` 成功 |
| 2.8 | メトリクスレポート投稿（RC + ASC） | ✅ | Slack 投稿成功 |
| 2.9 | **Mixpanel 追加（Python 修正）** | ❌ | 次のタスク |

### Step 3: ベストプラクティス確認 ✅ 完了

| # | タスク | 状態 |
|---|--------|------|
| 3.1 | dmScope: per-channel-peer | ✅ |
| 3.2 | logging.redactSensitive | ✅ |
| 3.3 | historyLimit: 25 | ✅ |

### Step 4: exec approvals + github スキル ⚠️ 未確認

| # | タスク | 状態 |
|---|--------|------|
| 4.1 | exec ツール有効化確認 | ⚠️ |
| 4.2 | github スキル有効化 | ⚠️ |

### Step 5: Gmail 統合 ❌ 未着手

| # | タスク | 状態 |
|---|--------|------|
| 5.1 | Google Cloud Console でプロジェクト作成 | ❌ ユーザー作業 |
| 5.2 | Gmail API 有効化 | ❌ ユーザー作業 |
| 5.3 | OAuth 認証情報作成 | ❌ ユーザー作業 |
| 5.4 | Gmail プラグインインストール | ❌ |
| 5.5 | openclaw.json に設定追加 | ❌ |
| 5.6 | OAuth 認証実行 | ❌ ユーザー作業 |
| 5.7 | テスト | ❌ |

### Step 6: LINE 統合 ❌ 未着手

| # | タスク | 状態 |
|---|--------|------|
| 6.1 | LINE Official Account 作成 | ❌ ユーザー作業 |
| 6.2 | Messaging API 有効化 | ❌ ユーザー作業 |
| 6.3 | Channel Secret / Access Token 取得 | ❌ ユーザー作業 |
| 6.4 | Webhook URL 設定 | ❌ ユーザー作業 |
| 6.5 | openclaw.json に LINE 設定追加 | ❌ |
| 6.6 | Gateway 再起動 | ❌ |
| 6.7 | テスト | ❌ |

---

## VPS 用 Cron プロンプト（正確な内容）

**テスト用 Cron と 5am Cron で同じプロンプトを使う。**

```
統合メトリクスレポートを作成してSlack #metricsに投稿してください。

## 手順

### 1. App Store Connect (exec)
/home/anicca/scripts/daily-metrics/.venv/bin/python -c 'import sys; sys.path.insert(0, "/home/anicca/scripts/daily-metrics"); import os; os.environ["ASC_KEY_ID"]="D637C7RGFN"; os.environ["ASC_ISSUER_ID"]="f53272d9-c12d-4d9d-811c-4eb658284e74"; os.environ["ASC_PRIVATE_KEY"]=open("/home/anicca/.keys/AuthKey_D637C7RGFN.p8").read(); os.environ["ASC_VENDOR_NUMBER"]="93486075"; import asyncio; from asc_client import fetch_app_store_metrics; m=asyncio.run(fetch_app_store_metrics()); print(f"Downloads: {m.total_downloads_7d}"); print(f"Countries: {dict(m.downloads_by_country)}")'

### 2. RevenueCat (exec + curl)
curl -sf "https://api.revenuecat.com/v2/projects/projbb7b9d1b/metrics/overview" -H "Authorization: Bearer $REVENUECAT_V2_SECRET_KEY"

### 3. Mixpanel 14日間 (exec + curl)
from_date=$(date -d "13 days ago" +%Y-%m-%d); to_date=$(date +%Y-%m-%d); curl -sf "https://mixpanel.com/api/2.0/segmentation?project_id=3970220&event=onboarding_started&from_date=$from_date&to_date=$to_date&unit=day" -u "$MIXPANEL_API_SECRET:"

全データを取得したら、以下のフォーマットでSlack #metrics (C091G3PKHL2) に投稿:

📊 Anicca Daily Report (日付)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 APP STORE (7日): Downloads {X}, Top: {国}({数})
💰 REVENUE: MRR ${X}, Subs {X}, Trials {X}
📈 FUNNEL (14日): onboarding {X}, paywall {X}, trial {X}
📊 変換率: オンボ→Paywall {X}%, Paywall→Trial {X}%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧘 Anicca

確認不要、即座に実行。
```

### VPS パス設定

| 項目 | VPS パス |
|------|---------|
| Python venv | `/home/anicca/scripts/daily-metrics/.venv/bin/python` |
| スクリプト | `/home/anicca/scripts/daily-metrics/` |
| ASC Key | `/home/anicca/.keys/AuthKey_D637C7RGFN.p8` |
| 環境変数 | `/home/anicca/.env` |

---

## VPS systemd user service セットアップ（正しい方法）

### ❌ 間違い: system service

```
/etc/systemd/system/openclaw-gateway.service  ← 間違い
systemctl start openclaw-gateway              ← 間違い
```

**エラー**: `Gateway service check failed: Error: systemctl --user unavailable: Failed to connect to bus: No medium found`

**原因**: OpenClaw は **user session DBus** を必要とする。system service には DBus session がない。

---

### ✅ 正しい方法: user service + lingering

| 項目 | 正しい設定 |
|------|-----------|
| **サービスファイル** | `/home/anicca/.config/systemd/user/openclaw-gateway.service` |
| **lingering** | `sudo loginctl enable-linger anicca` |
| **起動コマンド** | `systemctl --user start openclaw-gateway` |
| **有効化** | `systemctl --user enable openclaw-gateway` |
| **ログ確認** | `journalctl --user -u openclaw-gateway -f` |

---

### 手順（コピペで実行可能）

**前提**: root ユーザーで SSH 接続して実行する。`$(id -u anicca)` は anicca ユーザーの UID を取得する。

```bash
# 1. system service を削除（間違った設定を削除）
sudo systemctl stop openclaw-gateway
sudo systemctl disable openclaw-gateway
sudo rm -f /etc/systemd/system/openclaw-gateway.service
sudo systemctl daemon-reload

# 2. lingering を有効化
# Lingering: ユーザーがログアウト・再起動しても user session を維持する仕組み
# これがないと anicca ユーザーの systemd user service が停止する
sudo loginctl enable-linger anicca

# 3. ローカルから openclaw.json をコピー（ローカルMacで実行）
# ※ VPSではなくローカルMacのターミナルで実行すること
# scp ~/.openclaw/openclaw.json anicca@46.225.70.241:/home/anicca/.openclaw/

# 4. 権限設定（セキュリティ必須）
chmod 600 /home/anicca/.env
chmod 600 /home/anicca/.openclaw/openclaw.json
chmod 600 /home/anicca/.keys/AuthKey_D637C7RGFN.p8
chown -R anicca:anicca /home/anicca/.openclaw /home/anicca/.keys /home/anicca/.env

# 5. user service ディレクトリを作成
sudo -u anicca mkdir -p /home/anicca/.config/systemd/user

# 6. user service ファイルを作成（EnvironmentFile 付き）
sudo -u anicca tee /home/anicca/.config/systemd/user/openclaw-gateway.service << 'EOF'
[Unit]
Description=OpenClaw Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/openclaw gateway start
Restart=always
RestartSec=10
EnvironmentFile=/home/anicca/.env
Environment="PATH=/usr/bin:/bin"
Environment="HOME=/home/anicca"

[Install]
WantedBy=default.target
EOF

# 7. service ファイルの権限設定
chmod 644 /home/anicca/.config/systemd/user/openclaw-gateway.service

# 8. ユーザー systemd をリロード
# XDG_RUNTIME_DIR: XDG Base Directory Specification で定義されたユーザーセッションのランタイムディレクトリ
# systemctl --user は DBus 経由でユーザーセッションに接続するため、この環境変数が必須
# Lingering が有効でも、root から実行する場合は明示的に設定が必要
sudo -u anicca XDG_RUNTIME_DIR=/run/user/$(id -u anicca) systemctl --user daemon-reload

# 9. サービスを有効化 + 起動
sudo -u anicca XDG_RUNTIME_DIR=/run/user/$(id -u anicca) systemctl --user enable openclaw-gateway
sudo -u anicca XDG_RUNTIME_DIR=/run/user/$(id -u anicca) systemctl --user start openclaw-gateway

# 10. 状態確認
sudo -u anicca XDG_RUNTIME_DIR=/run/user/$(id -u anicca) systemctl --user status openclaw-gateway
```

### anicca ユーザーで直接実行する場合

```bash
# anicca ユーザーに切り替え
su - anicca

# XDG_RUNTIME_DIR を設定
export XDG_RUNTIME_DIR=/run/user/$(id -u)

# systemd コマンド実行
systemctl --user daemon-reload
systemctl --user enable openclaw-gateway
systemctl --user start openclaw-gateway
systemctl --user status openclaw-gateway
```

---

### 確認コマンド

```bash
# Gateway が起動しているか
sudo -u anicca XDG_RUNTIME_DIR=/run/user/$(id -u anicca) systemctl --user status openclaw-gateway

# ポート 18789 がリッスンしているか
ss -tlnp | grep 18789

# ログ確認
sudo -u anicca XDG_RUNTIME_DIR=/run/user/$(id -u anicca) journalctl --user -u openclaw-gateway -n 50

# lingering 確認
loginctl show-user anicca | grep Linger
```

---

## 重要な発見

| 発見 | 内容 |
|------|------|
| **MCP は OpenClaw 未対応** | OpenClaw の GPT-4o エージェントは read/write/exec ツール使用可能。MCP ツールは Claude Code 専用 |
| **Slack 投稿の正しい方法** | `exec` で `openclaw message send --channel slack --target "<チャンネルID>" --message "..."` |
| **groupPolicy: open** | 全チャンネルでアクセス可能（チャンネル ID 個別指定不要） |
| **Cron 実行** | ✅ VPS 移行で 24 時間稼働（05:00 JST 自動実行） |
| **ログの場所** | `~/.openclaw/logs/`（`~/Library/Logs/openclaw/` ではない） |
| **VPS では user service 必須** | system service は DBus session がないためエラー。`systemctl --user` + `enable-linger` を使う |

---

## 最終更新

- 作成日: 2026-02-05
- 更新日: 2026-02-06 22:00 JST
- 作成者: Claude Code
- ステータス: 🟢 **VPS Gateway 稼働中（profile: full）** — ベース完成、次は Docker化 or Gmail/LINE

### 参照ファイル

| ファイル | 内容 |
|---------|------|
| `.cursor/plans/reference/secrets.md` | 全シークレット（VPS 情報追加予定） |
| `.cursor/plans/reference/openclaw-learnings.md` | OpenClaw 失敗から学んだこと |
| `~/.openclaw/openclaw.json` | OpenClaw 設定 |
| `~/.openclaw/cron/jobs.json` | Cron ジョブ設定 |
| `~/.openclaw/logs/gateway.err.log` | エラーログ |
