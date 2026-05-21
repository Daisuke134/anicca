# TikTok Agent: 現状分析 + スケジュール投稿 + 統合ロードマップ

> 作成日: 2026-01-28
> 最終更新: 2026-01-28
> 目的: エージェントが何を受け取り、何を決定し、何を出力するのかを明確にする。嘘なし。

---

## 1. エージェントの現状（As-Is）— 正直な分析

### 1.1 エージェントが受け取るコンテキスト（INPUT）

| 情報源 | 内容 | タイミング |
|--------|------|-----------|
| System Prompt | ペルソナ定義（25-35歳、6-7年習慣失敗）、7ステップワークフロー、コンテンツルール、4トーン | 起動時に固定 |
| User Message | 「今日のTikTok投稿プロセスを実行しろ」+ 現在のJST時刻（HH:MM）+ 今日の日付 | 起動時に注入 |

**エージェントが起動時に持っている情報はこれだけ。** 昨日の成績も、hookリストも、トレンドも持っていない。全てツール呼び出しで取得する。

### 1.2 エージェントが各ステップで取得するデータ（GROUNDED DATA）

| Step | Tool | 取得データ | フィールド |
|------|------|-----------|-----------|
| - | User Message injection | 現在のJST時刻・今日の日付 | 現在時刻（HH:MM JST）、日付（YYYY-MM-DD） |
| 1 | `get_yesterday_performance` | 昨日の投稿成績 | `posts[]`（like_rate, share_rate等） |
| 2 | `get_hook_candidates` | Thompson Sampling選択hook | `selected.id`, `selected.text`, `selected.tone`, `selected.target_problem_types` |
| 3 | `search_trends` | Exa APIトレンド | `results[]`（title, url, snippet × 5件） |
| 5 | `evaluate_image` | GPT-4o画像評価 | `quality_score`(1-10), `issues[]`, `recommendation`("post"/"regenerate"/"skip") |

### 1.3 エージェントが自分で決定すること（DECISIONS）

| 決定事項 | 現状 | あるべき姿（1.5.0） |
|---------|------|---------------------|
| **Hook選択** | Thompson Samplingから自動選択 | ✅ 実装済み |
| **トレンド検索クエリ** | エージェントが自由に決定 | ✅ 実装済み |
| **画像プロンプト** | エージェントが作成 | ✅ 実装済み |
| **キャプション** | エージェントが作成 | ✅ 実装済み |
| **ハッシュタグ** | エージェントが選択 | ✅ 実装済み |
| **Agent Reasoning** | エージェントが2-3文で説明 | ✅ 実装済み |
| **投稿時刻** | ✅ エージェントはHH:MM（時刻のみ）を出力。日付はコード側で今日に固定 | ✅ 実装済み（1.5.0） |

### 1.4 エージェントの出力（OUTPUT）

現在、エージェントが最終的に出力する（ツール経由で外部に送信する）もの:

| 出力先 | 内容 | ツール |
|--------|------|--------|
| Fal.ai | 画像プロンプト + モデル選択 | `generate_image` |
| Blotato → TikTok | キャプション + 画像URL + ハッシュタグ + `scheduledTime` | `post_to_tiktok` |
| Railway DB | blotato_post_id, caption, hook_candidate_id, agent_reasoning, `scheduled_at` | `save_post_record` |

---

## 2. 修正内容（To-Be）— スケジュール投稿対応

### 2.1 Blotato APIスケジュール機能

Blotato API `/v2/posts` は以下のスケジュールオプションをサポート:

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `scheduledTime` | ISO 8601 string | 指定時刻に投稿（最優先） |
| `useNextFreeSlot` | boolean | 次の空きスロットに自動配置 |
| なし | — | 即時投稿 |

