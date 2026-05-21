# Agent Orchestration Spec — Anicca 自律エージェント統合戦略

> **目的**: 5つの外部事例から学んだパターンを Anicca（OpenClaw + Claude Code）に統合するための設計仕様書。
> コンテキストが失われても、このファイル単体で全体像・理由・手順が分かるように記述する。

---

## 0. 背景と学習ソース

### 0.1 分析した外部事例

| # | 事例 | 核心の教訓 | Aniccaへの適用度 |
|---|------|----------|----------------|
| 1 | **Agent Zero**（Docker自律エージェント） | ローカル実行・プライバシー・3モデル使い分け | 思想参考。ツール不要 |
| 2 | **ScreenSnap Pro**（8エージェント×Notion） | 専門化・品質ゲート・Claim Lock・PMエージェント | **1.6.2 Closed-Loop Opsと同等。直接適用** |
| 3 | **10人AIチーム**（Claude Code Agent Teams） | リアルタイム分業・fact-checker常駐・virtual-client | **Claude Code機能そのもの。即利用可能** |
| 4 | **OpenClaw初心者ガイド** | 6ツール構成（Claude/GitHub/Vercel/AWS/Terminal/Telegram） | 通過済み |
| 5 | **ClawRouter**（モデル自動ルーティング） | 14次元スコアリング・4ティアルーティング・USDC課金 | 規模拡大後に検討 |
| 6 | **100x Engineer**（AI時代のエンジニアリング） | Plan→Execute・CLAUDE.md・Night Queue・検証必須 | **全パターンが適用対象** |

### 0.2 Aniccaの現在地（2026年2月9日）

| 項目 | 現状 |
|------|------|
| OpenClaw | VPS稼働中。GPT-4o。cron 3本（メトリクス/ミーティングリマインダー×2） |
| Claude Code | CLAUDE.md + rules 16 + skills 30+ + Serenaメモリ 12+。3ゲート開発ワークフロー運用中 |
| 1.6.2設計 | Closed-Loop Ops（14ファイル）+ trend-hunter（11ファイル）設計完了。未実装 |
| 月額APIコスト | $5-10（低い。ルーティング最適化は不要） |
| Agent Teams | 機能あり。テンプレート未整備 |

### 0.3 現状のギャップ（事例 vs Anicca）

| 事例のパターン | Aniccaの対応状況 | ギャップ |
|--------------|----------------|---------|
| PRODUCT_CONTEXT.md（DO/DON'T） | persona.md + ios_app_architecture メモリ | **DON'Tリストが未明示** |
| Night Queue（寝てる間にPR） | なし | **運用パターン未確立** |
| Known Mistakes（既知のミス蓄積） | Serenaメモリに散在 | **CLAUDE.mdへの昇格ルールなし** |
| Claim Lock（並列タスク競合防止） | ADR-005（VPS sole executor）で部分対応 | **Step Executorレベルのロック未設計** |
| PM Agent（ボトルネック自動検知） | Heartbeat設計あり | **Morgan的チェック項目が未統合** |
| Context File System（構造化コンテキスト） | Serenaメモリ12個 | **cost_constraints, golden_examples 不足** |
| スキル専門化 | 1つのAniccaエージェントが全担当 | **専門スキル分離が未実施** |
| Agent Teamsテンプレート | 機能のみ。テンプレートなし | **定型チーム構成の文書化が必要** |
| デュアルレビュー | codex-review + ユーザー確認 | **AI/人間の責任分担が未明文化** |
| モデルルーティング | GPT-4o固定 | **P3で検討（今は不要）** |

---

## 1. 概要（What & Why）

### What

外部事例から抽出した9つのパターンを、3フェーズに分けてAniccaに導入する。

| Phase | テーマ | 含むパターン | 前提条件 |
|-------|--------|------------|---------|
| **P0** | 基盤強化 | PRODUCT_CONTEXT / Night Queue / Known Mistakes | なし（即着手可） |
| **P1** | エージェント自律化 | Claim Lock / PM Agent / Context拡張 / スキル専門化 | P0完了 |
| **P2** | パイプライン構築 | Agent Teamsテンプレ / 1.6.2実装連携 | P1完了 |
| **P3** | スケール最適化 | モデルルーティング / 分析ダッシュボード | 月額$50+到達時 |

