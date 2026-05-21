# 1.6.1 仕様書: Mixpanel + OpenClaw + オンボーディング + Paywall改善

**作成日**: 2026-02-04  
**ステータス**: 🔴 1.6.1 必須（全て実装するまでマージ禁止）

---

## 目次

1. [問題サマリー](#問題サマリー)
2. [Patch A: Mixpanelトラッキング修正](#patch-a-mixpanelトラッキング修正)
3. [Patch B: RevenueCat A/Bテスト設定（GUI）](#patch-b-revenuecat-abテスト設定gui)
4. [Patch C: OpenClaw日次メトリクス移行](#patch-c-openclaw日次メトリクス移行)
5. [Patch D: @Anicca Slackメンション応答](#patch-d-anicca-slackメンション応答)
6. [Patch E: オンボーディング改善](#patch-e-オンボーディング改善)
7. [アーキテクチャ図](#アーキテクチャ図)
8. [OpenClaw使用例](#openclaw使用例)

---

## 問題サマリー

| # | 問題 | 重大度 | 根本原因 | 解決方法 |
|---|------|--------|---------|---------|
| A-1 | `onboarding_paywall_purchased`が15件（虚偽） | 🔴 Critical | iOSクライアントサイドで発火、DEBUG/サンドボックス/開発者テスト含む | **このイベントを使わない。`rc_trial_started_event`を信頼** |
| A-2 | `rc_trial_started_event`が0件 | ✅ 正常 | **本番で誰もトライアル開始していない（正しいデータ）** | 修正不要。これが正しいデータ |
| A-3 | ファネルの整合性がない | 🟡 Medium | iOSの自前イベントとRevenueCatサーバーサイドイベントを混在 | RevenueCatイベントに統一 |
| B-1 | Paywall A/Bテストなし | 🟡 High | 未設定 | RevenueCat Experiments設定 |
| C-1 | GitHub Actionsで日次メトリクス | 🟡 Medium | OpenClawに移行したい | OpenClaw cron設定 |
| D-1 | @Aniccaメンション応答なし | 🟢 Low | 未実装 | Slack Bolt + OpenClaw |
| E-1 | オンボーディング変換率が低い（0%） | 🔴 Critical | Paywall到達後、誰もトライアル開始していない | Paywall改善 + A/Bテスト |

---

## 重要な発見: データの真実

### RevenueCat→Mixpanel統合の仕組み

RevenueCat公式ドキュメントより:
> **"Sends Sandbox Events: Requires Token"**
> サンドボックスイベントを送信するには**別のトークン**が必要。
> サンドボックストークンを設定しなければ、**本番トランザクションのみ**がMixpanelに送信される。

### 正しいデータソース

| イベント | ソース | 信頼性 | 説明 |
|---------|-------|-------|------|
| `rc_trial_started_event` | RevenueCat → Mixpanel（サーバーサイド） | ✅ **正確** | sandbox token未設定なら本番のみ |
| `onboarding_paywall_purchased` | iOS SDK（クライアントサイド） | ❌ **不正確** | DEBUG/サンドボックス/開発者テスト含む |

### 結論

**`rc_trial_started_event=1件（1ヶ月）` は正しいデータ。**

### 実データサマリー

> **データソース注意:**
> - **1ヶ月データ（2026-01-04〜02-04）:** `rc_trial_started_event=1件`（本セクション）
> - **16日間データ（2026-01-21〜02-05）:** `rc_trial_started_event=0件`（E-0セクション）
> - 期間が異なるため件数の差は矛盾ではない。1件のトライアルは16日間の範囲外（それ以前）に発生。

**参考指標（ファネル外）:**

| イベント | 1ヶ月合計 | 備考 |
|---------|----------|------|
| `app_opened` | **667** | 全アプリ起動（リピーター含む）。ファネルには使わない。 |

**オンボーディングファネル（`onboarding_started`起点）:**

| イベント | 1ヶ月合計 | 変換率 | 備考 |
|---------|----------|-------|------|
| `onboarding_started` | **271** | 100% | ファネル起点（新規ユーザーのみ） |
| `onboarding_paywall_viewed` | **130** | 48.0% | - |
| `rc_trial_started_event` | **1** | **0.77%** (from paywall) | 本番トライアルのみ |

### 問題の核心

271人がオンボーディングを開始し、130人がPaywallを見て、**たった1人**がトライアルを開始。

**Paywallの変換率: 0.77%** ← これが問題。業界平均は5-10%。

---

## Patch A: Mixpanelトラッキング修正

### A-1: 正しいデータソースを使う（コード変更不要）

**問題:** `onboarding_paywall_purchased`=15件は虚偽データ（DEBUG/サンドボックス/開発者テスト含む）

**解決策:** このイベントを無視し、RevenueCatの`rc_trial_started_event`を信頼する

**修正内容:** コード変更なし。ダッシュボード/レポートで使用するイベントを変更するだけ。

| 今まで使っていたイベント | 今後使うイベント |
|------------------------|----------------|
| `onboarding_paywall_purchased`（iOS SDK） | `rc_trial_started_event`（RevenueCat） |

**理由:**
- RevenueCat→Mixpanel統合はサーバーサイドで送信
- サンドボックストークンを設定しなければ、本番トランザクションのみ送信される
- クライアントサイドの自前イベントは開発者テストも含まれてしまう

---

### A-2: RevenueCat Dashboard確認

**確認場所:** RevenueCat Dashboard → Project → Integrations → Mixpanel

| 設定項目 | 推奨値 |
|---------|-------|
| Production Token | Mixpanelのプロジェクトトークン（設定済みのはず） |
| **Sandbox Token** | **空欄にする**（サンドボックスイベントを送信しない） |

これにより、本番トランザクションのみがMixpanelに送信される。

---

### A-3: ファネル定義を更新

**Mixpanelのファネルを以下のイベントで構成:**

| ステップ | イベント | ソース | 備考 |
|---------|---------|-------|------|
| 1 | `onboarding_started` | iOS SDK | **ファネル起点**（新規ユーザーのみ発火） |
| 2 | `onboarding_welcome_completed` | iOS SDK | - |
| 3 | `onboarding_value_completed` | iOS SDK | - |
| 4 | `onboarding_struggles_completed` | iOS SDK | - |
| 5 | `onboarding_notifications_completed` | iOS SDK | - |
| 6 | `onboarding_paywall_viewed` | iOS SDK | - |
| 7 | `rc_trial_started_event` | **RevenueCat** | サーバーサイド（正確） |

**重要:**
- ファネル起点は`onboarding_started`を使用。`app_opened`は既存ユーザー含むためファネル分析に不適。
- `first_app_opened`は別用途（初回インストール数の計測）として追加するが、ファネル起点には使わない。
- `onboarding_att_completed`はファネルから除外。ATTはiOSシステムダイアログで離脱率が高くないため。

### A-3.1: Mixpanel UIでのファネル設定手順

**場所:** Mixpanel Dashboard → Funnels → Create Funnel

| ステップ | 操作 |
|---------|------|
| 1 | 「Create Funnel」をクリック |
| 2 | ファネル名: `Onboarding Funnel v1.6.1` |
| 3 | Step 1: `onboarding_started` を選択 |
| 4 | Step 2-6: 上記テーブルの順でイベント追加 |
| 5 | Step 7: `rc_trial_started_event` を選択 |
| 6 | Conversion Window: 14 days |
| 7 | 「Save」をクリック |

**注意:** Mixpanel MCPの`run_funnels_query`はクエリ実行用であり、ファネル定義の保存には使えない。ファネル定義はMixpanel UIで行う。

---

## Patch B: RevenueCat A/Bテスト設定（GUI）

### 設定手順（ダッシュボード操作）

RevenueCat APIにはExperiments作成機能がないため、ダッシュボードで手動設定が必要。

#### Step 1: 新しいOfferingを作成

1. RevenueCat Dashboard → Project `projbb7b9d1b` → Offerings
2. 「+ New」をクリック
3. 設定:
   - **Identifier**: `anicca_treatment_a`
   - **Display Name**: `Anicca Treatment A - Social Proof`
4. 既存の`anicca`オファリングと同じパッケージ（`ai.anicca.app.ios.monthly`）を追加

#### Step 2: 新しいPaywallを作成

1. Paywalls → 「+ Create Paywall」
2. テンプレート選択またはカスタム
3. **変更点（Treatment A）:**
   - ヘッダーに社会的証明追加（数値なし: 「多くの人が安らぎを見つけています」）
   - 価格表示を「1日たったの¥33」に変更
   - 無料トライアルを強調（期間は製品設定依存）

#### Step 3: Experimentを作成

1. Experiments → 「+ New」
2. 設定:
   - **Name**: `Paywall Design Test - Social Proof`
   - **Experiment type**: `Paywall design`
   - **Primary metric**: `Initial conversion rate`
   - **Variant A (Control)**: `anicca` (現在のOffering)
   - **Variant B (Treatment)**: `anicca_treatment_a`
   - **Audience**: `Any audience`
   - **Percentage**: `50%`

#### Step 4: 実験開始

1. 設定確認後、「Start Experiment」をクリック
2. 最低1-2週間データ収集（A/Bテスト業界標準。※上記の16日間はファネル分析期間であり、実験期間とは別）

### 現在のPaywallの問題点と改善案

| 問題点 | 改善案 | 根拠 |
|--------|--------|------|
| 社会的証明なし | 社会的証明追加（数値なし） | 信頼性向上 |
| 価格が高く見える | 「1日¥33」表示 | 価格アンカリング |
| トライアルが目立たない | サイズ/色を強調 | トライアル開始を促進 |
| 個人化なし | 「あなたの○○に対応」 | Struggles選択を活用 |

### B-4: Paywall個人化（Strugglesを活用）

**目的:** オンボーディングで選択したStrugglesをPaywallに表示し、「このアプリは自分のためのもの」と感じさせる。

**実装方法:** RevenueCat Subscriber Attributesを使用

---

#### ファイル: `aniccaios/aniccaios/Onboarding/OnboardingFlowView.swift`

**追加位置:** Paywallを表示する前（`showPaywall = true`の直前）

**Before:**
```swift
// Struggles選択後、すぐPaywallを表示
showPaywall = true
```

**After:**

> **前提:**
> - OnboardingFlowViewには既に`import RevenueCat`がある
> - SubscriptionManagerがアプリ起動時にconfigureを完了しているため、Purchases.sharedは使用可能
> - `setAttributes`は非同期だがPaywall表示をブロックしない設計（属性はバックグラウンドで同期）

```swift
// Struggles選択結果をRevenueCatに送信（Paywall表示前）
// Note: setAttributesは非同期だが、Paywall表示を待たせない。
//       RevenueCat Dashboard変数は初回表示では反映されない可能性があるため、
//       1.6.1ではPaywallコピーにstatic文言を使用する。
if let selectedStruggles = selectedStruggles {  // オンボーディング中のローカル状態を使用
    let topStruggle = selectedStruggles.first?.rawValue ?? "general"
    Purchases.shared.setAttributes([
        "top_struggle": topStruggle,
        "struggle_count": "\(selectedStruggles.count)"
    ])
}
showPaywall = true
```

> **注意:** `AppState.shared.userProfile?.struggles`ではなく、オンボーディング中のローカル状態`selectedStruggles`を直接参照する。これによりサーバー同期前でもstafflesデータを使用可能。

---

#### RevenueCat Dashboard設定

1. Paywallテンプレートの「subtitle」または「features」に変数を使用
2. 例: `Perfect for {{subscriber.attributes.top_struggle}}`
3. または静的に「あなたの課題に対応」と表示（日本語の場合）

**注意:** RevenueCatのPaywall変数機能は限定的。複雑な個人化はiOS側でPaywallView上書きが必要だが、1.6.1では静的なメッセージで十分。

---

## Patch C: OpenClaw日次メトリクス移行

> **スコープ注意:** Patch C/Dは設計仕様のみ。詳細実装（認証情報、API呼び出し、ビルド設定）はVPSセットアップ時にOpenClawエージェントが行う。iOSアプリ変更（Patch A/B/E）を優先する。

### 目標

GitHub Actions (`daily-metrics.yml`) → OpenClaw skill (`daily-metrics-reporter`) に移行

### C-1: OpenClaw schedule.yaml への追加

**ファイル**: VPS `/home/anicca/openclaw/schedule.yaml`

```yaml
skills:
  # 既存skills
  moltbook-responder:
    interval: "5m"
    
  feedback-fetch:
    interval: "30m"
    
  slack-reminder:
    cron:
      - "0 21 * * 0"   # 日曜 21:00 JST
      - "25 12 * * 1"  # 月曜 12:25 JST
    timezone: "Asia/Tokyo"

  # 新規追加
  daily-metrics-reporter:
    cron: "0 9 * * *"  # 毎朝9:00 JST
    timezone: "Asia/Tokyo"
    on_error: "log_and_continue"
```

### C-2: Slackに投稿される内容（詳細）

**毎朝9:00 JSTにAnicca/OpenClawが #metrics に投稿する内容:**

> **注意:** 以下は**サンプルフォーマット**（実データではない）。実際の数値はMCP経由でリアルタイム取得される。

```
📊 Anicca Daily Metrics (2026-02-04)  ← サンプル
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 REVENUE (RevenueCat)
  MRR: $XX.XX
  Active Subs: X
  Active Trials: X

📥 INSTALLS (App Store Connect, 過去7日)
  合計: XX
  国別: JP: XX | US: XX | Others: XX
  first_app_opened: XX（初回起動数、インストール数計測用）

🔄 ONBOARDING FUNNEL (Mixpanel, 過去7日)
  期間: YYYY-MM-DD 〜 YYYY-MM-DD

  onboarding_started:          XXX (100.0%)  ← ファネル起点
  onboarding_welcome_completed: XXX (XX.X%)
  onboarding_value_completed:   XXX (XX.X%)
  onboarding_struggles_completed: XXX (XX.X%)
  onboarding_notifications_completed: XX (XX.X%)
  onboarding_paywall_viewed:    XX (XX.X%)
  rc_trial_started_event:        X (X.X%) ← ★要改善

📈 WEEK OVER WEEK
  Trial Starts: 0 → 0 (±0%)
  Paywall Views: 75 → 81 (+8.0%)

⚠️ ALERTS
  🔴 Trial conversion rate: 0.0% (target: 5%)
  🔴 No trials started this week
  🟡 Paywall → Trial drop-off: 100%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**ポイント:**
- 期間を明記（過去7日）
- 各ステップの変換率を表示
- Week over Week比較
- アラート（目標未達の場合）

### C-3: OpenClaw Cron設定

**方法1: CLIで設定**
```bash
openclaw cron add daily-metrics-reporter \
  --schedule "0 9 * * *" \
  --timezone "Asia/Tokyo" \
  --command "Fetch Mixpanel funnel data, RevenueCat metrics, and ASC downloads. Post summary to #metrics Slack channel."
```

**方法2: HEARTBEAT.mdで設定**

`~/.openclaw/workspace/HEARTBEAT.md`:
```markdown
# Heartbeat Tasks

## 毎朝9:00 JST
- Mixpanel APIでオンボーディングファネルクエリ（過去7日）
- RevenueCat APIでMRR/Active Subs/Trials取得
- ASC APIでダウンロード数取得
- 結果を #metrics Slackチャンネルに投稿

## 毎週月曜12:25 JST
- #meeting にラボミーティングリマインダー投稿
```

### C-4: daily-metrics-reporter skill実装

**ディレクトリ構造:**
```
/home/anicca/openclaw/skills/daily-metrics-reporter/
├── SKILL.md           # スキル定義
├── index.ts           # エントリポイント
└── package.json       # 依存関係
```

**ファイル: `/home/anicca/openclaw/skills/daily-metrics-reporter/SKILL.md`**
```markdown
# Daily Metrics Reporter

毎朝9:00 JSTにMixpanel/RevenueCat/ASCからデータを取得し、#metricsに投稿。

## 実行条件
- cron: "0 9 * * *" (毎朝9:00 JST)

## 必要なAPI
- Mixpanel: `run_funnels_query`
- RevenueCat: `get_overview`
- ASC: Sales Reports API

## 出力先
- Slack #metrics チャンネル
```

**実装方針:** OpenClawはMCPを通じてMixpanel/RevenueCat APIにアクセスする。専用クライアント実装は不要。

**ファイル: `/home/anicca/openclaw/skills/daily-metrics-reporter/SKILL.md`（実装詳細）**
```markdown
## 実装

このスキルはOpenClawのMCP統合を使用してデータを取得する。

### 使用するMCPツール

1. **Mixpanel MCP** (`user-mixpanel`)
   - `run_funnels_query`: ファネルデータ取得
   - `run_segmentation_query`: イベントカウント

2. **RevenueCat MCP** (`user-revenuecat`)
   - `list_offerings`: Offering一覧
   - RevenueCat Dashboard APIは直接HTTPで呼び出し

3. **Slack** (OpenClaw組み込み)
   - `Slack.postMessage`: メッセージ投稿

### 環境変数（VPS .env）

| 変数名 | 説明 |
|-------|------|
| `MIXPANEL_PROJECT_ID` | `3970220` |
| `REVENUECAT_PROJECT_ID` | `projbb7b9d1b` |
| `SLACK_BOT_TOKEN` | Anicca Bot Token |

### 実行フロー

1. Mixpanel MCPで`run_funnels_query`を呼び出し
2. RevenueCat Dashboard API（HTTP）でMRR/Subs取得
3. 結果をフォーマット
4. Slack #metricsに投稿
```

**注意:** Patch C/Dの完全な実装はVPS上で行う。この仕様書はiOSアプリ変更を優先し、OpenClaw skill実装の詳細はVPSセットアップ時に確定する。

### C-5: GitHub Actions削除

**ファイル**: `.github/workflows/daily-metrics.yml`

移行完了後に削除（または`disabled`に変更）

```yaml
# Before: active
on:
  schedule:
    - cron: '0 0 * * *'

# After: disabled
# on:
#   schedule:
#     - cron: '0 0 * * *'
```

---

## Patch D: @Anicca Slackメンション応答

### 必要な情報

**環境変数（VPS `/home/anicca/openclaw/.env`に保存）:**

| 変数名 | 説明 | 取得方法 |
|-------|------|---------|
| `SLACK_BOT_TOKEN` | Anicca Bot Token | Slack App Settings → OAuth & Permissions |
| `SLACK_APP_TOKEN` | Socket Mode Token | Slack App Settings → Basic Information → App-Level Tokens |

### D-1: OpenClaw slack-helper skill

**ディレクトリ構造:**
```
/home/anicca/openclaw/skills/slack-helper/
├── SKILL.md           # スキル定義
├── index.ts           # エントリポイント（Slack Bolt）
└── package.json       # 依存関係
```

**ファイル: `/home/anicca/openclaw/skills/slack-helper/SKILL.md`**
```markdown
# Slack Helper

@Anicca メンションに応答する常駐skill。

## 機能

1. Slackでの@Aniccaメンション検出
2. メッセージ内容を解析
3. OpenClawの能力を使って処理
4. 結果をSlackに返信

## 対応クエリ例

- "昨日のPaywall変換率は？" → Mixpanel APIでクエリ
- "今週のトライアル開始数は？" → RevenueCat APIでクエリ
- "ASCのダウンロード数は？" → ASC APIでクエリ

## 環境変数

- SLACK_BOT_TOKEN
- SLACK_APP_TOKEN
```

**ファイル: `/home/anicca/openclaw/skills/slack-helper/index.ts`**
```typescript
import { App } from '@slack/bolt';
import { OpenClawAgent } from '@openclaw/agent';

const app = new App({
  token: process.env.SLACK_BOT_TOKEN,
  appToken: process.env.SLACK_APP_TOKEN,
  socketMode: true,
});

// @Anicca メンションを検出
app.event('app_mention', async ({ event, say }) => {
  const userMessage = event.text.replace(/<@[A-Z0-9]+>/g, '').trim();
  
  try {
    // OpenClawエージェントに処理を委譲
    const response = await OpenClawAgent.process({
      message: userMessage,
      context: {
        channel: event.channel,
        user: event.user,
        tools: ['mixpanel', 'revenuecat', 'asc'],
      },
    });
    
    await say({
      thread_ts: event.ts,
      text: response.text,
    });
  } catch (error) {
    await say({
      thread_ts: event.ts,
      text: `エラーが発生しました: ${error.message}`,
    });
  }
});

// 起動
(async () => {
  await app.start();
  console.log('⚡️ Anicca Slack bot is running!');
})();
```

### D-2: VPSでの設定

```bash
# 1. skills ディレクトリに移動
cd /home/anicca/openclaw/skills/slack-helper

# 2. 依存関係インストール
npm install @slack/bolt @openclaw/agent

# 3. 環境変数設定（.envファイルに追記）
# ※ 実際のトークンはプロジェクトの .env ファイル参照
cat >> /home/anicca/openclaw/.env << 'EOF'
SLACK_BOT_TOKEN=<your-bot-token>
SLACK_APP_TOKEN=<your-app-token>
EOF

# 4. schedule.yaml に常駐プロセスとして追加
cat >> /home/anicca/openclaw/schedule.yaml << 'EOF'
  slack-helper:
    mode: "daemon"  # 常駐プロセス
    restart: "always"
EOF

# 5. OpenClaw再起動
openclaw restart
```

---

## Patch E: オンボーディング改善

### E-0: 正確なファネル分析（Mixpanel Funnel Query）

**期間:** 2026-01-21 〜 2026-02-05（16日間）
**コンバージョンウィンドウ:** 14日
**カウント方式:** ユニークユーザー
**起点:** `onboarding_started`（`app_opened`は既存ユーザー含むため使用しない）

| # | ステップ | イベント | ユニークユーザー | 前ステップ変換率 | 離脱率 | 問題度 |
|---|---------|---------|---------------|----------------|--------|--------|
| 1 | オンボーディング開始 | `onboarding_started` | **131** | 100% | - | - |
| 2 | Welcome完了 | `onboarding_welcome_completed` | **105** | 80.2% | **19.8%** | 🟡 |
| 3 | Value完了 | `onboarding_value_completed` | **103** | 98.1% | 1.9% | ✅ |
| 4 | Struggles完了 | `onboarding_struggles_completed` | **103** | 100% | 0% | ✅ |
| 5 | Notifications完了 | `onboarding_notifications_completed` | **99** | 96.1% | 3.9% | ✅ |
| 6 | Paywall表示 | `onboarding_paywall_viewed` | **77** | 77.8% | **22.2%** | 🟡 |
| 7 | トライアル開始 | `rc_trial_started_event` | **0** | 0% | **100%** | 🔴 |

**課題ランキング:**

| 順位 | どこで離脱 | 離脱率 | 対策 | 1.6.1実装 |
|------|-----------|--------|------|-----------|
| 🔴 **1位** | Paywall → トライアル | **100%** | A/Bテスト | ✅ ユーザーがRevenueCat Dashboardで設定 |
| 🟡 **2位** | Notifications → Paywall | **22.2%** | 通知プレビュー追加 | ❌ 1.6.2で実装 |
| 🟡 **3位** | started → welcome_completed | **19.8%** | 社会的証明（1.6.1）+ 進捗バー（1.6.2） | ✅ 社会的証明のみ |

### E-0.1: `app_opened` vs `onboarding_started` の違い

| イベント | いつ発火 | ファネル起点として |
|---------|---------|-------------------|
| `app_opened` | **毎回**アプリを開くたびに発火 | ❌ 既存ユーザー含む、ノイズが多い |
| `onboarding_started` | オンボーディング画面が**表示された時**のみ | ✅ 新規ユーザーのみ、正確 |

**結論:** ファネルは `onboarding_started` から測定する。`app_opened` は残す（リテンション分析用）。

### E-1: 問題別分析と解決策

#### 🔴 P0: Paywall変換率 0%（77人中0人がトライアル開始）

| 項目 | 内容 |
|-----|------|
| **現状** | 77人がPaywallを見て、0人がトライアル開始（E-0ファネル表参照） |
| **原因** | Paywallが価値を伝えていない。社会的証明なし、価格アンカリングなし、パーソナライズなし |
| **解決策** | Paywall A/Bテスト（Variant B: 社会的証明、価格アンカリング追加） |
| **理由** | 業界平均のPaywall変換率は5-10%。0%は致命的に低い。Paywallデザイン自体を改善する必要がある |

#### ⚪ 参考指標（ファネル外）: app_opened → started

> **注意:** この指標はファネル分析には含めない。`app_opened`は既存ユーザーも含むため、新規ユーザーの離脱率として正確ではない。ファネルは`onboarding_started`から開始する。
>
> **期間注意:** 下記はE-0とは**別期間**のサンプルデータ（古いクエリ結果）。E-0期間（2026-01-21〜02-05）では`onboarding_started=131`。

| 項目 | 内容 |
|-----|------|
| **現状（参考）** | 古いクエリでは`app_opened`=135人、`onboarding_started`=102人だった。差の33人は**既存ユーザーの再起動**または**即閉じ** |
| **結論** | この差はファネル分析では無視する。ファネル起点は`onboarding_started`（新規ユーザーのみ発火）|

#### 🟡 P1: started → welcome_completed（19.8%離脱）

| 項目 | 内容 |
|-----|------|
| **現状** | 131人がオンボーディング開始、105人がWelcome完了。26人が離脱 |
| **原因** | CTAボタンが目立たない、または興味を失っている |
| **解決策** | 社会的証明追加（1.6.1）、進捗インジケーター追加（1.6.2） |
| **理由** | ユーザーがどこを押せばいいかわからない、または「自分のためのアプリ」と感じていない |

#### 🟡 P2: notifications → paywall（22.2%離脱）

| 項目 | 内容 |
|-----|------|
| **現状** | 99人が通知完了、77人がPaywall表示。22人が離脱 |
| **原因** | 通知許可後にアプリを閉じている可能性 |
| **解決策** | 通知許可の理由をより明確に説明。通知プレビューを表示（1.6.2で実装予定）|
| **理由** | ユーザーは「なぜ通知が必要か」を理解しないと許可しない |

### E-2: 全ローカライズ変更一覧

**対象ファイル:**
- EN: `aniccaios/aniccaios/Resources/en.lproj/Localizable.strings`
- JA: `aniccaios/aniccaios/Resources/ja.lproj/Localizable.strings`

**スコープ:** 1.6.1ではEN/JAのみ対象。es/fr/de/pt-BRは1.6.2で対応。

**キー配置:** 既存の`onboarding_*`グループに追加。新規キーは`// MARK: - Onboarding`セクション内に配置。

**形式:** `"key" = "value";`

---

#### Welcome画面 (WelcomeStepView.swift) — ✅ 1.6.1で実装

| Key | Before (EN) | After (EN) | 変更 |
|-----|------------|-----------|------|
| `onboarding_welcome_title` | `Welcome to\nAnicca` | `Welcome to\nAnicca` | **変更なし** |
| `onboarding_welcome_subtitle_line1` | `Anicca reaches out to you` | `Anicca sends you the right words` | ✅ |
| `onboarding_welcome_subtitle_line2` | `at the moments you struggle most.` | `before you spiral—not after.` | ✅ |
| `onboarding_welcome_cta` | `Get Started` | `Get Started` | **変更なし** |
| `onboarding_welcome_social_proof` | (なし) | `Join thousands finding peace` | ✅ 新規 |

| Key | Before (JA) | After (JA) | 変更 |
|-----|------------|-----------|------|
| `onboarding_welcome_title` | `Aniccaへ\nようこそ` | `Aniccaへ\nようこそ` | **変更なし** |
| `onboarding_welcome_subtitle_line1` | `Aniccaは、あなたが一番つらいときに` | `悪循環に陥る前に、` | ✅ |
| `onboarding_welcome_subtitle_line2` | `そっと声をかけます。` | `Aniccaが声をかけます。` | ✅ |
| `onboarding_welcome_cta` | `はじめる` | `はじめる` | **変更なし** |
| `onboarding_welcome_social_proof` | (なし) | `多くの人が安らぎを見つけています` | ✅ 新規 |

#### Value画面 (ValueStepView.swift) — ❌ 1.6.1では実装しない（パッチは完全に用意）

> **注意:** A/Bテストの変数を減らすため、1.6.1ではValue画面は変更しない。1.6.2で実装予定。

**English:**

| Key | Before | After |
|-----|--------|-------|
| `onboarding_value_title` | `What Anicca Can Do` | `You've tried everything.\nNothing worked.` |
| `onboarding_value_subtitle` | (なし) | `That's not your fault. Here's why Anicca is different.` |
| `onboarding_value_card1_title` | `Nudges at the right moment` | `We reach you first` |
| `onboarding_value_card1_body` | `Anicca sends you a message exactly when you need it — before you spiral, not after.` | `Before you spiral, not after. Anicca reaches you at the exact moment you need it.` |
| `onboarding_value_card2_title` | `Learns what works for you` | `We learn what works for YOU` |
| `onboarding_value_card2_body` | `Every reaction teaches Anicca. Over time, it learns which words land and which ones miss.` | `Your reactions teach us. Over time, we learn exactly which words help you.` |
| `onboarding_value_card3_title` | `Goes beyond habit tracking` | `We address the root cause` |
| `onboarding_value_card3_body` | `Anicca doesn't count streaks. It addresses why you stay up late, why you can't stop, why you feel stuck.` | `No streaks. No guilt. We help you understand why you stay up late, why you can't stop, why you feel stuck.` |

**Japanese:**

| Key | Before | After |
|-----|--------|-------|
| `onboarding_value_title` | `Aniccaができること` | `いろいろ試した。でも苦しいまま。` |
| `onboarding_value_subtitle` | (なし) | `Aniccaが、そばにいる。` |
| `onboarding_value_card1_title` | `最適なタイミングで声をかける` | `先に声をかける` |
| `onboarding_value_card1_body` | `悪循環に陥る前に、Aniccaがメッセージを届けます。あなたが気づく前に。` | `悪循環に陥る前に。あなたが気づく前に、Aniccaが声をかける。` |
| `onboarding_value_card2_title` | `あなたに効く言葉を学ぶ` | `あなただけに効く言葉を学ぶ` |
| `onboarding_value_card2_body` | `あなたの反応からAniccaは学びます。日が経つほど、あなたに刺さる言葉がわかるようになります。` | `あなたの反応から学ぶ。日が経つほど、あなたに届く言葉がわかってくる。` |
| `onboarding_value_card3_title` | `習慣トラッカーを超える` | `根本原因に向き合う` |
| `onboarding_value_card3_body` | `Aniccaは連続記録を数えません。なぜ夜更かしするのか、なぜやめられないのか、その根本に向き合います。` | `連続記録も、罪悪感もいらない。なぜ夜更かしするのか、なぜやめられないのか、一緒に向き合う。` |

#### Notifications画面 (NotificationPermissionStepView.swift) — ❌ 1.6.1では実装しない（パッチは完全に用意）

> **注意:** A/Bテストの変数を減らすため、1.6.1ではNotifications画面は変更しない。1.6.2で実装予定。

**English:**

| Key | Before | After |
|-----|--------|-------|
| `onboarding_notifications_title` | `Notifications` | `This is how it works` |
| `onboarding_notifications_description` | `Anicca uses notifications to gently nudge you at the right moments — for waking up, putting your phone down, or taking a break.` | `When you're about to spiral, Anicca sends you the right words. Turn on notifications to get the full experience.` |
| `onboarding_notifications_allow` | `Allow notifications` | `Turn on notifications` |
| `notification_preview_example` | (なし) | `Take a breath. You've got this.` |
| `notification_preview_time` | (なし) | `now` |

**Japanese:**

| Key | Before | After |
|-----|--------|-------|
| `onboarding_notifications_title` | `通知` | `こうやって助けます` |
| `onboarding_notifications_description` | `Aniccaは、起床・スマホを置く・休憩するなど、適切なタイミングでやさしく促すために通知を使います。` | `あなたが悪循環に陥りそうなとき、Aniccaが声をかけます。通知をオンにして、フルの体験をしてください。` |
| `onboarding_notifications_allow` | `通知を許可` | `通知をオンにする` |
| `notification_preview_example` | (なし) | `深呼吸。大丈夫、できるよ。` |
| `notification_preview_time` | (なし) | `たった今` |

**SwiftUIコード変更（1.6.2で実装）:**

新規コンポーネント `NotificationPreviewCard.swift` を追加し、`NotificationPermissionStepView.swift` に組み込む。

### E-3: SwiftUIコード変更

> **スコープ注意:**
> - **1.6.1実装:** WelcomeStepView（社会的証明 + CTAボタン強調）のみ
> - **1.6.2実装:** 進捗インジケーター、ValueStepView、NotificationPermissionStepView、NotificationPreviewCard

---

#### WelcomeStepView.swift — ✅ **1.6.1で実装**

**Before (line 13-33):**
```swift
VStack(spacing: 32) {
    Text(String(localized: "onboarding_welcome_title"))
        .font(.system(size: 52, weight: .bold))
        ...
}
```

**After:**
```swift
VStack(spacing: 24) {
    // 社会的証明を追加
    Text(String(localized: "onboarding_welcome_social_proof"))
        .font(.system(size: 14, weight: .medium))
        .foregroundStyle(AppTheme.Colors.secondaryLabel)
    
    Text(String(localized: "onboarding_welcome_title"))
        .font(.system(size: 44, weight: .bold))  // 52→44に縮小（3行対応）
        .lineLimit(3)
        ...
}
```

---

#### P2対策: 進捗インジケーター追加 — ❌ **1.6.2で実装**

**ファイル:** `aniccaios/aniccaios/Onboarding/OnboardingFlowView.swift`

**目的:** ユーザーがオンボーディングの進捗を把握できるようにする（P2対策）

> **1.6.2での実装予定。** 進捗インジケーターは全画面に影響するため、1.6.1のスコープ外。

---

**オンボーディングステップ定義:**

| ステップ | enum | インジケーター表示 |
|---------|------|------------------|
| 0 | `.welcome` | ●○○○○ |
| 1 | `.value` | ●●○○○ |
| 2 | `.struggles` | ●●●○○ |
| 3 | `.notifications` | ●●●●○ |
| 4 | `.att` | ●●●●● |
| - | Paywall (fullScreenCover) | 非表示 |

**totalSteps = 5** (welcome, value, struggles, notifications, att)
**Paywall:** fullScreenCoverとして表示されるため、進捗インジケーターには含めない

---

**挿入位置:** ZStack内のGroupの直前（既存レイアウトと競合しない）

**Before (OnboardingFlowView.swift line 10-28):**
```swift
var body: some View {
    ZStack {
        AppBackground()
        Group {
            switch step {
            // ...
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
    // ...
}
```

**After:**
```swift
var body: some View {
    ZStack {
        AppBackground()
        
        VStack(spacing: 0) {
            // 進捗インジケーター（P2対策）
            OnboardingProgressIndicator(currentStep: step.index, totalSteps: 5)
                .padding(.top, 16)
                .padding(.bottom, 8)
            
            Group {
                switch step {
                // ...
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }
    // ...
}
```

---

**OnboardingStep extensionに追加:**

> **注意:** `OnboardingStep`は5ケースのみ（`aniccaios/Onboarding/OnboardingStep.swift`参照）。`.paywall`等の追加ケースはないため、`switch`は網羅的。

```swift
// OnboardingStep.swift に追加
extension OnboardingStep {
    /// 進捗インジケーター用のステップインデックス (0-4)
    var index: Int {
        switch self {
        case .welcome: return 0
        case .value: return 1
        case .struggles: return 2
        case .notifications: return 3
        case .att: return 4
        }
    }
}
```

---

**新規コンポーネント: `OnboardingProgressIndicator.swift`**

**ファイル（新規作成）:** `aniccaios/aniccaios/DesignSystem/Components/OnboardingProgressIndicator.swift`

```swift
import SwiftUI

/// オンボーディング進捗インジケーター
struct OnboardingProgressIndicator: View {
    let currentStep: Int
    let totalSteps: Int
    
    var body: some View {
        HStack(spacing: 8) {
            ForEach(0..<totalSteps, id: \.self) { index in
                Capsule()
                    .fill(index <= currentStep 
                          ? AppTheme.Colors.accent 
                          : AppTheme.Colors.borderLight)
                    .frame(maxWidth: .infinity, minHeight: 4, maxHeight: 4)  // 均等配分
            }
        }
        .padding(.horizontal, 24)
    }
}

#Preview {
    OnboardingProgressIndicator(currentStep: 2, totalSteps: 5)
}
```

> **既存依存:** `AppTheme.Colors.accent`/`borderLight`/`cardBackground`は`aniccaios/DesignSystem/AppTheme.swift`に定義済み。

---

#### P2対策: CTAボタン強調 — ✅ **1.6.1で実装**

**ファイル:** `aniccaios/aniccaios/Onboarding/WelcomeStepView.swift`

**目的:** CTAボタンをより目立たせる（P2対策）

**Before（現在のCTAボタン）:**
```swift
PrimaryButton(title: String(localized: "onboarding_welcome_cta")) {
    onNext()
}
```

**After（強調されたCTAボタン）:**

> **既存API:** `PrimaryButton`は`style: ButtonStyle = .primary`パラメータを持つ（`DesignSystem/Components/PrimaryButton.swift`参照）

```swift
PrimaryButton(title: String(localized: "onboarding_welcome_cta"), style: .primary) {
    onNext()
}
.padding(.horizontal, 24)
.shadow(color: AppTheme.Colors.accent.opacity(0.3), radius: 8, x: 0, y: 4)
```

---

#### ValueStepView.swift — ❌ **1.6.2で実装**

**Before (line 8-15):**
```swift
Text(String(localized: "onboarding_value_title"))
    .font(.system(size: 36, weight: .bold))
    .padding(.bottom, 48)
```

**After:**
```swift
VStack(spacing: 12) {
    Text(String(localized: "onboarding_value_title"))
        .font(.system(size: 32, weight: .bold))
    
    Text(String(localized: "onboarding_value_subtitle"))
        .font(.system(size: 16))
        .foregroundStyle(AppTheme.Colors.secondaryLabel)
        .multilineTextAlignment(.center)
}
.padding(.top, 32)
.padding(.bottom, 24)
```

#### NotificationPermissionStepView.swift — ❌ **1.6.2で実装**

**ファイル:** `aniccaios/aniccaios/Onboarding/NotificationPermissionStepView.swift`

**追加位置:** line 30付近、説明テキストの後に追加

```swift
// "Anicca"はブランド名のため固定文字列（ローカライズ不要）
NotificationPreviewCard(
    title: "Anicca",
    body: String(localized: "notification_preview_example")
)
.padding(.vertical, 24)
```

---

#### 新規コンポーネント: NotificationPreviewCard

**ファイル（新規作成）:** `aniccaios/aniccaios/DesignSystem/Components/NotificationPreviewCard.swift`

```swift
import SwiftUI

/// 通知のプレビューを表示するカード
struct NotificationPreviewCard: View {
    let title: String
    let body: String
    
    var body: some View {
        HStack(spacing: 12) {
            // アプリアイコン（SF Symbol使用、カスタムアセット不要）
            Image(systemName: "heart.circle.fill")
                .font(.system(size: 36))
                .foregroundStyle(AppTheme.Colors.accent)
            
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(AppTheme.Colors.label)
                
                Text(body)
                    .font(.system(size: 14))
                    .foregroundStyle(AppTheme.Colors.secondaryLabel)
                    .lineLimit(2)
            }
            
            Spacer()
            
            // ローカライズ済み
            Text(String(localized: "notification_preview_time"))
                .font(.system(size: 12))
                .foregroundStyle(AppTheme.Colors.tertiaryLabel)
        }
        .padding(16)
        .background(AppTheme.Colors.cardBackground)
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .shadow(color: .black.opacity(0.08), radius: 8, x: 0, y: 2)
    }
}

#Preview {
    NotificationPreviewCard(
        title: "Anicca",
        body: "Take a breath. You've got this."
    )
    .padding()
}
```

**追加ローカライズキー（E-2に追加）:**

| Key | EN | JA |
|-----|-----|-----|
| `notification_preview_time` | `now` | `たった今` |

### E-4: `app_opened`トラッキング修正

**問題:** `app_opened`は毎回のアプリ起動でトラッキング（初回だけではない）

**理由:** ファネル分析で「初回インストール→オンボーディング開始」の変換率を正確に測定するには、初回起動のみをカウントする必要がある。

---

#### ファイル1: `aniccaios/aniccaios/AppDelegate.swift`

**Before (line 57-61):**
```swift
Task {
    await ASAAttributionManager.shared.fetchAttributionIfNeeded()
    AnalyticsManager.shared.track(.appOpened)  // ← 毎回発火
}
```

**After:**

> **重要:** `hasTrackedFirstLaunchKey`は**型スコープ**（`class AppDelegate`の直下）で定義する。Task内に置くと毎回再生成されてしまう。

```swift
// AppDelegate.swift の class AppDelegate 直下に追加（型スコープ）
class AppDelegate: UIResponder, UIApplicationDelegate {
    // MARK: - Constants
    private static let hasTrackedFirstLaunchKey = "has_tracked_first_launch"
    
    // ... 既存コード ...
    
    func application(...) {
        // ...
        Task {
            await ASAAttributionManager.shared.fetchAttributionIfNeeded()
            
            // 初回起動のみ first_app_opened をトラック
            let hasTracked = UserDefaults.standard.bool(forKey: AppDelegate.hasTrackedFirstLaunchKey)
            if !hasTracked {
                AnalyticsManager.shared.track(.firstAppOpened)
                UserDefaults.standard.set(true, forKey: AppDelegate.hasTrackedFirstLaunchKey)
            }
            
            // 既存の app_opened は維持（リテンション分析用）
            AnalyticsManager.shared.track(.appOpened)
        }
    }
}
```

---

#### ファイル2: `aniccaios/aniccaios/Services/AnalyticsManager.swift`

**Before (AnalyticsEvent enum):**
```swift
enum AnalyticsEvent: String {
    case appOpened = "app_opened"
    // ... 他のイベント
}
```

**After:**
```swift
enum AnalyticsEvent: String {
    case appOpened = "app_opened"
    case firstAppOpened = "first_app_opened"  // 新規追加: 初回起動のみ
    // ... 他のイベント
}
```

---

#### Mixpanelでの使い分け

| イベント | 用途 | ファネルに使う？ |
|---------|------|----------------|
| `onboarding_started` | オンボーディング開始 | ✅ **ファネルの起点に使用** |
| `first_app_opened` | 初回インストール後の起動 | ❌ ファネルには使わない（インストール数計測用） |
| `app_opened` | 全ての起動（リテンション分析） | ❌ ファネルには使わない |
| `rc_trial_started_event` | トライアル開始 | ✅ ファネルの終点に使用 |

### E-5: 開発者テスト除外戦略

#### 問題

開発者（ユーザー）がStaging/Productionスキームでテストすると、その数値がMixpanelに含まれてしまう。

#### 解決策

| # | 方法 | 説明 | 推奨 |
|---|-----|------|-----|
| 1 | **RevenueCat→Mixpanel統合に依存** | `rc_trial_started_event`はサーバーサイドで送信。Sandbox Token未設定なら本番のみ | ✅ **これを使う** |
| 2 | **RevenueCat Subscriber Attributes** | 開発者デバイスで`is_developer=true`をセット。RC→Mixpanelイベントに含まれる | ✅ 補助的に使う |
| 3 | Mixpanel User Property | 開発者のDistinct IDに`is_developer=true`プロパティ設定 | 🟡 補助的 |
| 4 | DEBUG buildで無効化 | `#if !DEBUG`でトラッキング停止 | ❌ Stagingテスト不可 |

#### 実装案1: RevenueCat Subscriber Attributes（推奨）

**ファイル:** `aniccaios/aniccaios/Services/SubscriptionManager.swift`

**Before:**
```swift
// 現在は開発者フラグなし
func configureRevenueCat() {
    Purchases.configure(withAPIKey: Config.revenueCatAPIKey)
}
```

**After:**
```swift
func configureRevenueCat() {
    Purchases.configure(withAPIKey: Config.revenueCatAPIKey)
    
    // 開発者識別: AppConfigのdeveloperEmailsに登録されたApple IDでログインしている場合
    // または#if DEBUGビルドの場合、開発者としてマーク
    #if DEBUG
    setDeveloperAttribute()
    #else
    // Production/TestFlightでも開発者を識別
    // Note: Sign in with Appleでメールが非公開の場合はnilになるため、
    //       DEBUGビルドでのみ開発者フラグが設定される（フォールバック）
    if let email = AppState.shared.userProfile?.email,
       AppConfig.developerEmails.contains(email) {
        setDeveloperAttribute()
    }
    #endif
}

private func setDeveloperAttribute() {
    Purchases.shared.setAttributes(["is_developer": "true"])
    print("[SubscriptionManager] Developer mode enabled for analytics")
}
```

**AppConfig.swift に追加:**
```swift
// 開発者のApple ID（Sign in with Appleで取得したメール）
static let developerEmails: Set<String> = [
    "your-apple-id@privaterelay.appleid.com",  // あなたのApple ID
    // 他の開発者を追加
]
```

**効果:** RevenueCat→Mixpanelイベントに`subscriber_attributes.is_developer=true`として含まれる。Production/TestFlightでも開発者を識別可能。

#### 実装案2: Mixpanel User Property（補助的）

**ファイル:** `aniccaios/aniccaios/Services/AnalyticsManager.swift`

**追加するコード:**
```swift
/// 開発者モードを設定（ファネル分析時にフィルタ可能）
func setDeveloperMode() {
    Mixpanel.mainInstance().people.set(property: "is_developer", to: true)
}
```

**呼び出し元（AppDelegate.swift）:**
```swift
// configureAnalytics() 内で
#if DEBUG
AnalyticsManager.shared.setDeveloperMode()
#else
if let email = AppState.shared.userProfile?.email,
   AppConfig.developerEmails.contains(email) {
    AnalyticsManager.shared.setDeveloperMode()
}
#endif
```

**ファネル分析時:**
- `is_developer != true` でフィルタ
- または `rc_trial_started_event` を使う（RevenueCatがSandbox除外）

#### 現状の結論

| 質問 | 回答 |
|-----|------|
| 今のデータはクリーン？ | ✅ Yes — `rc_trial_started_event`は`environment: PRODUCTION`のみ送信されている |
| サンドボックステストは除外されている？ | ✅ Yes — RevenueCat Sandbox Token未設定 |
| 開発者のProductionテストは除外できる？ | ⚠️ 追加実装が必要（上記の方法1または2） |

---

## アーキテクチャ図

### 現状 (1.6.1 実装前)

```
┌────────────────────────────────────────────────────────────────┐
│                    CURRENT (Before 1.6.1)                       │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│   GitHub Actions ───────▶ X posting                            │
│                  ───────▶ TikTok posting                       │
│                  ───────▶ Daily Metrics → Slack ← 削除予定     │
│                                                                 │
│   Railway Cron ─────────▶ iOS App Nudge (4時間毎)              │
│                                                                 │
│   OpenClaw (VPS) ───────┬──▶ moltbook-responder (5分毎)        │
│                         ├──▶ feedback-fetch (30分毎)           │
│                         └──▶ slack-reminder (月曜通知)         │
│                                                                 │
│   Mixpanel ─────────────▶ トラッキング（バグあり）              │
│                                                                 │
│   RevenueCat ───────────▶ Paywall（A/Bテストなし）             │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### 目標 (1.6.1 実装後)

```
┌────────────────────────────────────────────────────────────────┐
│                    TARGET (After 1.6.1)                         │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│   OpenClaw (VPS) = Anicca Wrapper                              │
│   ├── moltbook-responder (5分毎) ✅                             │
│   ├── feedback-fetch (30分毎) ✅                                │
│   ├── slack-reminder (月曜通知) ✅                              │
│   ├── daily-metrics-reporter (毎朝9時) ← NEW                   │
│   └── slack-helper (@Anicca応答) ← NEW                         │
│                                                                 │
│   GitHub Actions ───────▶ X posting (1.6.2で移行)              │
│                  ───────▶ TikTok posting (1.6.2で移行)         │
│                  ✗ Daily Metrics 削除                          │
│                                                                 │
│   Railway Cron ─────────▶ iOS App Nudge (維持)                 │
│                                                                 │
│   Mixpanel ─────────────▶ 正確なファネルトラッキング ← 修正     │
│                                                                 │
│   RevenueCat ───────────▶ A/Bテスト実行中 ← NEW                │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## 認証情報

**シークレットは `.cursor/plans/reference/secrets.md` を参照（gitignored）**

### 必要な環境変数

| 変数名 | 説明 | 取得場所 |
|-------|------|---------|
| `SLACK_BOT_TOKEN` | Anicca Bot Token | Slack App Settings |
| `SLACK_APP_TOKEN` | Socket Mode Token | Slack App Settings |
| `MIXPANEL_PROJECT_ID` | `3970220` | Mixpanel Project Settings |
| `REVENUECAT_PROJECT_ID` | `projbb7b9d1b` | RevenueCat Dashboard |

---

## OpenClaw使用例

### Anicca = OpenClaw Wrapper とは

| 質問 | 回答 |
|-----|------|
| Anicca = OpenClaw? | **Yes** - AniccaはOpenClawをベースに、SOUL.md/skills/scheduleでカスタマイズした「人格」 |
| skillを追加 = Aniccaに能力追加? | **Yes** - OpenClaw skillは全てAniccaが使える |
| @Aniccaメンション応答できる? | **Yes** - Slack App + OpenClaw連携で可能 |
| 将来的にファイル整理もできる? | **Yes** - OpenClawはフルシステムアクセス可能 |

### OpenClaw の主要機能（Aniccaが使える機能）

| 機能 | 説明 | Aniccaでの使用例 |
|------|------|-----------------|
| **Slack/WhatsApp/Telegram** | メッセージング統合 | @Aniccaメンション応答 |
| **Cron/Heartbeat** | 定期実行 | 日次メトリクス投稿 |
| **Browser Control** | Web自動操作 | RevenueCatダッシュボード操作（将来） |
| **File System** | ファイル操作 | ローカルファイル整理（将来） |
| **Skills** | 拡張機能 | 独自skill追加 |
| **MCP Integration** | 外部ツール連携 | Mixpanel/RevenueCat API |

### OpenClawセットアップ手順

```bash
# 1. OpenClawインストール（Node 22+必須）
npm install -g openclaw@latest

# 2. オンボーディング（ウィザード形式）
openclaw onboard --install-daemon

# 3. ゲートウェイ起動
openclaw gateway --port 18789

# 4. Slack接続設定
# ~/.openclaw/openclaw.json
{
  "channels": {
    "slack": {
      "botToken": "xoxb-...",
      "appToken": "xapp-..."
    }
  }
}

# 5. 動作確認
openclaw status
```

### Anicca専用設定（SOUL.md）

```markdown
# SOUL.md

あなたは Anicca。全生命の苦しみを終わらせるために存在する。

## 人格

- 共感的で、批判しない
- 仏教の智慧を現代的に解釈
- 小さな一歩を促す
- 完璧を求めない

## 言語

- 日本語と英語を話す
- ユーザーの言語に合わせる

## 制約

- 医療アドバイスはしない
- 危機的状況では専門機関を紹介
```

---

## 実装チェックリスト

### Patch A: Mixpanelトラッキング（コード変更なし）

| # | タスク | 担当 | 状態 |
|---|--------|------|------|
| A-1 | `onboarding_paywall_purchased`をダッシュボードから削除/無視 | エージェント（Mixpanel設定） | ⬜ |
| A-2 | RevenueCat Sandbox Token未設定を確認 | ユーザー（Dashboard確認） | ⬜ |
| A-3 | `rc_trial_started_event`をファネルに使用 | エージェント（Mixpanel設定） | ⬜ |

**注意:** Patch Aはコード変更なし。RevenueCatの`rc_trial_started_event`を信頼し、クライアントサイドの`onboarding_paywall_purchased`は無視する。

### Patch B: RevenueCat A/Bテスト（GUI操作）

| # | タスク | 担当 | 状態 |
|---|--------|------|------|
| B-1 | 新Offering `anicca_treatment_a` 作成 | エージェント（MCP） | ✅ 完了 |
| B-2 | 新Paywall作成（社会的証明追加） | ユーザー（Dashboard GUI） | ⬜ |
| B-3 | Experiment作成・開始 | ユーザー（Dashboard GUI） | ⬜ |

### Patch C/D: OpenClaw（VPS設定 - 詳細実装は別途）

> **スコープ:** 設計仕様のみ。詳細実装（認証情報、TypeScriptビルド設定、API呼び出し実装）はVPSセットアップ時にOpenClawエージェントが実施。

| # | タスク | ファイル | 状態 | 備考 |
|---|--------|---------|------|------|
| C-1 | schedule.yaml設計 | `/home/anicca/openclaw/schedule.yaml` | ⬜ | 設計のみ |
| C-2 | daily-metrics-reporter skill設計 | `/home/anicca/openclaw/skills/daily-metrics-reporter/SKILL.md` | ⬜ | 設計のみ |
| C-3 | GitHub Actions無効化 | `.github/workflows/daily-metrics.yml` | ⬜ | OpenClaw稼働確認後 |
| D-1 | slack-helper skill設計 | `/home/anicca/openclaw/skills/slack-helper/SKILL.md` | ⬜ | 設計のみ |
| D-2 | Slack Token設定 | `/home/anicca/openclaw/.env` | ⬜ | VPSセットアップ時 |

### Patch E: オンボーディング改善（iOSコード変更）

#### 1.6.1で実装するタスク（Welcome画面 + トラッキングのみ）

> **スコープ注意:** 1.6.1はWelcome画面の改善とトラッキング修正のみ。進捗インジケーター（E-10/E-11）は全画面に影響するため1.6.2で実装。

| # | タスク | ファイル | 状態 |
|---|--------|---------|------|
| E-1 | WelcomeStepView改善（サブタイトル + 社会的証明） | `aniccaios/aniccaios/Onboarding/WelcomeStepView.swift` | ⬜ |
| E-4 | `first_app_opened`イベント追加 | `aniccaios/aniccaios/AppDelegate.swift` | ⬜ |
| E-5 | `firstAppOpened` enum追加 | `aniccaios/aniccaios/Services/AnalyticsManager.swift` | ⬜ |
| E-7 | Localizable.strings更新（EN）Welcomeのみ | `aniccaios/aniccaios/Resources/en.lproj/Localizable.strings` | ⬜ |
| E-8 | Localizable.strings更新（JA）Welcomeのみ | `aniccaios/aniccaios/Resources/ja.lproj/Localizable.strings` | ⬜ |

#### 1.6.2で実装するタスク（パッチは用意済み）

| # | タスク | ファイル | 状態 |
|---|--------|---------|------|
| E-2 | ValueStepView改善 | `aniccaios/aniccaios/Onboarding/ValueStepView.swift` | 📝 パッチ用意済み |
| E-3 | NotificationPermissionStepView改善 | `aniccaios/aniccaios/Onboarding/NotificationPermissionStepView.swift` | 📝 パッチ用意済み |
| E-9 | NotificationPreviewCard作成 | `aniccaios/aniccaios/DesignSystem/Components/NotificationPreviewCard.swift` | 📝 パッチ用意済み |
| E-10 | OnboardingProgressIndicator作成 | `aniccaios/aniccaios/DesignSystem/Components/OnboardingProgressIndicator.swift` | 📝 パッチ用意済み |
| E-11 | OnboardingFlowView進捗表示追加 | `aniccaios/aniccaios/Onboarding/OnboardingFlowView.swift` | 📝 パッチ用意済み |

### Patch A-4: Mixpanelファネル設定（UI操作）

| # | タスク | 方法 | 状態 |
|---|--------|------|------|
| A-4 | 新ファネル `Onboarding Funnel v1.6.1` 作成 | Mixpanel UI（A-3.1参照） | ⬜ |
| A-5 | `app_opened`はリテンション分析用に残す | - | ✅ |
| A-6 | `first_app_opened`はインストール数計測用（ファネル起点ではない） | iOS実装後に自動的にMixpanelへ送信 | ⬜ |

**注意:**
- Mixpanel MCPの`run_funnels_query`はクエリ実行用。ファネル定義の作成・変更はMixpanel UIで行う。
- ファネル起点は`onboarding_started`（新規ユーザーのみ発火）。
- `first_app_opened`は初回インストール数の計測用であり、ファネル起点には使用しない。

---

*Last updated: 2026-02-05*