Source: [Blotato Publish Post API](https://help.blotato.com/api/api-reference/publish-post)

### 2.2 TikTok最適投稿時刻データ

複数の大規模調査データ（2025-2026年）:

| 曜日 | 最適時間帯 | ソース |
|------|-----------|--------|
| 月曜 | 6:00, 10:00, 13:00, 22:00 | Shopify, SocialPilot |
| 火曜 | 9:00, 22:00 | RecurPost (2M posts) |
| 水曜 | 14:00-17:00 | SocialPilot |
| 木曜 | 7:00-11:00, 23:00 | Sprout Social (2.7B engagements) |
| 金曜 | 20:00 | RecurPost |
| 土曜 | 17:00, 20:00 | Multiple sources |
| 日曜 | 20:00 | Gudsho |

**Key insight**: 投稿後30-90分の初期エンゲージメントがアルゴリズム推薦に最も影響する。

Sources:
- [Buffer - Best Time to Post on TikTok](https://buffer.com/resources/best-time-to-post-on-tiktok/)
- [Sprout Social - Best Times to Post](https://sproutsocial.com/insights/best-times-to-post-on-tiktok/)
- [SocialPilot - 700K TikTok Insights](https://www.socialpilot.co/blog/best-time-to-post-on-tiktok)
- [Shopify - Best Time to Post](https://www.shopify.com/blog/best-time-to-post-on-tikok)

### 2.3 実装変更（実装済み）

#### A. `post_to_tiktok` ツール — `posting_time`（HH:MM）を受け取る

エージェントは `posting_time`（HH:MM形式、例: `"20:00"`）を出力する。コード側で今日の日付と組み合わせてISO 8601（例: `"2026-01-28T20:00:00+09:00"`）を構築し、Blotato APIの `scheduledTime` に渡す。

```python
# tools.py — post_to_tiktok
# エージェントは HH:MM のみ指定。日付はコードが today で固定。
"posting_time": {
    "type": "string",
    "description": "Posting time in HH:MM format (JST). Code will build ISO 8601 from today's date + this time."
}
```

#### B. System Prompt STEP 3.5 — エージェントはHH:MMのみ出力

```
### STEP 3.5: Decide Posting Time
Based on the selected hook's target_problem_type and today's day of week,
decide the optimal posting time (JST).

Output HH:MM only (e.g., "20:00"). The date is never decided by the agent —
code always uses today's date.

Use these evidence-based guidelines:
- Monday: 10:00 or 22:00 JST
- Tuesday: 9:00 or 22:00 JST
- Wednesday: 14:00-17:00 JST
- Thursday: 7:00-11:00 JST
- Friday: 20:00 JST
- Saturday: 17:00 or 20:00 JST
- Sunday: 20:00 JST

Consider the target persona (25-35歳): evening hours (19:00-23:00) tend to
have higher engagement for self-improvement content.

Pass the decided time as posting_time (HH:MM) to post_to_tiktok.
```

#### C. `save_post_record` — `posting_time`（HH:MM）を受け取り、コード側でISO 8601に変換

`save_post_record` も `posting_time`（HH:MM）を受け取る。コード内で今日の日付と結合しISO 8601に変換してDBの `scheduled_at` カラムに保存する。

```python
# save_post_record ツール定義
"posting_time": {
    "type": "string",
    "description": "Posting time in HH:MM format (JST). Converted to ISO 8601 in code."
}
```

#### D. User Message にJST時刻を注入

エージェント起動時のUser Messageに現在のJST時刻と今日の日付を注入する。これによりエージェントは現在時刻を認識し、過去の時刻を指定しないよう判断できる。

---

## 3. エージェントの完全な INPUT → OUTPUT フロー（1.5.0実装済み）

```
INPUT（固定）:
├── System Prompt: ペルソナ、ワークフロー、コンテンツルール、投稿時刻ガイドライン
└── User Message: 「今日のTikTok投稿を実行しろ」+ 現在JST時刻 + 今日の日付

STEP 1: get_yesterday_performance
├── INPUT: なし
└── OUTPUT: 昨日の投稿成績（posts[], metrics）

STEP 2: get_hook_candidates(strategy="thompson")
├── INPUT: strategy="thompson"
└── OUTPUT: selected hook（id, text, tone, target_problem_types）

STEP 3: search_trends(query=エージェントが決定)
├── INPUT: hookテーマに基づくクエリ
└── OUTPUT: トレンド5件（title, url, snippet）

STEP 3.5: 【エージェントが内部で決定】投稿時刻
├── INPUT: 曜日 + ガイドライン + ペルソナ + 現在JST時刻
└── OUTPUT: posting_time（HH:MM）→ コード側で今日の日付 + HH:MM → ISO 8601に変換

STEP 4: generate_image(prompt=エージェントが作成, model="nano_banana")
├── INPUT: 画像プロンプト + モデル
└── OUTPUT: image_url

STEP 5: evaluate_image(image_url, intended_hook)
├── INPUT: 画像URL + hook文
└── OUTPUT: quality_score, issues[], recommendation
├── score >= 6 → STEP 6
├── score < 6 → STEP 4に戻る（max 2回）
└── 2回失敗 → 一番良い画像でSTEP 6

STEP 6: post_to_tiktok(image_url, caption, hashtags, posting_time)
├── INPUT: 画像URL + キャプション + ハッシュタグ + 投稿時刻（HH:MM）
├── コード: 今日の日付 + posting_time → ISO 8601 → Blotato scheduledTime
└── OUTPUT: blotato_post_id

STEP 7: save_post_record(blotato_post_id, caption, hook_candidate_id, agent_reasoning, posting_time)
├── INPUT: 投稿記録の全フィールド + posting_time（HH:MM）
├── コード: HH:MM → ISO 8601変換 → scheduled_at カラムに保存
└── OUTPUT: record_id
```

**エージェントが決定する6つのこと（1.5.0）:**

| # | 決定事項 | 根拠データ |
|---|---------|-----------|
| 1 | **Hook選択** | Thompson Sampling（成績データベース） |
| 2 | **トレンド検索クエリ** | 選択されたhookのテーマ |
| 3 | **画像プロンプト** | hook + トレンド + ペルソナ |
| 4 | **キャプション** | hook + トレンド + ハッシュタグ |
| 5 | **投稿時刻（HH:MMのみ）** | 曜日 + エンゲージメントデータ + ペルソナ + 現在JST時刻 |
| 6 | **Agent Reasoning** | 全ステップの判断根拠 |

---

## 4. GHA vs Railway: なぜ分離されているか + 統合ロードマップ

### 4.1 現状の分離理由

| 項目 | App Nudge（Railway） | TikTok Agent（GHA） |
|------|---------------------|---------------------|
| 言語 | Node.js (TypeScript) | Python |
| DB接続 | 直接（Prisma ORM） | HTTP API経由（AdminAPIClient） |
| 実行時間 | ~30秒 | ~3-5分（画像生成） |
| なぜこの言語 | APIサーバーと同じ環境 | OpenAI Function Calling SDKがPython先行だった |

**しかし、OpenAI SDK for TypeScript/Node.js も Function Calling を完全サポートしている。** Python を選んだ理由は当時の判断であり、技術的制約ではなくなった。

### 4.2 統合の判断

**Decision: V3（将来）でNode.jsに統合し、Railway上で実行する。**

| 観点 | GHAに統合 | Railwayに統合 |
|------|----------|--------------|
| DB接続 | HTTP API経由（遅い） | **直接Prisma（速い）** |
| 言語統一 | Python（API側と別） | **Node.js（API側と同じ）** |
| ログ・監視 | GHA logs | **Railway logs（既存監視と統合）** |
| コスト | 無料 | CPU課金（~$1-2/日） |
| 実行時間 | 6時間まで | タイムアウト設定可能 |
| スケジュール | cron（5-20分ズレ）| cron（正確）|

**Railwayに統合する理由:**
1. DB直接アクセス（HTTP API経由より高速・信頼性高い）
2. Node.js統一（メンテコスト削減）
3. 既存の監視・ログ基盤と統合
4. App NudgeとTikTok Agentが同じDB・同じコードベースで学習を共有
5. 将来の「1エージェント、複数チャネル」に向けた基盤

**GHAを選ばない理由:**
- DB接続がHTTP API経由になり遅い
- Python/Node.js混在のまま
- スケジュール精度が低い（5-20分ズレ）

### 4.3 統合ロードマップ

| Phase | 内容 | タイミング |
|-------|------|-----------|
| **V1（今）** | Python + GHA。スケジュール投稿追加。 | **1.5.0** |
| **V2** | Node.js書き換え + Railway cron移行 | 1.6.0 |
| **V3** | App Nudge + TikTok Agent統合。1つのエージェントが全チャネル担当 | 1.7.0+ |
| **V4** | 24/7常時稼働エージェント。リアルタイム判断 | 2.0.0 |

**V1（1.5.0）でやること:**
- スケジュール投稿をBlotato `scheduledTime` で実装
- エージェントがWHEN（HH:MMのみ）を決定できるようにする
- Python + GHAのまま（リファクタは次バージョン）

### 4.4 V4 ビジョン: 24/7 自律型プロアクティブエージェント（2.0.0）

> Aniccaの未来。行動変容Nudgeではなく、ユーザーの「仕事・タスク」を自律的にこなすエージェント。
> Claude Code のように動くが、24/7 常時稼働で自分から行動する。

#### コンセプト

| 項目 | 内容 |
|------|------|
| **何か** | VPS上で常時稼働するプロアクティブAIエージェント |
| **何をする** | コード書く、Slack送る、Webクロール、アプリ作る、プロセス自動化 |
| **何が違う** | 指示待ちではなく自発的に行動する。エラーを検知→自動修正→報告 |
| **接続方法** | VPS（Railway/Fly.io）+ Slack Bot + MCP ツール |
| **ユーザーとの対話** | Slack メンション、Webダッシュボード、モバイル通知 |

#### 市場の現状（2025-2026）

| プロダクト | 24/7常時稼働 | プロアクティブ | 月額コスト |
|-----------|-------------|--------------|-----------|
| Claude Code（Agent SDK） | セッション単位 | ❌ 指示待ち | API従量 |
| Cursor Background Agent | タスク完了まで | ❌ 指示待ち | $200/月 |
| Devin (Cognition) | タスク完了まで | ❌ 指示待ち | $500/月 |
| OpenAI Codex | 最大7時間 | ❌ 指示待ち | API従量 |
| Claude-Flow (OSS) | **✅ デーモン** | **✅ 自発的** | VPS + API |
| **Anicca V4（目標）** | **✅ デーモン** | **✅ 自発的** | $220-740/月 |

**→ 完全なプロアクティブ24/7エージェントはまだ市場にない。チャンスがある。**

#### アーキテクチャ

```
┌───────────────────────────────────────────┐
│ VPS (Railway / 常時稼働)                    │
│                                             │
│  ┌─────────────┐  ┌──────────────┐         │
│  │ Scheduler   │  │ Event Listener│         │
│  │ (node-cron) │  │ (Slack/GH)   │         │
│  └──────┬──────┘  └──────┬───────┘         │
│         └────────┬───────┘                  │
│                  ▼                          │
│  ┌──────────────────────────────┐          │
│  │    Task Queue (BullMQ)      │          │
│  │    自発的タスク生成もここ     │          │
│  └──────────────┬──────────────┘          │
│         ┌───────┼───────┐                  │
│         ▼       ▼       ▼                  │
│  ┌────────┐┌────────┐┌────────┐           │
│  │ Code   ││ Slack  ││ Web    │           │
│  │ Skill  ││ Skill  ││ Crawl  │           │
│  │(Claude ││(Bolt.js)││(Play-  │           │
│  │ SDK)   ││        ││wright) │           │
│  └────────┘└────────┘└────────┘           │
│                                             │
│  ┌──────────────────────────────┐          │
│  │  Memory (PostgreSQL+pgvector)│          │
│  │  長期記憶・学習・コンテキスト  │          │
│  └──────────────────────────────┘          │
│                                             │
│  ┌──────────────────────────────┐          │
│  │  MCP Server (ツール統合)     │          │
│  └──────────────────────────────┘          │
└───────────────────────────────────────────┘
```

#### 実行トリガー（3種類）

| パターン | 仕組み | 例 |
|---------|--------|-----|
| **Cron** | 定期実行 | 毎朝6:00にGitHub Issues確認→タスクリスト作成→Slack報告 |
| **イベント** | Webhook/Slack | `@agent これ調べて` → リサーチ → 結果返信 |
| **自発的** | エージェント自身が判断 | エラーログ検知→原因分析→修正PR→Slack報告 |

#### プロアクティブ行動の1日（具体例）

| 時間 | 行動 | トリガー |
|------|------|---------|
| 06:00 | TikTok投稿スケジュール（V1から継承） | Cron |
| 08:00 | GitHub Issues/PR状況確認→今日のタスクリスト→Slack報告 | Cron |
| 随時 | エラーログ監視→異常検知→自動調査→Slack通知 | イベント |
| 随時 | Slackで `@agent` メンション→タスク実行 | イベント |
| 15:00 | 未完了タスク進捗確認→リマインド | Cron |
| 20:00 | 日次レポート生成→Slack投稿 | Cron |
| 週月曜 | 週次コードベース健全性チェック | Cron |

#### スキルシステム

```
skills/
├── code/           ← コーディング（Claude Agent SDK）
│   ├── write-feature.ts
│   ├── fix-bug.ts
│   └── review-pr.ts
├── communication/  ← Slack/メール
│   ├── slack-message.ts
│   └── daily-report.ts
├── web/            ← Web クロール/リサーチ
│   ├── crawl.ts
│   └── research.ts
├── automation/     ← プロセス自動化
│   ├── deploy.ts
│   └── cron-tasks.ts
└── meta/           ← 自己管理
    ├── learn.ts        ← 経験から学習
    └── plan-day.ts     ← 1日の計画立案
```

#### 主要な課題と対策

| 課題 | 対策 |
|------|------|
| **コスト暴走** | 日/月トークン上限設定。ルールベースフィルタでLLM呼び出し前に不要タスク除外。月額$500以内が初期目標 |
| **暴走エージェント** | Bounded Autonomy（有界自律性）。高リスク操作は人間承認必須。タイムアウト設定 |
| **ハルシネーション** | 全出力に検証ステップ。コード変更はテスト通過必須 |
| **セキュリティ** | MCPレベルのアクセス権管理。サンドボックス実行。監査ログ |

#### 技術スタック（推奨）

| レイヤー | 技術 | 理由 |
|---------|------|------|
| ランタイム | Node.js/TypeScript | Claude Agent SDKとの親和性。既存API統一 |
| LLM | Claude API (Agent SDK) | MCPネイティブ。ヘッドレス実行対応 |
| タスクキュー | BullMQ + Redis | リトライ/優先度/遅延実行 |
| メモリ | PostgreSQL + pgvector | 既存DB活用。セマンティック記憶 |
| メッセージング | Slack Bolt.js | イベント駆動。リアルタイム双方向 |
| Webクロール | Playwright | ヘッドレスブラウザ |
| デプロイ | Railway | 既存インフラ。常時稼働対応 |

#### コスト見積もり

| 項目 | 月額 |
|------|------|
| VPS（Railway Worker） | $20-40 |
| Claude API（中程度） | $100-500 |
| Redis（タスクキュー） | $10-20 |
| Slack API | 無料 |
| **合計** | **$130-560/月** |

#### V1→V4 への進化パス

```
V1 (1.5.0): Python + GHA → 1日1回TikTok投稿
    ↓
V2 (1.6.0): Node.js + Railway cron → DB直接、言語統一
    ↓
V3 (1.7.0): 全チャネル統合エージェント → App Nudge + TikTok + 将来のチャネル
    ↓
V4 (2.0.0): 24/7常時稼働 → プロアクティブ、Slack Bot、自発的タスク、長期記憶
```

**Sources:** Cursor Scaling Agents Blog, Devin 2025 Annual Review, OpenAI Codex Agent Loop, Claude Agent SDK Docs, Claude-Flow V3, Gartner Multi-Agent Report 2025

---

## 5. テスト計画

### 5.1 スケジュール投稿テスト — テスト済み・検証完了

エージェントを実行し、`posting_time` を現在時刻+3分に設定。3分後にTikTokに投稿が出現することを確認済み。

| テスト項目 | 結果 |
|-----------|------|
| Blotato `scheduledTime` 送信 | ✅ PASS |
| 3分後にTikTok投稿出現 | ✅ PASS |
| Blotato投稿ステータス | ✅ `"published"` 確認 |
| DB `scheduled_at` カラム追加 | ✅ 動作確認済み |
| `save_post_record` に `scheduled_at` 保存 | ✅ 動作確認済み |

### 5.2 GHA CLIテスト

```bash
# mainマージ後にCLIから実行
gh workflow run anicca-daily-post.yml
gh run list --workflow=anicca-daily-post.yml
gh run watch <run-id>
gh run view <run-id> --log
```

GUI操作は不要。全てターミナルから実行・監視可能。

---

## 6. App Store リリースまでのタスク一覧

| # | タスク | 内容 | 状態 |
|---|--------|------|------|
| 1 | スケジュール投稿実装 | `post_to_tiktok` に `posting_time`（HH:MM）追加 + System Prompt STEP 3.5改修 | ✅ 完了 |
| 2 | `save_post_record` に `scheduled_at` 追加 | DB記録にも投稿予定時刻を保存（`posting_time` HH:MM → ISO 8601変換） | ✅ 完了 |
| 3 | スケジュール投稿テスト | 3分後投稿でBlotato動作確認 | ✅ 完了（3分後テストPASS、Blotato status: `"published"` 確認） |
| 4 | コードレビュー（サブエージェント） | マージ前の最終チェック | ✅ 完了（C-1 validation追加、W-1/S-2/S-3エラーリーク修正） |
| 5 | dev → main マージ | Backend Production デプロイ | 未着手 |
| 6 | GHA CLIテスト | `gh workflow run` で動作確認 | 未着手 |
| 7 | release/1.5.0 作成 | mainから切る | 未着手 |
| 8 | App Store ビルド＆提出 | fastlane release | 未着手 |
