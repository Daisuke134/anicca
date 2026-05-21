# CLAUDE.md コンパクト化計画（v2 - レビュー反映済み）

## 概要（What & Why）

CLAUDE.mdが1,936行/43,000文字に膨張し、パフォーマンス警告が出ている。
Anthropic公式推奨は300行以下。現状は6.5倍超過。

**なぜ問題か:**
- CLAUDE.mdが長すぎるとClaudeが指示全体を無視する確率が上がる（Anthropic公式見解）
- 毎セッション開始時に全文読み込まれ、コンテキストウィンドウを圧迫
- 重複情報が多く、矛盾も発生している

**ゴール:**
- CLAUDE.md: 1,936行 → **~400行**
- パフォーマンス警告の解消
- **注意:** `.claude/rules/`も毎セッション読み込まれるため、総トークン負荷は「再編成による優先度整理」が主な改善。頻度の低い情報は`.cursor/plans/reference/`（自動読み込みなし）に移動して総負荷も削減する。

---

## 受け入れ条件

| # | 条件 | 検証方法 |
|---|------|---------|
| 1 | CLAUDE.mdが400行以下 | `wc -l CLAUDE.md` |
| 2 | 削除した情報がゼロ（全て移動先に存在） | 移動先ファイルの存在確認 |
| 3 | CLAUDE.mdに残った情報は「毎セッション必須」のものだけ | レビューで確認 |
| 4 | パフォーマンス警告が消える（43k文字 → ~10k文字） | Claude Code起動時に確認 |
| 5 | ワークツリー矛盾が解消されている | レビューで確認 |
| 6 | 既存`.claude/rules/`ファイルとの重複がない | ファイル内容確認 |
| 7 | ロールバック手順が定義されている | Specに記載 |

---

## As-Is / To-Be

### As-Is: 現在のCLAUDE.md構造（1,936行）

| # | セクション | 行数 | 判定 | 移動先 |
|---|-----------|------|------|--------|
| 1 | 意思決定ルール | 24 | KEEP | - |
| 2 | ベストプラクティス検索 | 34 | KEEP | - |
| 3 | 出力形式ルール | 3 | KEEP | - |
| 4 | テスト範囲ルール | 28 | KEEP（トリム） | - |
| 5 | ブランチルール | 78 | KEEP（トリム、環境変数テーブルは保持） | - |
| 6 | バージョニングルール | 14 | MERGE → 既存 git-workflow.md | `.claude/rules/git-workflow.md` |
| 7 | 後方互換ルール | 35 | KEEP（トリム、コード例削除） | - |
| 8 | コミット・プッシュルール | 4 | REMOVE（git-workflow.mdに既存） | - |
| 9 | 言語ルール | 5 | KEEP | - |
| 10 | リファクタリング方針 | 16 | MERGE → 既存 coding-style.md | `.claude/rules/coding-style.md` |
| 11 | 3ゲート開発ワークフロー | 50 | MOVE | `.claude/rules/dev-workflow.md`（新規） |
| 12 | 並列開発ルール (Worktrees) | 139 | MOVE | `.claude/rules/worktree.md`（新規） |
| 13 | 実機デプロイ自動化 | 77 | MOVE | `.claude/rules/deployment.md`（新規） |
| 14 | マージ前の最終確認 | 32 | KEEP（トリム） | - |
| 15 | API後方互換性ルール | 42 | MERGE → #7に統合 | - |
| 16 | Landing Page (Netlify) | 44 | MOVE | `.claude/rules/deployment.md` に統合 |
| 17 | コンテンツ変更ルール | 13 | KEEP | - |
| 18 | Gitトラブルシューティング | 26 | MERGE → 既存 git-workflow.md | `.claude/rules/git-workflow.md` |
| 19 | App Storeリンクルール | 10 | MOVE | `.claude/rules/deployment.md` に統合 |
| 20 | リリース管理 Q&A | 76 | REMOVE（Q6,Q7のみdev-workflow.mdに移動） | Q6,Q7 → `.claude/rules/dev-workflow.md` |
| 21 | Specファイルの書き方 | 104 | MOVE | `.claude/rules/spec-writing.md`（新規） |
| 22 | プロジェクト概要 | 22 | KEEP | - |
| 23 | サブスクリプション & Paywall | 21 | KEEP | - |
| 24 | ペルソナ定義（詳細版） | 61 | REMOVE（コンパクト版#32で十分。外部ファイル存在を検証後に削除） | - |
| 25 | iOS実装状況 | 53 | KEEP | - |
| 26 | 開発ワークフロー (Kiro) | 16 | KEEP（トリム） | - |
| 27 | ワークツリールール（絶対厳守） | 45 | REMOVE（#12の重複。矛盾解消はTo-Be参照） | - |
| 28 | チェックリスト（作業開始時） | 8 | REMOVE（#27の再重複） | - |
| 29 | TDD & テスト戦略 | 316 | MERGE → 既存 testing.md を拡張 | `.claude/rules/testing.md`（既存を拡張） |
| 30 | ユーザー情報 | 6 | KEEP | - |
| 31 | ツール・スキル・MCP使用ルール | 164 | MERGE → 既存 skill-subagent-usage.md + 新規 tool-usage.md | `.claude/rules/tool-usage.md`（新規）、重複部分は既存に統合 |
| 32 | ペルソナ（コンパクト版） | 16 | KEEP | - |
| 33 | セッション開始時の必須アクション | 9 | KEEP | - |
| 34 | 実装完了時の必須アクション | 19 | KEEP | - |
| 35 | API Key & Secret管理 | 102 | MOVE（Railway URLのみCLAUDE.mdに残す） | `.cursor/plans/reference/secrets.md`（非自動読み込み） |
| 36 | Cronジョブアーキテクチャ | 31 | MOVE | `.cursor/plans/reference/infrastructure.md`（非自動読み込み） |
| 37 | 1.5.0で学んだ教訓 | 67 | SPLIT: FK制約パターン→coding-style.md、Railway教訓→infrastructure.md、GHA教訓→git-workflow.md | 各所に分散統合 |
| 38 | Daily Metrics Report | 54 | MOVE | `.cursor/plans/reference/daily-metrics.md`（非自動読み込み） |
| 39 | 日報 | 6 | KEEP | - |
| 40 | 最終更新日 | 1 | KEEP | - |