### Why

| 理由 | 根拠 |
|------|------|
| **ハルシネーション防止** | ScreenSnap Proで「存在しない機能を記事に書いた」事故。Aniccaでも Nudge/コンテンツに嘘が混入するリスクがある |
| **並列実行の安全性** | 1.6.2で複数Step Executorが並列動作。Claim Lockなしだと同じタスクを複数が掴む（ScreenSnap Proで実証済み） |
| **自己修復パイプライン** | 監視ダッシュボード < PMエージェント。問題を検知して自動で修復する方が人間の介入が減る |
| **寝てる間の生産性** | Night Queueで8-12時間分の低リスク作業を自動処理。100x Engineerパターン |
| **コンテキスト損失の防止** | CLAUDE.mdの「既知のミス」+ Context File Systemで、セッション間の知識損失を最小化 |

---

## 2. 受け入れ条件

### P0 受け入れ条件

| # | 条件 | 検証方法 |
|---|------|---------|
| AC-01 | PRODUCT_CONTEXT が `.serena/memories/product_context` に存在し、DO 10項目以上 / DON'T 10項目以上を含む | `mcp__serena__read_memory("product_context")` で確認 |
| AC-02 | Night Queue 運用ドキュメントが `.cursor/plans/night-queue.md` に存在し、フロー・テンプレート・制約を含む | ファイル存在確認 + 内容レビュー |
| AC-03 | CLAUDE.md に「既知のミス」セクションが存在し、5項目以上の高頻度ミスパターンを含む | CLAUDE.md の行数が150行以下を維持しつつ、セクションが存在 |
| AC-04 | OpenClaw の `openclaw-anicca.md` に sessionTarget/delivery.mode の正しい設定が明記されている | ファイル内容確認 |

### P1 受け入れ条件

| # | 条件 | 検証方法 |
|---|------|---------|
| AC-05 | Claim Lock パターンが 1.6.2 Closed-Loop Ops Spec に反映されている | `02-data-layer.md` に claim_id カラム設計が存在 |
| AC-06 | Heartbeat に Morgan 的チェック3項目（バックログ枯渇/滞留/バランス）が設計されている | `closed-loop-ops/` 内の該当Specに記載 |
| AC-07 | Serenaメモリに `product_context`, `cost_constraints`, `golden_examples` が存在する | `mcp__serena__list_memories` で確認 |
| AC-08 | OpenClaw スキル分離設計が文書化されている（4専門スキル以上） | `openclaw-anicca.md` または専用Specに記載 |
| AC-09 | デュアルレビューの責任分担が `.claude/rules/dev-workflow.md` に明記されている | ファイル内容確認 |

### P2 受け入れ条件

| # | 条件 | 検証方法 |
|---|------|---------|
| AC-10 | Agent Teams テンプレートが 3種類以上 `.claude/skills/` に存在する | ファイル存在確認 |
| AC-11 | Night Queue + Agent Teams の統合フローが文書化され、1回以上テスト実行されている | 実行ログまたはPR |

---

## 3. As-Is / To-Be

### 3.1 PRODUCT_CONTEXT（P0-1）

**As-Is**: Aniccaの機能定義が `persona.md`（ターゲットユーザー）と `ios_app_architecture`（技術構成）に分散。「Aniccaが**やらないこと**」の明示的リストが存在しない。

**To-Be**: `.serena/memories/product_context` に以下を集約。

