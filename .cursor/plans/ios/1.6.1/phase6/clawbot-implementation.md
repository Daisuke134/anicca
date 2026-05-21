# Clawdbot 導入仕様書

> 最終更新: 2026-01-25
> ステータス: 計画中

---

## 概要

### Clawdbotとは

Clawdbot は Peter Steinberger が開発したセルフホスト型AIアシスタント。
ChatGPT/Claudeと違い、**VPSまたはローカルPCで常時稼働**し、以下が可能：

1. **ファイルシステムアクセス** - コードを直接読み書き
2. **コマンド実行** - `git`, `npm`, `xcodebuild` 等を実行
3. **プロアクティブ通知** - 指定時刻に自動でメッセージ送信
4. **マルチチャネル** - Slack, Telegram, WhatsApp, Discord 等に接続

### なぜ導入するか

| 現状 | Clawdbot導入後 |
|------|---------------|
| KPI確認のために各ダッシュボードを開く | Slackに自動投稿される |
| 月曜ミーティングアナウンスを手動投稿 | 完全自動（祝日スキップ含む） |
| コード作業のためにCursor/ターミナルを開く | Slack DMで依頼するだけ |

### 公式リソース

- ドキュメント: https://docs.clawd.bot
- GitHub: https://github.com/clawdbot/clawdbot
- スキルマーケット: https://clawdhub.com/skills
- Discord: https://discord.gg/clawdbot

---

## 成田さん専用ユースケース

### 1. KPI自動投稿

**目的**: Anicca の日次KPIを自動でSlackに投稿

| 項目 | 値 |
|------|-----|
| 投稿先 | #anicca-kpi |
| 時刻 | 毎日 9:00 JST |
| データソース | App Store Connect, RevenueCat, Superwall |

**投稿フォーマット**:

```
📊 Anicca Daily KPI (2026-01-25)

📱 Installs
• Today: 142
• vs yesterday: +15%
• This week: 1,023

💰 Revenue (RevenueCat)
• MRR: $4,230
• New subscriptions: 12
• Churn: 3

🔔 Nudge Performance
• Delivered: 8,432
• Tapped: 5,734 (68%)
• 👍: 4,201 (73%)

🚀 Funnel (Superwall)
• Paywall views: 892
• Conversions: 47 (5.3%)
```

---

### 2. 月曜ミーティングアナウンス

**目的**: 研究室Slackに毎週月曜のミーティング通知を自動投稿

| 項目 | 値 |
|------|-----|
| 投稿先 | 研究室Slackチャンネル（要設定） |
| 時刻 | 毎週月曜 11:00 JST |
| 条件 | 祝日は自動スキップ |

**投稿フォーマット**:

```
📢 本日12:00からミーティングがあります。
出席できない方は事前にご連絡ください。
```

**祝日判定**:
- 日本の祝日APIまたはカレンダースキルで判定
- 祝日の場合は投稿しない

---

### 3. 「頼む」機能（コード作業依頼）

**目的**: Slack DMでコード作業を依頼し、ClawdbotがAniccaリポジトリで作業

| 項目 | 値 |
|------|-----|
| 入力 | Slack DM to Clawdbot |
| 作業場所 | `/Users/cbns03/Downloads/anicca-project` |
| 出力 | 作業完了報告 + PR作成（依頼時） |

**ワークフロー例**:

```
成田さん: 「NudgeCardViewに🤖アイコン追加しといて」
    ↓
Clawdbot: 「了解。作業開始します...」
    ↓
（coding-agent がファイルを編集）
    ↓
Clawdbot: 「完了しました ✅
変更内容:
- NudgeCardView.swift L58 に🤖表示追加
- isAIGenerated フラグで条件分岐

PR作りますか？それとも直接pushしますか？」
    ↓
成田さん: 「PR作って」
    ↓
Clawdbot: 「PR作成しました: https://github.com/.../pull/123」
```

---

### 4. 朝ブリーフィング（オプション）

**目的**: 毎朝の情報をSlack DMにまとめて送信

| 項目 | 値 |
|------|-----|
| 投稿先 | Slack DM (成田さん宛) |
| 時刻 | 毎日 7:00 JST |