### To-Be: 新しいCLAUDE.md構造（~400行）

```
1. 絶対ルール（~100行）
   - 意思決定ルール（選択肢出すな）
   - ベストプラクティス検索ルール
   - 出力形式ルール（テーブル使え）
   - テスト範囲ルール（変更した部分だけ）
   - 言語ルール（日本語で返す）
   - コンテンツ変更ルール（Before/After示せ）

2. ブランチ & デプロイ（~80行）
   - ブランチ構成テーブル（dev/main/release）
   - Railway環境（サービス名 + 環境変数テーブル ← 保持）
   - 後方互換の核心ルール（コード例なし、API + iOS統合版）
   - マージ前確認ルール（要約版）
   - ワークツリールール（1行要約 + 詳細参照リンク）
   - Fastlane必須（1行。xcodebuild禁止。詳細はtool-usage.md）

3. プロジェクト概要（~100行）
   - 技術スタック
   - サブスクリプション情報
   - iOS実装状況
   - ペルソナ（コンパクト版）
   - Railway URL（Staging/Production）

4. セッション管理（~50行）
   - セッション開始時アクション
   - 実装完了時アクション
   - 開発コマンド一覧
   - 日報パス

5. 参照先インデックス（~30行）
   - .claude/rules/ ファイル一覧と用途
   - .cursor/plans/reference/ ファイル一覧と用途
```

### To-Be: ファイル移動先

#### `.claude/rules/`（毎セッション自動読み込み）— 高頻度で必要な情報のみ

| ファイル | 内容 | 既存/新規 |
|---------|------|----------|
| `coding-style.md` | 既存 + リファクタリング方針 + FK制約パターン | 既存を拡張 |
| `git-workflow.md` | 既存 + バージョニング + Gitトラブルシューティング + GHA教訓 + Q7(hotfix) | 既存を拡張 |
| `testing.md` | 既存を `testing-strategy.md` にリネーム。TDD全内容を統合 | 既存をリネーム+拡張 |
| `security.md` | 変更なし | 既存のまま |
| `skill-subagent-usage.md` | 変更なし（tool-usage.mdと役割分担） | 既存のまま |
| `dev-workflow.md` | 3ゲート + Feature Flag(Q6) + hotfix(Q7) | **新規** |
| `worktree.md` | 並列開発ルール全体 | **新規** |
| `deployment.md` | 実機デプロイ + Netlify + App Storeリンク | **新規** |
| `spec-writing.md` | Specファイルの書き方 | **新規** |
| `tool-usage.md` | MCP優先ルール + Fastlane + Maestro MCP | **新規** |

**合計: 10ファイル**（既存5 + 新規5）

#### `.cursor/plans/reference/`（自動読み込みなし）— 低頻度の参照情報

| ファイル | 内容 | 頻度 |
|---------|------|------|
| `secrets.md` | API Key名・用途一覧、GitHub Secrets、Railway環境変数詳細 | デプロイ時のみ |
| `infrastructure.md` | Cronジョブ構成 + Railway運用ルール + Railway教訓 | インフラ作業時のみ |
| `daily-metrics.md` | Daily Metrics Report詳細 | メトリクス作業時のみ |

---

## ワークツリー矛盾の解消