```
## Aniccaが提供する機能（DO）
- ProblemType ベースの通知（Nudge）
- ルールベース + LLM生成の Nudge コンテンツ
- 13種類の ProblemType 選択（オンボーディング）
- Nudge フィードバック（役に立った/邪魔だった）
- サブスクリプション（$9.99/月、1週間トライアル）
- 6言語ローカライズ（ja, en, de, es, fr, pt-BR）
- Sign in with Apple

## Aniccaが提供しない機能（DON'T）
- チャット/メッセージング機能
- SNS連携/共有機能
- ゲーミフィケーション/ポイント/バッジ
- コミュニティ/フォーラム
- 習慣トラッカー（ストリーク、チェックリスト）
- 瞑想ガイド/音声コンテンツ
- カレンダー連携
- ウェアラブルデバイス連携
- オフライン専用モード（APIとの通信が必要）
- 無料プラン（トライアルのみ）

## エージェントが言及してはいけないこと
- 未実装の機能を「できます」と言う
- 競合アプリの具体名での批判
- 医療アドバイス・診断
- 「必ず改善する」等の断定的な効果保証
```

### 3.2 Night Queue（P0-2）

**As-Is**: タスク蓄積→バッチ実行の運用パターンが存在しない。全タスクがリアルタイム・手動実行。

**To-Be**: `.cursor/plans/night-queue.md` に以下のフローを文書化。

```
## Night Queue 運用フロー

### 日中（蓄積フェーズ）
- 低リスクタスクを night-queue.md の「待機リスト」に追記
- 対象: リファクタ、リンター修正、テスト追加、ドキュメント更新、依存関係更新

### 退勤前（起動フェーズ）
1. night-queue.md から3-5個のタスクを選択
2. 各タスクに worktree を作成: git worktree add ../anicca-nq-<task> -b nq/<task>
3. Agent Teams（TeamCreate）で起動
4. 各エージェントにタスク割り当て（TaskCreate + TaskUpdate）
5. run_in_background: true で実行

### 翌朝（レビューフェーズ）
1. TaskList でステータス確認
2. 各 worktree のドラフト PR をレビュー
3. 良いもの → dev にマージ
4. 悪いもの → クローズ + 原因を「既知のミス」に追記
5. worktree クリーンアップ

### 制約
- Night Queue タスクは main/dev に直接コミットしない（worktree必須）
- 同じファイルを触るタスクを同時に入れない
- バックエンドAPI変更を含むタスクは Night Queue 対象外（手動デプロイ必要）
```

### 3.3 Known Mistakes（P0-3）

**As-Is**: 既知のミスが Serenaメモリと MEMORY.md に散在。CLAUDE.md に統合セクションなし。

**To-Be**: CLAUDE.md に「既知のミス」セクション追加（10行以内）。詳細は Serenaメモリに委譲。

```markdown
### 既知のミス（エージェント共通）

| ミスパターン | 正しい対応 |
|------------|-----------|
| delivery.mode: "silent" | 無効。"announce" or "none" のみ |
| sessionTarget: "main" でcron | agentTurn を使う |
| announce + exec in prompt | 二重投稿になる。none + exec を使う |
| Mixpanel /api/query/events | /api/2.0/segmentation が正しい |
| 存在しない機能を言及 | product_context メモリの DON'T を確認 |

詳細: `mcp__serena__read_memory("openclaw-anicca-setup")`
```

### 3.4 Claim Lock パターン（P1-1）

**As-Is**: ADR-005（VPS sole executor）で「実行者は1つ」を保証。しかし Heartbeat が5分ごとに動き、前回の未完了ステップと新規ステップが競合する可能性がある。

**To-Be**: OpsMissionStep テーブルに Claim Lock を追加。

```
## テーブル変更（Prisma）
OpsMissionStep {
  ...既存フィールド...
  claimId     String?    // ユニーク claim ID（executor-{timestamp}-{random}）
  claimedAt   DateTime?  // claim 取得時刻
  claimExpiry DateTime?  // claim 有効期限（デフォルト30分）
}

## Claim → Verify → Execute フロー
1. Heartbeat が pending ステップを取得
2. claimId を生成して書き込み（UPDATE ... WHERE claimId IS NULL）
3. 再取得して自分の claimId が残っているか確認
4. 残っていれば実行開始。残っていなければスキップ
5. 実行完了 or 失敗で claimId をクリア
6. claimExpiry を超えたステップは自動解放（stale recovery）
```

### 3.5 PM Agent / Heartbeat 統合（P1-2）

