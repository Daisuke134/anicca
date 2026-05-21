# 0xSero OpenClaw Hacks — Slack完全コピー実装スペック

**作成日**: 2026-02-18
**実装時間**: 夜間（23:00 JST〜）
**原則**: 0xSeroのDiscordセットアップを100%コピー。Discord→Slack以外の変更なし。オリジナルの味ゼロ。

**ソース**: 0xSero (@0xSero) Xスレッド 2026-02-17, 49.3K views, Thread 1/6〜5/6

---

## 1. Task Management（タスク管理）

**0xSeroの原文**:
> Use forum for long term life tasks, each post under forum is its own session.
> Use the new feature to allow openclaw to build you UI components in discord.
> Feed it your problems, ambitions, goals, context, socials.

**Slack実装**:

0xSeroはDiscord Forumチャンネルを使っている。Forumでは各投稿が独立スレッド＝独立セッションになる。

Slackにはフォーラム機能がない。代替: **`#tasks` チャンネル1個 + スレッド式**。
- 1タスク = 1スレッド（チャンネル乱立防止）
- OpenClawが各スレッドに進捗・リマインダー・調査結果を投稿
- チャンネルトピックに「長期タスク管理。1スレッド=1タスク」と設定

**タスク一覧（初期スレッド）**:
- ペイウォールCVR改善
- x402 Nudge API
- Mac Mini移行
- 確定申告（締切3/16）
- 免許更新（締切2/28）
- 健康診断（2月末）
- 新幹線予約（3/5, 3/7）

**UIコンポーネント**: SlackはBlock Kit（ボタン/セレクト/モーダル）対応。OpenClawのmessageツールで送信可能。タスクの状態更新ボタン等に使う。

**フィード内容**: MEMORY.md + USER.md の内容を `#tasks` のチャンネルトピックまたは固定メッセージとして投稿。問題・野望・ゴール・コンテキスト・SNSを集約。

---

## 2. Code（コード管理）

**0xSeroの原文**:
> Setup a tapoki thread forwarder.
> Setup a RAG over my top 30 repos to find common issues, inefficiencies and areas for growth.
> Infra channel with all my devices, codebases, etc.

### 2a. Thread Forwarder（GitHub → Slack）

「Tapoki thread forwarder」の正確なツールは特定できなかったが、機能は「GitHub/CI通知をチャットのスレッドに転送し、各PR/issueが独立スレッドになる」こと。

**Slack実装**: GitHub公式Slack連携
- チャンネル: `#code`
- 設定: `/github subscribe Daisuke134/anicca.ai issues pulls commits releases deployments`
- PR/issueごとに自動でスレッドが立つ
- CIの成功/失敗もここに流れる

### 2b. RAG over Repos

0xSeroは30リポを横断検索して共通の問題・非効率・改善点を見つけている。

僕らは1リポ（anicca.ai）のみ。RAGの代わりに**定期コードスキャン**:
- チャンネル: `#code`
- cronで週1回、以下をスキャン:
  - 依存関係の脆弱性（`npm audit`）
  - 未使用コード/デッドコード検出
  - TODO/FIXME/HACK コメント一覧
  - テストカバレッジ
- 結果を `#code` に投稿

### 2c. Infraチャンネル

- チャンネル: `#infra`
- heartbeat（またはcron）で定期投稿:

```
📍 Infrastructure Status
─────────────────────────
VPS (Hetzner):
  IP: 46.225.70.241
  Disk: 63% used
  CPU: ...
  Memory: ...
  Uptime: ...
  OpenClaw: running

Mac Mini (Tailscale):
  Host: cbns03macbook-pro
  Status: online/sleeping
  Disk: ...

Railway (Backend API):
  URL: https://api.anicca.ai
  Health: OK/DOWN
  Response: ...ms

Services:
  - OpenClaw Gateway: ✅
  - Express API: ✅
  - PostgreSQL: ✅
  - RevenueCat: ✅
  - Mixpanel: ✅
  - Blotato: ✅
  - Apify: ⚠️ (credits low)
  - fal.ai: ✅
```

---

## 3. Shopping（買い物）

**0xSeroの原文**:
> Setup GPU-Mac watchdog to catch.
> Yesterday Openclaw made its first purchase and delivery to my house autonomously.
> Helped me get a domain.

**Slack実装**:
- チャンネル: `#shopping`

### 3a. Watchdog（残高/在庫監視）
Mac Miniは既に購入済み。同じ仕組みで以下を監視:
- Apifyクレジット残高（現在$0.30 → しきい値$1以下で警告）
- Railway月額料金
- fal.ai残高
- Anthropic APIクレジット
- cronで6時間ごとにチェック → `#shopping` に報告

### 3b. 自律購入
将来的に実装。今は残高が低下したら `#shopping` に通知 → Daisが承認 → 購入。

### 3c. ドメイン
anicca.ai既にある。新ドメインが必要になったら `#shopping` で対応。

---

## 4. Logistics（運用管理）

**0xSeroの原文**:
> Config channel which just shows you all the openclaw configs, crons, models, etc.
> Logs channel which just forwards all openclaw logs.

### 4a. `#config` チャンネル

cronで1日1回（朝8:00 JST）に以下をダンプ:

