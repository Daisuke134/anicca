# OpenClaw 完全実装 Spec（1.6.1.5）

**最終更新**: 2026-02-05 17:30 JST
**ステータス**: 実装中

---

## 1. 概要（What & Why）

### What
Anicca を OpenClaw wrapper として完全に実装し、Slack #metrics チャンネルで `@Anicca` としてメンション応答できるようにする。

### Why
- 毎朝の metrics レポートを自動化
- `@Anicca MRRは？` などの質問にリアルタイム応答
- 開発チームの KPI 可視化を効率化

### ゴール
| 機能 | 説明 |
|------|------|
| `@Anicca` メンション応答 | Slack #metrics で質問 → 自動返答 |
| Daily Metrics 自動投稿 | 毎朝9:00 JST に統合レポート投稿 |
| ミーティングリマインダー | 日曜21:00、月曜11:25 に自動投稿 |

---

## 2. 現状分析（As-Is）

### 完了済み
| 項目 | 状態 |
|------|------|
| OpenClaw CLI | v2026.2.2-3 インストール済み |
| Gateway | port 18789 で稼働中 (pid 62903) |
| LaunchAgent | ai.openclaw.gateway.plist 設定済み |
| Slack tokens | xoxb-, xapp- 設定済み |
| Channel 設定 | C091G3PKHL2 (#metrics) 設定済み |
| Cron Jobs | 3件登録済み（ただし失敗中） |
| Agent 設定 | "anicca" agent 作成済み |

### 問題点（Critical Issues）
| 問題 | 原因 | 影響 |
|------|------|------|
| **Slack App 名が "OpenClaw"** | Slack API でアプリ名未変更 | `@OpenClaw` でメンションされる |
| **`requireMention: false`** | 設定ミス | 全メッセージに応答してスパム化 |
| **Cron 失敗** | OpenAI Key が isolated session で見つからない | Daily metrics 投稿されない |
| **mentionPatterns 未設定** | routing 設定なし | @Anicca でマッチしない |
| **IDENTITY.md 未作成** | workspace 設定不完全 | ペルソナが定義されていない |
| **SOUL.md 未作成** | workspace 設定不完全 | 行動指針が定義されていない |
| **RevenueCat/ASC credentials 未設定** | plist に未追加 | 統合レポート生成不可 |

---

## 3. 受け入れ条件

| # | 条件 | テスト方法 |
|---|------|-----------|
| AC1 | Slack App 表示名が "Anicca" | Slack で確認 |
| AC2 | `@Anicca hello` で応答が返る | Slack #metrics でテスト |
| AC3 | `@OpenClaw` でも応答する（後方互換） | Slack でテスト |
| AC4 | メンションなしのメッセージには応答しない | 通常メッセージ送信で確認 |
| AC5 | `@Anicca MRRは？` で RevenueCat データ返却 | Slack でテスト |
| AC6 | `@Anicca トライアル数は？` で Mixpanel データ返却 | Slack でテスト |
| AC7 | 毎朝9:00 JST に統合レポート自動投稿 | Cron 手動実行でテスト |
| AC8 | 統合レポートに Mixpanel + RevenueCat + ASC 含む | 投稿内容確認 |

---

## 4. To-Be 設計

### 4.1 Slack App 設定変更

| 項目 | Before | After |
|------|--------|-------|
| App Name | OpenClaw | Anicca |
| Display Name | OpenClaw | Anicca |
| Description | AIアシスタント | Anicca - 行動変容AIアシスタント |

**作業場所**: https://api.slack.com/apps → Basic Information → App name

### 4.2 openclaw.json 修正

```json
{
  "identity": {
    "name": "Anicca",
    "theme": "compassionate behavior change assistant",
    "emoji": "🧘"
  },
  "routing": {
    "groupChat": {
      "mentionPatterns": ["@anicca", "anicca", "@openclaw", "openclaw"]
    }
  },
  "channels": {
    "slack": {
      "channels": {
        "C091G3PKHL2": {
          "allow": true,
          "requireMention": true
        }
      }
    }
  }
}
```

### 4.3 IDENTITY.md 作成

**パス**: `~/.openclaw/workspace/IDENTITY.md`

```markdown
# Identity

Name: Anicca
Emoji: 🧘
Theme: Compassionate behavior change assistant

## Personality
- 共感的で非批判的
- 簡潔で要点を押さえた応答
- 絵文字を適度に使用
- 日本語で応答（英語の質問には英語で）
```

### 4.4 SOUL.md 作成

**パス**: `~/.openclaw/workspace/SOUL.md`

```markdown
# Soul

## Core Values
- ユーザーの挫折を責めない
- 小さな進歩を称える
- 6-7年間変われなかった人への共感

## Boundaries
- 医療アドバイスはしない
- 診断は行わない
- 専門家への相談を促す

## Communication Style
- 簡潔に、要点のみ
- 専門用語を避ける
- 具体的なアクションを提案
```

### 4.5 LaunchAgent plist 更新

**追加する環境変数**:
```xml
<key>REVENUECAT_V2_SECRET_KEY</key>
<string>sk_YTtULZGUcQuIepNzNOasKQYsKmZJX</string>
<key>ASC_KEY_ID</key>
<string>[GitHub Secrets から取得]</string>
<key>ASC_ISSUER_ID</key>
<string>[GitHub Secrets から取得]</string>
```

### 4.6 auth-profiles.json 設定

**パス**: `~/.openclaw/agents/anicca/agent/auth-profiles.json`

```json
{
  "openai": {
    "apiKey": "sk-proj-..."
  }
}
```

### 4.7 Cron Jobs 再設定

**既存ジョブ削除 → 新規作成**

```bash
# daily-metrics-reporter
openclaw cron add \
  --name "daily-metrics-reporter" \
  --cron "0 9 * * *" \
  --tz "Asia/Tokyo" \
  --session isolated \
  --agent anicca \
  --message "Execute daily metrics report:

## Task
Generate and post the daily Anicca metrics report to Slack #metrics.

## Data Sources
1. **Mixpanel** (Project ID: 3970220)
   - Events: first_app_opened, onboarding_started, onboarding_paywall_viewed, rc_trial_started_event
   - Period: Last 7 days
   - Use curl with Basic Auth (API Secret: from env var MIXPANEL_API_SECRET)

2. **RevenueCat** (Project ID: projbb7b9d1b)
   - Metrics: MRR, Active Subs, Active Trials, Churn Rate
   - Use curl with Bearer token (from env var REVENUECAT_V2_SECRET_KEY)

## Output Format
Post to Slack #metrics (C091G3PKHL2) using slack tool:

📊 Anicca Daily Metrics (YYYY-MM-DD)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 REVENUE (RevenueCat)
  MRR: $X
  Active Subs: X
  Active Trials: X
  Monthly Churn: X%

🔄 ONBOARDING FUNNEL (Mixpanel - 7日)
  first_app_opened: X (100%)
  onboarding_started: X (X%)
  paywall_viewed: X (X%)
  trial_started: X (X%)

## Instructions
1. Fetch data from each source using curl
2. Calculate conversion rates
3. Format the report
4. Post to Slack using the slack tool" \
  --announce \
  --channel slack \
  --to "channel:C091G3PKHL2"
```

---

## 5. テストマトリックス

| # | To-Be | テスト名 | 方法 |
|---|-------|----------|------|
| 1 | Slack App 名変更 | `test_slack_app_name` | Slack UI で確認 |
| 2 | requireMention: true | `test_mention_only_response` | 通常メッセージ → 無応答確認 |
| 3 | @Anicca メンション応答 | `test_anicca_mention` | `@Anicca hello` → 応答確認 |
| 4 | @OpenClaw 後方互換 | `test_openclaw_mention` | `@OpenClaw hello` → 応答確認 |
| 5 | MRR クエリ | `test_mrr_query` | `@Anicca MRRは？` → RevenueCat データ |
| 6 | Trial クエリ | `test_trial_query` | `@Anicca トライアル数` → Mixpanel データ |
| 7 | Daily Cron 実行 | `test_daily_cron` | `openclaw cron run <id> --force` |
| 8 | 統合レポートフォーマット | `test_report_format` | Slack 投稿内容確認 |

---

## 6. 境界（Boundaries）

### やること
- Slack App 名変更（"OpenClaw" → "Anicca"）
- openclaw.json の修正（requireMention, mentionPatterns）
- IDENTITY.md / SOUL.md 作成
- plist への credentials 追加
- auth-profiles.json 設定
- Cron Jobs 再設定
- Gateway 再起動
- テスト実行

### やらないこと
- iOS アプリの変更
- API サーバーの変更
- X/TikTok 投稿機能（1.6.2 スコープ）
- ASC 完全統合（Sales Reports API は時間がかかるため、1.6.2 で対応）

---

## 7. 実行手順

### Phase 1: 設定修正

```bash
# 1. Slack App 名変更（GUI作業）
# https://api.slack.com/apps → Basic Information → App name → "Anicca"

# 2. openclaw.json 修正
# ~/.openclaw/openclaw.json を編集

# 3. IDENTITY.md 作成
cat > ~/.openclaw/workspace/IDENTITY.md << 'EOF'
# Identity
...
EOF

# 4. SOUL.md 作成
cat > ~/.openclaw/workspace/SOUL.md << 'EOF'
# Soul
...
EOF

# 5. plist 更新
# ~/Library/LaunchAgents/ai.openclaw.gateway.plist を編集

# 6. auth-profiles.json 設定
mkdir -p ~/.openclaw/agents/anicca/agent
cat > ~/.openclaw/agents/anicca/agent/auth-profiles.json << 'EOF'
{
  "openai": {
    "apiKey": "sk-proj-..."
  }
}
EOF
```

### Phase 2: Gateway 再起動

```bash
launchctl unload ~/Library/LaunchAgents/ai.openclaw.gateway.plist
launchctl load ~/Library/LaunchAgents/ai.openclaw.gateway.plist
openclaw gateway status
```

### Phase 3: Cron Jobs 再設定

```bash
# 既存ジョブ削除
openclaw cron remove 9ea836ce-75cc-48b7-be70-89cfe0c0a958
openclaw cron remove 5fa97054-022f-4da4-874a-7c0fc12900b0
openclaw cron remove f6155e45-3aa8-4798-93ba-6a968da8cedc

# 新規ジョブ作成（上記参照）
```

### Phase 4: テスト

```bash
# 1. Gateway 状態確認
openclaw gateway status
openclaw health

# 2. Slack メンションテスト（GUI）
# @Anicca hello

# 3. Cron 手動実行
openclaw cron run <new-job-id> --force
```

---

## 8. E2E 判定

| 項目 | 値 |
|------|-----|
| UI変更 | なし（Slack のみ） |
| Maestro E2E | 不要（iOS アプリ変更なし） |
| 手動テスト | 必要（Slack でのメンション応答確認） |

---

## 9. ユーザー作業（GUI）

| # | タスク | 手順 |
|---|--------|------|
| 1 | Slack App 名変更 | https://api.slack.com/apps → Basic Information → "Anicca" |
| 2 | ASC credentials 取得 | GitHub Secrets から ASC_KEY_ID, ASC_ISSUER_ID をコピー |

---

## 10. 認証情報一覧

| サービス | 項目 | 値 | 設定先 |
|---------|------|-----|--------|
| OpenAI | API Key | sk-proj-... | plist + auth-profiles.json |
| Mixpanel | Project ID | 3970220 | plist |
| Mixpanel | API Secret | b613eff96fec412ca7fa307942333e2c | plist |
| RevenueCat | Project ID | projbb7b9d1b | Cron message |
| RevenueCat | V2 Secret Key | sk_YTtULZGUcQuIepNzNOasKQYsKmZJX | plist |
| Slack | Bot Token | xoxb-... | openclaw.json |
| Slack | App Token | xapp-... | openclaw.json |
| Slack | Channel ID | C091G3PKHL2 | openclaw.json |

---

## 11. ファイル変更一覧

| ファイル | 操作 |
|---------|------|
| `~/.openclaw/openclaw.json` | 編集（identity, routing, requireMention） |
| `~/.openclaw/workspace/IDENTITY.md` | 新規作成 |
| `~/.openclaw/workspace/SOUL.md` | 新規作成 |
| `~/Library/LaunchAgents/ai.openclaw.gateway.plist` | 編集（RevenueCat credentials 追加） |
| `~/.openclaw/agents/anicca/agent/auth-profiles.json` | 新規作成 |

---

## 12. リスク & 対策

| リスク | 対策 |
|--------|------|
| Gateway 再起動後に接続失敗 | `openclaw gateway status` で確認、ログ確認 |
| Cron が再び失敗 | auth-profiles.json の設定を確認 |
| Slack メンションが動かない | mentionPatterns の設定確認 |
| API rate limit | curl に retry logic 追加（将来対応） |

---

## 13. 完了条件

- [ ] Slack App 表示名が "Anicca"
- [ ] `@Anicca hello` で応答
- [ ] 通常メッセージに無応答
- [ ] `@Anicca MRRは？` で RevenueCat データ返却
- [ ] Daily Cron 手動実行で Slack 投稿成功