**As-Is**: Heartbeat の設計に evaluateTriggers / processReactionQueue / promoteInsights / recoverStaleSteps がある。ボトルネック検知は未設計。

**To-Be**: Heartbeat に Morgan 的チェック3項目を追加。

```
## Heartbeat 拡張（5分ごと）
既存:
  1. evaluateTriggers()
  2. processReactionQueue()
  3. promoteInsights()
  4. recoverStaleSteps()

追加（Morgan パターン）:
  5. checkBacklogHealth()
     - OpsProposal(status=pending) が 0件 → trend-hunter トリガーを生成
     - 閾値: 最低3件の pending proposal を維持
  6. detectStalledSteps()
     - OpsMissionStep(status=in_progress, updatedAt < now-30min) → アラート
     - 3回連続アラート → 自動キャンセル + 再提案
  7. checkPipelineBalance()
     - 各ステータスの件数を集計
     - 特定ステータスに偏りがあれば Slack 通知
```

### 3.6 Context File System 拡張（P1-3）

**As-Is**: Serenaメモリ 12個。product_context / cost_constraints / golden_examples が不足。

**To-Be**: 以下の3メモリを追加。

```
## 追加メモリ

### product_context（P0-1 と同一）
- DO/DON'T リスト
- 上記 3.1 参照

### cost_constraints
- Railway: Staging/Production のプラン・制限
- OpenAI API: 月額上限目安（$50）
- Anthropic API: Claude Code 利用量
- RevenueCat: 無料枠の範囲
- VPS: Hostinger $6/月
- パフォーマンスSLA: API応答 < 2秒、Nudge配信 < 5秒

### golden_examples
- 良い Spec の実例（closed-loop-ops の README 等）
- 良い PR の実例（コミットメッセージ、変更サマリ）
- 良い Nudge テキストの実例（ルールベース / LLM 生成）
- 良い CLAUDE.md エントリの実例
```

### 3.7 OpenClaw スキル専門化（P1-4）

**As-Is**: 1つの `anicca` エージェントが全タスクを担当（メトリクス、リマインダー、Slack応答）。

**To-Be**: 4つの専門スキルに分離。

```
## スキル分離設計

### metrics-specialist
- 担当: ASC/RC/Mixpanel データ取得、レポート生成
- ツール: exec（curl）、web_search
- 制約: Slack投稿は #metrics チャンネルのみ

### content-specialist
- 担当: コンテンツ作成、品質チェック、X/TikTok投稿下書き
- ツール: exec、web_search、browser
- 制約: 投稿は下書きのみ。公開は人間承認後

### nudge-analyst
- 担当: Nudge効果分析、改善提案、フィードバック集計
- ツール: exec（DB クエリ）、memory
- 制約: Nudge内容の変更は提案のみ。実装は別フロー

### meeting-manager
- 担当: ミーティングリマインダー、議題管理、祝日チェック
- ツール: exec（curl: holidays-jp API）、slack
- 制約: #meeting チャンネルのみ

## 移行方法
1. 各スキルファイルを /usr/lib/node_modules/openclaw/skills/ に作成
2. cron jobs を各スキルに紐付け
3. openclaw.json の bindings を更新
4. 段階的に移行（1スキルずつ切り替え、動作確認後に次へ）
```

### 3.8 Agent Teams テンプレート（P2-1）

**As-Is**: Agent Teams 機能はあるが、チーム構成を毎回ゼロから設計。

**To-Be**: 3種類のテンプレートを `.claude/skills/` に作成。

```
## テンプレート 1: team-ios-api-parallel（iOS + API 並列実装）
- ios-dev: iOS側の実装（SwiftUI/Swift）
- api-dev: API側の実装（Express/Prisma）
- tester: 両方のテスト作成（TDD）
- team-lead: 進行管理、ファイル境界監視、マージ判断
- 制約: ios-dev と api-dev は同じファイルを触らない

## テンプレート 2: team-research（リサーチ並列）
- researcher-1: Web検索・記事収集
- researcher-2: コード/ドキュメント探索
- analyst: 収集データの分析・比較表作成
- fact-checker: 常駐。各出力を逐次検証
- 制約: 書き込みなし。リサーチ結果のみ返す

## テンプレート 3: team-refactor（大規模リファクタ）
- refactor-a: モジュールA担当
- refactor-b: モジュールB担当
- tester: 既存テスト維持 + 新規テスト
- reviewer: 各変更をレビュー（品質ゲート）
- 制約: 各リファクタは独立worktree。同じファイル禁止
```