**投稿フォーマット**:

```
☀️ おはようございます

📅 今日の予定
• 12:00 - 研究室ミーティング
• 15:00 - コードレビュー

📩 未読メール（重要度高）
• App Store: Your app is ready for review

💬 Slack未読
• #anicca-dev: 2件のメンション

📊 昨日のKPI
• インストール: 142 (+15%)
• MRR: $4,230
```

---

## インフラ構成

### 決定事項

| 項目 | 決定 | 理由 |
|------|------|------|
| **ホスティング** | VPS (Hetzner CX11) | 24/7稼働保証、プロアクティブ通知に必須 |
| **コスト** | €3.79/月 (≈$5) | Mac常時起動より信頼性が高い |
| **チャネル** | Slack のみ | Telegram/LINE は使用しない |
| **AIモデル** | Claude API | 既存のAPI Keyを使用 |

### VPS スペック (Hetzner CX11)

| 項目 | 値 |
|------|-----|
| CPU | 1 vCPU (Intel) |
| RAM | 2 GB |
| Storage | 20 GB NVMe |
| OS | Ubuntu 22.04 |
| 場所 | Falkenstein, DE (または Ashburn, US) |

---

## 導入タスクリスト

### Phase 0: インフラセットアップ（1-2時間）

| # | タスク | コマンド/手順 | 完了 |
|---|--------|--------------|------|
| 0.1 | Hetzner アカウント作成 | https://www.hetzner.com/cloud | ☐ |
| 0.2 | CX11 サーバー作成 | Ubuntu 22.04, Falkenstein | ☐ |
| 0.3 | SSH接続確認 | `ssh root@<IP>` | ☐ |
| 0.4 | Node.js 22 インストール | `curl -fsSL https://deb.nodesource.com/setup_22.x \| sudo -E bash - && sudo apt-get install -y nodejs` | ☐ |
| 0.5 | Clawdbot インストール | `npm install -g clawdbot@latest` | ☐ |
| 0.6 | オンボーディング実行 | `clawdbot onboard --install-daemon` | ☐ |

### Phase 1: 認証設定（30分）

| # | タスク | 詳細 | 完了 |
|---|--------|------|------|
| 1.1 | Claude API Key 設定 | ウィザードで入力 | ☐ |
| 1.2 | Slack App 作成 | https://api.slack.com/apps → Create New App | ☐ |
| 1.3 | Slack Bot Token 取得 | OAuth & Permissions → Bot User OAuth Token | ☐ |
| 1.4 | Slack チャネル連携 | `clawdbot channels add slack` | ☐ |
| 1.5 | 初回テスト | Slack DMで「Hello」→ 応答確認 | ☐ |

### Phase 2: スキル導入（30分）

| # | スキル | コマンド | 用途 |
|---|--------|---------|------|
| 2.1 | Slack | `clawdbot skills add slack` | Slackメッセージ操作 |
| 2.2 | Coding Agent | `clawdbot skills add coding-agent` | コード作業依頼 |
| 2.3 | カレンダー | `clawdbot skills add caldav-calendar` | 祝日判定、予定確認 |
| 2.4 | リマインダー | `clawdbot skills add remind-me` | 通知設定 |
| 2.5 | Brave Search | `clawdbot skills add brave-search` | Web検索 |

### Phase 3: 自動化ルーチン設定（1-2時間）

| # | ルーチン | 時刻 | 設定内容 |
|---|---------|------|---------|
| 3.1 | 朝ブリーフィング | 毎日 7:00 JST | カレンダー + Slack + メール → DM |
| 3.2 | KPI自動投稿 | 毎日 9:00 JST | ASC + RevenueCat + Superwall → #anicca-kpi |
| 3.3 | 月曜アナウンス | 毎週月曜 11:00 JST | 祝日チェック → 研究室Slack |

### Phase 4: Anicca リポジトリ連携（30分）

| # | タスク | 詳細 | 完了 |
|---|--------|------|------|
| 4.1 | リポジトリ clone | VPS上に anicca-project を clone | ☐ |
| 4.2 | GitHub SSH Key 設定 | VPSからGitHubにpush可能にする | ☐ |
| 4.3 | ワークスペース設定 | `clawdbot configure --workspace ~/anicca-project` | ☐ |
| 4.4 | テスト | 「Phase 6のタスク教えて」→ spec読み取り確認 | ☐ |