```
⚙️ OpenClaw Configuration
─────────────────────────
Model: anthropic/claude-opus-4-5
Heartbeat Model: openai/gpt-4o-mini
Cron Model: anthropic/claude-sonnet-4-20250514

Active Crons (28):
  05:00 trend-hunter-5am
  05:05 app-metrics-morning
  05:10 app-reviews
  05:15 suffering-detector
  ...

Skills (30+):
  app-metrics, app-reviews, suffering-detector,
  trend-hunter, x-poster, tiktok-poster, ...

Channels:
  webchat: ✅
  slack: ✅ (#metrics, #ai)
  telegram: ❌

Environment Keys:
  BLOTATO_API_KEY: ✅
  APIFY_API_TOKEN: ✅
  FAL_KEY: ✅
  X_BEARER_TOKEN: ✅
  ...
```

設定変更時にも自動投稿（gateway config変更をフック）。

### 4b. `#logs` チャンネル

全cronの実行結果を転送:
- 成功: `✅ trend-hunter-5am completed (2m25s)`
- 失敗: `❌ tiktok-poster failed: Apify credits exhausted`
- SAFE-T発動: `🚨 SAFE-T triggered: severity 0.95`
- エラー: スタックトレース付き

**現在 `#metrics` に全部混ぜてるのを分離。**
- `#metrics` = アプリメトリクスのみ（RevenueCat/Mixpanel/ASC）
- `#logs` = cron実行ログ/エラー/システムイベント

---

## 5. Fun（楽しみ）

**0xSeroの原文**:
> Music channel, fed it all my favorite music and a feedback system with thumbs up and down so it can on cron recommend me new music based on feedback + my taste.
> Research channel, on heartbeat fetches me latest interesting research papers.

### 5a. `#music` チャンネル

- Daisの好きな音楽リストを初期データとしてフィード（要ヒアリング）
- cronでレコメンド投稿（昼12:00 JST、既存lunch-musicの出力先変更）
- 各投稿に 👍 👎 リアクションを促す
- OpenClawがリアクションを収集（Slack APIのreactions.get）
- 次回レコメンドにフィードバック反映
- フィードバックデータ保存: `~/.openclaw/workspace/music/feedback.json`

```json
{
  "liked": ["Artist - Song", ...],
  "disliked": ["Artist - Song", ...],
  "genres_preferred": ["lo-fi", "jazz"],
  "genres_avoided": ["heavy metal"]
}
```

### 5b. `#research` チャンネル

- **heartbeat**で最新論文を取得（latest-papersスキルの出力先変更）
- tech-newsスキルの出力もここ
- openclaw-usecaseスキルの出力もここ
- `#metrics`から完全分離

---

## チャンネル一覧（最終）

| チャンネル | カテゴリ | 投稿内容 |
|---|---|---|
| `#tasks` | Task Management | 長期タスク（スレッド式） |
| `#code` | Code | GitHub通知、コードスキャン |
| `#infra` | Code | VPS/Mac/Railwayヘルスチェック |
| `#shopping` | Shopping | 残高監視、購入通知 |
| `#config` | Logistics | 設定/cron/モデル一覧ダンプ |
| `#logs` | Logistics | cron結果、エラー、SAFE-T |
| `#music` | Fun | レコメンド + 👍👎フィードバック |
| `#research` | Fun | 論文、テックニュース |
| `#metrics` | **既存維持** | アプリメトリクスのみ |

新規: 8チャンネル。既存: `#metrics` 維持。

---

## 既存cronの出力先変更

| cron | 現在の出力先 | 変更後 |
|---|---|---|
| app-metrics | #metrics | #metrics（変更なし） |
| app-reviews | #metrics | #metrics（変更なし） |
| trend-hunter | #metrics | #logs（実行ログ） |
| x-poster | #metrics | #logs |
| tiktok-poster | #metrics | #logs |
| suffering-detector | #metrics | #logs + #research（検知内容） |
| latest-papers | #metrics | #research |
| tech-news | #metrics | #research |
| openclaw-usecase | #metrics | #research |
| lunch-music | なし | #music |
| moltbook-interact | #metrics | #logs |

---

## 実装順序（夜間）

1. Slack APIで8チャンネル作成
2. 各チャンネルのトピック設定
3. `#tasks` に初期タスクスレッド7個作成
4. `#config` ダンプcron作成（毎朝8:00 JST）
5. `#infra` ヘルスチェックcron作成（6時間ごと）
6. `#shopping` 残高監視cron作成（6時間ごと）
7. `#code` GitHub Slack連携設定
8. `#music` フィードバック収集の仕組み + lunch-music出力先変更
9. `#research` latest-papers/tech-news出力先変更
10. `#logs` 全cronの実行ログ転送設定
11. 既存cronのSlackチャンネルIDを全て更新
12. `#tasks` にMEMORY.md要約を固定メッセージとして投稿

---

## 未解決

- **Tapoki thread forwarder**: 正確なツール不明。GitHub Slack連携で同等機能カバー。
- **Daisの好きな音楽リスト**: 未取得。`#music` 開始前にヒアリング必要。
- **UIコンポーネント（Block Kit）**: タスク状態更新ボタン等、具体設計は実装時に決定。