**矛盾:** セクション5「単独作業時はdevで直接開発」 vs セクション27「devでの直接作業は禁止」

**決定:** 「原則ワークツリーを使う。ただしCLAUDE.md更新・ドキュメント変更などコード以外の変更はdev直接コミット可。」

**理由:**
- セクション27は後から追加された＝ユーザーの意図が進化した
- 全てにワークツリーを強制すると、ドキュメント1行変更でも余計なオーバーヘッド
- コード変更は隔離が安全、ドキュメント変更は競合リスクが低い

---

## 既存ファイル統合計画（BLOCKING issue #2 対応）

| 既存ファイル | 統合する内容 | 操作 |
|-------------|-------------|------|
| `coding-style.md` | + リファクタリング方針（16行）+ FK制約パターン（~15行） | 末尾に追加 |
| `git-workflow.md` | + バージョニング（14行）+ Gitトラブルシューティング（26行）+ GHA教訓（~20行）+ hotfix Q7（~10行） | 末尾に追加 |
| `testing.md` | → `testing-strategy.md` にリネーム。既存30行 + TDD全内容316行を統合・整理 | リネーム+マージ |
| `security.md` | 変更なし | - |
| `skill-subagent-usage.md` | 変更なし（tool-usage.mdがMCP/Fastlane/Maestro担当） | - |

---

## テストマトリックス

| # | To-Be | 検証方法 | カバー |
|---|-------|---------|--------|
| 1 | CLAUDE.mdが400行以下 | `wc -l` | ✅ |
| 2 | 全移動先ファイルが存在 | `ls .claude/rules/ && ls .cursor/plans/reference/` | ✅ |
| 3 | 情報の欠落がない | 移動前後のセクション照合 | ✅ |
| 4 | ワークツリー矛盾が解消 | CLAUDE.md + worktree.md 確認 | ✅ |
| 5 | 重複ナンバリング解消 | CLAUDE.md確認 | ✅ |
| 6 | パフォーマンス警告が消える | Claude Code起動時 | ✅ |
| 7 | Railway環境変数テーブルが保持されている | CLAUDE.mdのブランチセクション確認 | ✅ |
| 8 | Fastlane非インタラクティブenv varsが保持されている | tool-usage.md確認 | ✅ |
| 9 | ペルソナ外部ファイル存在確認 | `ls .claude/skills/agent-memory/memories/core/anicca-persona-absolute.md` | ✅ |
| 10 | Q6(Feature Flag) + Q7(hotfix)がdev-workflow.mdに移動済み | ファイル確認 | ✅ |

---

## 境界（やらないこと）

| やらないこと | 理由 |
|-------------|------|
| ルールの内容を変更する | 今回はコンパクト化のみ。ルール改善は別タスク |
| 新しいルールを追加する | スコープ外 |
| Serenaメモリの整理 | 別タスク |

---

## 実行手順

### Phase 1: 準備・検証

1. ペルソナ外部ファイルの存在確認（`.claude/skills/agent-memory/memories/core/anicca-persona-absolute.md`）
2. `.cursor/plans/reference/` ディレクトリ作成

### Phase 2: 既存ファイル拡張（`.claude/rules/`）

1. `coding-style.md` に追記: リファクタリング方針 + FK制約パターン
2. `git-workflow.md` に追記: バージョニング + Gitトラブルシューティング + GHA教訓 + hotfix Q7
3. `testing.md` → `testing-strategy.md` にリネーム + TDD全内容統合

### Phase 3: 新規ファイル作成

**`.claude/rules/`（自動読み込み）:**
1. `dev-workflow.md` — 3ゲート + Feature Flag + hotfix
2. `worktree.md` — 並列開発ルール（矛盾解消版）
3. `deployment.md` — 実機デプロイ + Netlify + App Storeリンク
4. `spec-writing.md` — Spec書き方ガイド
5. `tool-usage.md` — MCP優先 + Fastlane + Maestro

**`.cursor/plans/reference/`（非自動読み込み）:**
6. `secrets.md` — API Key管理
7. `infrastructure.md` — Cron + Railway運用
8. `daily-metrics.md` — Daily Metrics Report

### Phase 4: CLAUDE.md書き換え

1. 新しい~400行バージョンに書き換え
2. 移動セクションは参照リンクに置換
3. KEEP項目をトリム（冗長な例・コードブロック削減）
4. 参照先インデックスセクションを追加

### Phase 5: 検証

1. `wc -l CLAUDE.md` → 400行以下
2. 全ファイルの存在確認
3. 情報欠落チェック
4. ワークツリー矛盾の解消確認

### Phase 6: ロールバック計画

- 検証失敗した場合: `git revert` で即時復元
- 2セッション以上でエージェント動作を確認してから完了とする
- 問題があれば `git revert` で旧CLAUDE.mdに戻す