---

## 4. テストマトリックス

| # | To-Be | 検証方法 | カバー |
|---|-------|---------|--------|
| T-01 | PRODUCT_CONTEXT に DO 10+ / DON'T 10+ | Serenaメモリ読み取り確認 | AC-01 |
| T-02 | Night Queue フローが文書化されている | ファイル存在 + 内容レビュー | AC-02 |
| T-03 | CLAUDE.md に既知のミス5項目以上 | CLAUDE.md 読み取り確認 | AC-03 |
| T-04 | CLAUDE.md が150行以下 | `wc -l CLAUDE.md` | AC-03 |
| T-05 | sessionTarget 設定が正しく文書化 | openclaw-anicca.md 確認 | AC-04 |
| T-06 | Claim Lock が Spec に反映 | 02-data-layer.md に claimId 記載 | AC-05 |
| T-07 | Heartbeat に Morgan チェック3項目 | 該当Spec確認 | AC-06 |
| T-08 | Serenaメモリ3つ追加 | list_memories で確認 | AC-07 |
| T-09 | スキル分離設計が文書化 | openclaw-anicca.md 確認 | AC-08 |
| T-10 | デュアルレビュー責任分担が明記 | dev-workflow.md 確認 | AC-09 |
| T-11 | Agent Teams テンプレート3種類 | ファイル存在確認 | AC-10 |
| T-12 | Night Queue + Teams 統合テスト1回 | 実行ログ or PR 存在 | AC-11 |

---

## 5. 境界

### やること

| 対象 | 内容 |
|------|------|
| Serenaメモリ新規作成 | product_context, cost_constraints, golden_examples |
| CLAUDE.md 更新 | 既知のミスセクション追加（150行制限内） |
| Night Queue 運用ドキュメント | `.cursor/plans/night-queue.md` |
| 1.6.2 Spec 更新 | Claim Lock, Morgan パターンの追記 |
| OpenClaw スキル分離設計 | 設計文書のみ（VPS実装はP2） |
| Agent Teams テンプレート | `.claude/skills/` にテンプレートファイル |
| dev-workflow.md 更新 | デュアルレビューセクション追加 |

### やらないこと

| 対象 | 理由 |
|------|------|
| 1.6.2 のコード実装 | このSpecはドキュメント・設計のみ |
| ClawRouter 導入 | 月額コストが$50未満の現状では不要 |
| VPS上のOpenClaw設定変更 | 設計文書完了後に別タスクで実施 |
| Agent Teams の実コード実行 | テンプレート作成のみ。実行はP2テスト時 |
| 新しい Prisma migration | 設計のみ。実装は1.6.2実装フェーズ |
| スキルの SKILL.md 作成 | P2 で実装時に作成 |

### 触るファイル

| ファイル | 操作 |
|---------|------|
| `.cursor/plans/agent-orchestration-spec.md` | 新規作成（本ファイル） |
| `.cursor/plans/night-queue.md` | 新規作成 |
| `CLAUDE.md` | 更新（既知のミスセクション追加） |
| `.claude/rules/dev-workflow.md` | 更新（デュアルレビュー追加） |
| `.cursor/plans/reference/openclaw-anicca.md` | 更新（スキル分離設計追加） |
| `.cursor/plans/ios/1.6.2/implementation/closed-loop-ops/02-data-layer.md` | 更新（Claim Lock追加） |
| Serenaメモリ 3件 | 新規作成 |

### 触らないファイル

| ファイル | 理由 |
|---------|------|
| `aniccaios/` 配下の全Swift | コード実装なし |
| `apps/api/` 配下の全TS | コード実装なし |
| VPS上の `openclaw.json` | 設計のみ |
| `prisma/schema.prisma` | 設計のみ |

---