---

## Slack App 設定詳細

### 必要な OAuth Scopes

```
channels:history    - チャンネルメッセージ読み取り
channels:read       - チャンネル一覧取得
chat:write          - メッセージ投稿
im:history          - DM読み取り
im:read             - DM一覧取得
im:write            - DM送信
users:read          - ユーザー情報取得
```

### Event Subscriptions

```
message.channels    - チャンネルメッセージ受信
message.im          - DM受信
app_mention         - メンション受信
```

### Request URL

```
http://<VPS_IP>:18789/webhooks/slack
```

---

## Cron 設定詳細

### 朝ブリーフィング (7:00 JST)

```yaml
# ~/.clawdbot/cron.yaml
- name: morning_briefing
  schedule: "0 22 * * *"  # UTC 22:00 = JST 7:00
  action: message
  channel: slack
  target: "@daisuke"  # Slack user ID に置き換え
  message: |
    ☀️ おはようございます
    
    📅 今日の予定を確認しています...
    📩 メールをチェックしています...
    💬 Slack未読を確認しています...
```

### KPI自動投稿 (9:00 JST)

```yaml
- name: daily_kpi
  schedule: "0 0 * * *"  # UTC 0:00 = JST 9:00
  action: message
  channel: slack
  target: "#anicca-kpi"
  message: |
    📊 Anicca Daily KPI を取得しています...
```

### 月曜アナウンス (11:00 JST)

```yaml
- name: monday_meeting
  schedule: "0 2 * * 1"  # UTC 2:00 = JST 11:00, Monday only
  action: script
  script: |
    # 祝日チェック
    if is_holiday_japan(); then
      exit 0  # 祝日なら何もしない
    fi
    # アナウンス投稿
    send_slack "#naist-lab" "📢 本日12:00からミーティングがあります。出席できない方は事前にご連絡ください。"
```

---

## コスト見積もり

| 項目 | 月額 |
|------|------|
| Hetzner VPS (CX11) | $5 |
| Claude API (従量制) | ~$10-20 |
| Brave Search API | $0 (無料枠) |
| **合計** | **$15-25/月** |

---

## セキュリティ考慮事項

1. **SSH Key認証**: パスワード認証は無効化
2. **Firewall**: 必要なポートのみ開放 (22, 18789)
3. **API Keys**: 環境変数で管理、リポジトリにコミットしない
4. **Slack App**: 必要最小限のスコープのみ付与

---

## トラブルシューティング

### Gateway が起動しない

```bash
clawdbot gateway status
clawdbot gateway --verbose  # 詳細ログ
```

### Slack メッセージが届かない

```bash
clawdbot channels list
clawdbot channels test slack
```

### Cron が動かない

```bash
clawdbot cron list
clawdbot cron test <name>
```

---

## 将来の拡張（オプション）

| 拡張 | 説明 | 優先度 |
|------|------|--------|
| SNS自動投稿 | X/Twitter への投稿 (`bird` スキル) | 中 |
| Google Drive連携 | ファイル取得・保存 (`gog` スキル) | 低 |
| Todoist連携 | タスク管理 (`todoist` スキル) | 低 |
| 音声入力 | macOS app 経由 | 低 |

---

## 参考リンク

- [Clawdbot Getting Started](https://docs.clawd.bot/start/getting-started)
- [Slack Channel Setup](https://docs.clawd.bot/channels/slack)
- [Skills Config](https://docs.clawd.bot/tools/skills-config)
- [Cron Jobs](https://docs.clawd.bot/automation)
- [Henry Mascot の事例](https://medium.com/@henrymascot/my-almost-agi-with-clawdbot-cd612366898b)

---

## 実装担当

- [ ] Phase 0: インフラセットアップ
- [ ] Phase 1: 認証設定
- [ ] Phase 2: スキル導入
- [ ] Phase 3: 自動化ルーチン設定
- [ ] Phase 4: Anicca リポジトリ連携

---

## 承認

- [ ] 仕様レビュー完了
- [ ] 実装開始承認