## 6. 実行手順

### Phase 0（即着手可、並列実行可）

| ステップ | コマンド/操作 | 完了条件 |
|---------|-------------|---------|
| P0-1a | `mcp__serena__write_memory("product_context", ...)` | メモリ作成完了 |
| P0-1b | OpenClaw 側の参照設計を `openclaw-anicca.md` に追記 | ファイル更新完了 |
| P0-2 | `.cursor/plans/night-queue.md` を作成 | ファイル作成完了 |
| P0-3a | Serenaメモリから高頻度ミスを抽出 | リスト作成 |
| P0-3b | CLAUDE.md に「既知のミス」セクション追加 | 150行以下を確認 |
| P0-4 | `openclaw-anicca.md` の sessionTarget 記載を確認・更新 | 確認完了 |

### Phase 1（P0完了後）

| ステップ | コマンド/操作 | 完了条件 |
|---------|-------------|---------|
| P1-1 | `02-data-layer.md` に Claim Lock 設計を追記 | Spec更新完了 |
| P1-2 | Heartbeat 該当 Spec に Morgan チェック追記 | Spec更新完了 |
| P1-3a | `mcp__serena__write_memory("cost_constraints", ...)` | メモリ作成完了 |
| P1-3b | `mcp__serena__write_memory("golden_examples", ...)` | メモリ作成完了 |
| P1-4 | スキル分離設計を `openclaw-anicca.md` に追記 | 設計文書完了 |
| P1-5 | `dev-workflow.md` にデュアルレビューセクション追加 | ファイル更新完了 |

### Phase 2（P1完了後）

| ステップ | コマンド/操作 | 完了条件 |
|---------|-------------|---------|
| P2-1 | `.claude/skills/` にテンプレート3種作成 | ファイル作成完了 |
| P2-2 | Night Queue + Agent Teams 統合テスト | 1回以上実行してPR作成 |
| P2-3 | 1.6.2 Closed-Loop Ops 実装開始 | 別Specに従う |

---

## 7. 依存関係マップ

```
P0（並列実行可）                P1（P0完了後）              P2（P1完了後）
┌──────────────┐
│ P0-1         │──→ P1-1 Claim Lock
│ PRODUCT_     │──→ P1-3 Context拡張
│ CONTEXT      │──→ P1-4 スキル専門化
└──────────────┘
┌──────────────┐
│ P0-2         │──→ P2-1 Teamsテンプレ
│ Night Queue  │──→ P2-2 統合テスト
└──────────────┘
┌──────────────┐
│ P0-3         │（独立。いつでも完了可）
│ Known        │
│ Mistakes     │
└──────────────┘
                    P1-1 ──→ P1-2 PM Agent
                    P1-5 デュアルレビュー（独立）
```

---

## 8. E2E判定

| 項目 | 値 |
|------|-----|
| UI変更 | なし |
| 新画面 | なし |
| 新ボタン/操作 | なし |
| 結論 | Maestro E2Eシナリオ: **不要**（理由: 全てドキュメント・設計変更のみ。コード変更なし） |

---

## 9. リスクと軽減策

| リスク | 影響 | 軽減策 |
|--------|------|--------|
| CLAUDE.md が150行を超える | コンテキスト圧迫 | 既知のミスは5項目に絞り、詳細はSerenaメモリに委譲 |
| Night Queue でエージェントが暴走 | 意図しないコード変更 | worktree必須 + main/dev直接コミット禁止 + CI必須 |
| スキル専門化でOpenClaw設定が複雑化 | 運用負荷増 | 段階的移行（1スキルずつ） |
| Claim Lock の実装漏れ | 並列実行時のデータ競合 | テストマトリックスT-06で検証 |
| テンプレートが実態と乖離 | 使われなくなる | P2テストで実運用し、フィードバックで更新 |

---

## 10. 外部ツール・事例の詳細リファレンス

> **目的**: 各記事・ツールの要点を保存する。コンテキストが失われても「これ何だっけ？」にならないように。

### 10.1 Agent Zero（Docker自律エージェント）

| 項目 | 内容 |
|------|------|
| URL | https://www.agent-zero.ai/ |
| 何か | 自分のPC/サーバーで動く無料のAIエージェント。全データがローカルに留まる |
| 仕組み | Docker コンテナ内にLinux OS丸ごと。チャットモデル/ユーティリティモデル/ブラウザモデルの3枠でコスト最適化 |
| 強み | OSS、プライバシー最強、APIドキュメントを渡せば何でもツール化、シークレット管理（AIにもキーが見えない） |
| 弱み | セットアップが技術者向け。モデル自体は外部API依存 |
| Aniccaへの適用 | **今は不要。** 思想（ローカル実行・モデル使い分け）は参考。OpenClawで同等のことは既にできている |
| 無料トークン | Agent Zeroの暗号通貨トークンをステークすると毎日無料AI推論クレジットがもらえる仕組み。月額課金の代替 |

### 10.2 ScreenSnap Pro（8エージェント×Notionパイプライン）

| 項目 | 内容 |
|------|------|
| 何か | OpenClaw + 8専門エージェントで、記事の企画→執筆→校正→公開→SNS拡散→分析を24時間自動化 |
| 構成 | Scout(リサーチ) → Quill(執筆) → Sage(品質) → Ezra(公開) → Herald(SNS) → Archie(分析) + Morgan(PM) + Lurker(Reddit) |
| 中央ハブ | Notion DB（ステータス遷移: Backlog → To Do → In Progress → Review → Ready to Publish → Done） |
| 成果 | 10日で80+記事執筆、41公開。記事あたり$0.70。人間の作業=1日15分 |
| 壊れたこと | (1) レースコンディション → Claim Lock (2) ハルシネーション → PRODUCT_CONTEXT.md (3) cron動かない → isolated session (4) 記事長すぎ → 読みやすさゲート (5) 404リンク → Status=Done確認 (6) 重複投稿 → Claimフラグ |
| Aniccaへの適用 | **直接適用。** Claim Lock/Morgan/品質ゲート/スキル専門化を1.6.2に統合。Notion = Railway PostgreSQL |

### 10.3 10人AIチーム（Claude Code Agent Teams）

| 項目 | 内容 |
|------|------|
| 何か | Claude Code の Agent Teams 機能で、デスクリサーチを9体のAIに分業させた体験談 |
| 構成 | data-collector×2, analyst, fact-checker(常駐), strategist, virtual-client×2, formatter/writer, team-lead, 人間 |
| 発見 | (1) fact-checkerは「後まとめ」ではなく「常駐リアルタイム検証」が正解 (2) PMはAIの方が向いている (3) 人間の役割＝問い設計+最終判断+AIにできない領域 |
| Aniccaへの適用 | **Claude Codeの既存機能（TeamCreate/TaskCreate/SendMessage）で即再現可能。** テンプレート化してP2で導入 |

### 10.4 OpenClaw初心者ガイド

| 項目 | 内容 |
|------|------|
| 何か | OpenClaw セットアップに必要な6ツール（Claude/GitHub/Vercel/AWS/Terminal/Telegram）の紹介 |
| Aniccaへの適用 | **完全通過済み。** AniccaはHostinger VPS + Slack（Telegramではなく）で既に稼働中 |

### 10.5 ClawRouter（モデル自動ルーティング）

| 項目 | 内容 |
|------|------|
| URL | https://github.com/BlockRunAI/ClawRouter |
| 何か | OpenClawプラグイン。リクエストの内容を分析して、一番安いモデルに自動ルーティングする |
| 仕組み | 14次元の重みスコアリング（ローカル実行、<1ms）→ 4ティア（SIMPLE/MEDIUM/COMPLEX/REASONING）に分類 → 最安モデルに送信 |
| 14次元 | 推論マーカー(0.18), コード存在(0.15), 簡単指標(0.12), マルチステップ(0.12), 技術用語(0.10), トークン数(0.08), 創造性(0.05), 質問複雑度(0.05), 制約数(0.04), 命令動詞(0.03), 出力形式(0.03), ドメイン特化(0.02), 参照複雑度(0.02), 否定複雑度(0.01) |
| ティア→モデル | SIMPLE=Gemini Flash($0.60/M, 45%), MEDIUM=DeepSeek($0.42/M, 35%), COMPLEX=Opus($75/M, 15%), REASONING=DeepSeek Reasoner($0.42/M, 5%) |
| コスト削減 | ブレンド$3.17/M vs Opus単体$75/M = **96%削減**。開発者の体験: 月$4,660→約$800 |
| 支払い | x402プロトコル。USDC（暗号通貨ステーブルコイン）on Baseネットワーク。APIキー不要、ウォレット署名で認証。リクエスト単位課金 |
| 日本語対応 | あり（証明、こんにちは、アルゴリズム等のキーワード検出） |
| 導入方法 | `curl -fsSL https://raw.githubusercontent.com/BlockRunAI/ClawRouter/main/scripts/reinstall.sh \| bash` → ウォレットにUSDC送金 → `openclaw gateway restart` |
| 強み | OSS、ローカルルーティング（プライバシー）、30+モデル対応、1コマンド導入 |
| 弱み | USDC管理が必要、BlockRun APIへの依存、キーワードベース判定（ニュアンスは拾えない）、日本語精度は英語より低い可能性 |
| **Aniccaへの適用** | **P3（月額$50+到達時）に導入検討。** 現在の月$5-10では削減効果が$2-3程度で手間に見合わない |
| **導入トリガー** | 1.6.2 Closed-Loop Ops稼働 → Heartbeat(5分毎) + Step Executor並列 → リクエスト数10-100倍 → コスト最適化が必要になる |
| **導入時の注意** | Kill Switchタスク（send_nudge, post_x等）はCOMPLEX固定にする。安いモデルに回すと品質リスク |

### 10.6 100x Engineer（AI時代のエンジニアリング手法）

| 項目 | 内容 |
|------|------|
| 何か | 「AIにコードを書かせるのではなく、AIを使ってシステムを設計する人が100xエンジニア」という記事 |
| 5層スタック | (1) AI-first IDE (2) ターミナルエージェント（Claude Code） (3) バックグラウンドエージェント (4) チャットモデル (5) AIコードレビュー |
| 核心パターン | Plan→Execute（計画が契約）/ CLAUDE.md（組織の記憶）/ Night Queue（寝てる間にPR）/ デュアルレビュー / 検証必須 |
| Boris Cherny方式 | 5つのClaude Codeセッションを並列実行。人間のループ: Direct→Dissect→Delegate |
| 人間の役割 | 作業者 → **判断者**。「何をやりたいか」を決める + AIにできない領域を担当 + 最終チェック |
| Aniccaへの適用 | **全パターン適用対象。** CLAUDE.md/rules/specs/3ゲートで大部分は既に実践中。Night Queueが唯一の未導入パターン |

---

## 11. 用語集（クイックリファレンス）

| 用語 | 定義 | 出典 |
|------|------|------|
| **Night Queue** | 低リスクタスクを日中に蓄積し、夜間にバッチ実行するパターン | 100x Engineer 記事 |
| **Claim Lock** | 並列エージェントが同じタスクを掴まないための排他制御 | ScreenSnap Pro 記事 |
| **Morgan パターン** | PMエージェントがボトルネックを検知し、他エージェントを生成して自動修復 | ScreenSnap Pro 記事 |
| **PRODUCT_CONTEXT** | エージェントのハルシネーション防止のための DO/DON'T リスト | ScreenSnap Pro 記事 |
| **デュアルレビュー** | AI（スタイル/バグ）+ 人間（設計/セキュリティ）の二段階レビュー | 100x Engineer 記事 |
| **Context File System** | エージェントに渡すコンテキストを構造化・永続化する仕組み | 100x Engineer 記事 |
| **Heartbeat** | 5分ごとに実行されるシステム巡回処理 | 1.6.2 Closed-Loop Ops 設計 |
| **Step Executor** | OpsMissionStep を実行する個別ワーカー | 1.6.2 Closed-Loop Ops 設計 |

---

最終更新: 2026年2月9日
作成者: Claude Code (Opus 4.6)
