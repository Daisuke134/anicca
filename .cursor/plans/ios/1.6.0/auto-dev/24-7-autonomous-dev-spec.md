# Phase 1: Ralph セットアップ + CI 自動化基盤 Spec

## 開発環境

| 項目 | 値 |
|------|-----|
| **ワークツリーパス** | `/Users/cbns03/Downloads/anicca-auto-dev` |
| **ブランチ** | `feature/auto-dev-pipeline` |
| **ベースブランチ** | `dev` |
| **作業状態** | Spec レビュー反映済み |

---

## 1. 概要（What & Why）

### What

Ralph（https://github.com/frankbria/ralph-claude-code）を導入し、Claude Code CLI を自律ループ実行させる開発自動化基盤を構築する。

**スコープ**: Phase 1 は「手動トリガーの自律ループ実行基盤」。cron/daemon 化による完全 24/7 自動化は Phase 2。

### Why

| 現状の問題 | 解決策 |
|-----------|--------|
| Claude Code は1回の実行で止まる | Ralph がループで自動継続 |
| エラーで止まったら手動介入が必要 | Ralph の circuit breaker で自動停止 + Auto-Fix で自動復旧 |
| コードレビューが手動 | CodeRabbit で自動レビュー |

### アーキテクチャ（データフロー）

```
ユーザー: 「ralph」コマンドを実行（手動トリガー）
    │
    ▼
Ralph (ローカル)
    │
    ├── Claude Code CLI 呼び出し（ループ）
    │       │
    │       ├── コード生成・修正
    │       ├── テスト実行（fastlane test）
    │       └── git commit
    │
    └── タスク完了 or circuit break → git push
            │
            ▼
      GitHub（remote）
            │
            ├── ios-ci.yml: Fastlane テスト実行
            │       │
            │       ├── PASS → CodeRabbit レビュー
            │       │
            │       └── FAIL → claude-autofix.yml
            │               │
            │               └── 修正 commit → push → ios-ci.yml 再実行
            │
            └── claude.yml: @claude メンション → Claude 応答
```

**Ralph → GitHub Actions の接続**: Ralph が `git push` → GitHub Actions が自動トリガー。API 呼び出しは不要。

### Ralph の役割

| 機能 | 説明 |
|------|------|
| **自律ループ** | Claude Code を完了まで繰り返し実行 |
| **セッション継続** | 24時間コンテキストを維持 |
| **Circuit Breaker** | 3回進捗なし or 5回同じエラーで停止 |
| **レート制限** | 100 API calls/hour を超えない |
| **Dual-Condition Exit** | 完了指標 + EXIT_SIGNAL: true で終了 |

### GitHub Actions の役割（補助インフラ）

| Workflow | 役割 | 状態 |
|----------|------|------|
| `ios-ci.yml` | PR push → Fastlane テスト | ✅ 実装済み |
| `claude.yml` | `@claude` メンション → Claude 応答 | ✅ 実装済み |
| `claude-autofix.yml` | CI 失敗 → 自動修正（feature/* ブランチ限定） | ✅ 実装済み → 要修正（B2） |
| `.coderabbit.yml` | PR → 自動コードレビュー | ✅ 実装済み |

---

## 2. 受け入れ条件

| # | 条件 | テスト方法 |
|---|------|-----------|
| 1 | システム要件が全てインストール済み | `tmux -V && jq --version && timeout --version` |
| 2 | `ralph` コマンドが実行できる | `ralph --help` |
| 3 | `.ralph/` ディレクトリが正しく構成されている | ディレクトリ確認 |
| 4 | `.ralphrc` が正しい形式（パス制限あり） | Ralph が読み込めるか |
| 5 | `ralph` を実行すると Claude Code がループ実行される | `ralph --monitor --timeout 5` |
| 6 | circuit breaker が機能する（無限ループ防止） | 意図的にエラーを起こして確認 |
| 7 | CI が Fastlane 経由で動く | PR push → CI 実行 |
| 8 | CodeRabbit が dev 宛 PR をレビューする | PR 作成 → レビュー確認 |
| 9 | Auto-Fix が feature/* ブランチの CI 失敗時のみ動く | ブランチ名チェック |
| 10 | `claude-night-shift.yml` が削除されている | ファイル不在確認 |

---

## 3. As-Is / To-Be

### 3.1 システム要件（新規確認）

**To-Be**: 以下が全てインストール済み

| 依存 | 確認コマンド | macOS インストール |
|------|-------------|-------------------|
| Bash 4.0+ | `bash --version` | macOS デフォルト or `brew install bash` |
| tmux | `tmux -V` | `brew install tmux` |
| jq | `jq --version` | `brew install jq` |
| GNU coreutils | `timeout --version` | `brew install coreutils` |
| Git | `git --version` | Xcode Command Line Tools |
| Claude Code CLI | `claude --version` | `npm install -g @anthropic-ai/claude-code` |

### 3.2 Ralph（新規導入）

**As-Is**: 存在しない

**To-Be**:

```
/Users/cbns03/Downloads/anicca-auto-dev/
├── .ralph/
│   ├── PROMPT.md          # 開発指示書
│   ├── fix_plan.md        # タスクチェックリスト
│   ├── AGENT.md           # ビルド/テストコマンド
│   ├── specs/             # 技術仕様
│   └── logs/              # 実行ログ
├── .ralphrc               # Ralph 設定（パス制限あり）
└── ...
```

### 3.3 `.ralphrc`（修正）

**As-Is** (間違った形式 — Ralph の仕様と無関係):
```
MAX_ITERATIONS=20
TIMEOUT_MINUTES=60
CIRCUIT_BREAKER_MAX_REPEATED=3
COOLDOWN_SECONDS=30
LOG_LEVEL=info
```

**To-Be** (Ralph 正式形式 + セキュリティ強化):
```bash
PROJECT_NAME="anicca"
PROJECT_TYPE="swift"
MAX_CALLS_PER_HOUR=100
CLAUDE_TIMEOUT_MINUTES=15
CLAUDE_OUTPUT_FORMAT="json"
ALLOWED_TOOLS="Write,Read,Edit,Bash(git status),Bash(git add *),Bash(git commit *),Bash(git push origin *),Bash(git pull),Bash(git checkout *),Bash(git branch *),Bash(git diff *),Bash(git log *),Bash(cd *),Bash(ls *),Bash(fastlane *),Bash(xcodebuild test *),Bash(xcodebuild build *),Bash(swift *),Bash(npm test *)"
SESSION_CONTINUITY=true
SESSION_EXPIRY_HOURS=24
CB_NO_PROGRESS_THRESHOLD=3
CB_SAME_ERROR_THRESHOLD=5
```

**セキュリティ対策（B1 対応）**:
- `Bash(git *)` → 特定サブコマンドのみ許可（`git status`, `git add`, `git commit`, `git push origin`, etc.）
- `Bash(xcodebuild *)` → `test` と `build` のみ許可
- `Bash(rm *)`, `Bash(curl *)`, `Bash(wget *)` は許可しない
- `git push --force`, `git remote add` は許可しない

**注意**: Ralph は `ALLOWED_PATHS` / `DENY_PATHS` を直接サポートしていない。ALLOWED_TOOLS でコマンドレベルで制限する。

### 3.4 `.ralph/PROMPT.md`（新規）

**To-Be**:
```markdown
# Anicca 開発指示

## プロジェクト概要
iOS 行動変容アプリ。SwiftUI + Node.js API。

## 開発ルール
1. TDD: テストを先に書く
2. 破壊的変更禁止
3. Fastlane 経由でビルド/テスト（xcodebuild 直接実行禁止）
4. コミットメッセージは日本語OK
5. プロジェクトディレクトリ外のファイルに触れない

## 現在のタスク
fix_plan.md を参照

## 完了条件
- 全テスト PASS
- コードレビュー指摘対応
- EXIT_SIGNAL: true を出力
```

### 3.5 `.ralph/AGENT.md`（新規）

**To-Be**:
```markdown
# ビルド/テストコマンド

## iOS
cd aniccaios && FASTLANE_SKIP_UPDATE_CHECK=1 FASTLANE_OPT_OUT_CRASH_REPORTING=1 fastlane test

## API
cd apps/api && npm test
```

### 3.6 `claude-autofix.yml`（修正 — B2 対応）

**As-Is**: ブランチ名チェックなし（任意のブランチの CI 失敗で発火）

**To-Be**: `feature/*` ブランチのみに制限
```yaml
jobs:
  autofix:
    if: |
      github.event.workflow_run.conclusion == 'failure' &&
      github.event.workflow_run.head_branch != 'main' &&
      github.event.workflow_run.head_branch != 'dev' &&
      startsWith(github.event.workflow_run.head_branch, 'feature/')
```

### 3.7 `claude-night-shift.yml`（削除 — B4 対応）

**As-Is**: 存在する

**To-Be**: **削除**

**理由**: Ralph があれば不要。プロンプトインジェクションのリスクがメリットを上回る（Security Auditor 指摘 B4）。

---

## 4. テストマトリックス

| # | To-Be | テスト名 | カバー |
|---|-------|----------|--------|
| 1 | システム要件インストール | `test_system_requirements` | ❌ |
| 2 | Ralph インストール | `test_ralph_installed` | ❌ |
| 3 | .ralph/ ディレクトリ構成 | `test_ralph_directory_structure` | ❌ |
| 4 | .ralphrc 読み込み（セキュリティ制限付き） | `test_ralphrc_valid_secure` | ❌ |
| 5 | Ralph ループ実行 | `test_ralph_loop_execution` | ❌ |
| 6 | Circuit Breaker | `test_circuit_breaker` | ❌ |
| 7 | iOS CI (Fastlane) | `test_ios_ci_fastlane` | ✅ |
| 8 | CodeRabbit dev レビュー | `test_coderabbit_dev_branch` | ✅ |
| 9 | Auto-Fix feature/* 限定 | `test_autofix_feature_branch_only` | ❌ |
| 10 | Night Shift 削除確認 | `test_nightshift_deleted` | ❌ |

---

## 5. 境界

### やること

- システム要件のインストール（tmux, jq, GNU coreutils）
- Ralph のインストール（コミットハッシュ固定 — B3 対応）
- Ralph のプロジェクトセットアップ（`ralph-enable`）
- `.ralphrc` を正しい形式 + セキュリティ制限付きに修正
- `.ralph/` ディレクトリの作成と設定
- `claude-autofix.yml` を feature/* 限定に修正
- `claude-night-shift.yml` の削除
- 動作確認テスト

### やらないこと

- cron / launchd での自動実行（Phase 2）
- Slack/Discord 通知連携（Phase 2）
- 複数プロジェクト対応（スコープ外）
- iOS ソースコード変更
- API ソースコード変更

### 触るファイル

| ファイル | 操作 |
|---------|------|
| `.ralphrc` | 修正 |
| `.ralph/PROMPT.md` | 新規 |
| `.ralph/AGENT.md` | 新規 |
| `.ralph/fix_plan.md` | 新規 |
| `.github/workflows/claude-autofix.yml` | 修正（feature/* 制限追加） |
| `.github/workflows/claude-night-shift.yml` | **削除** |

### 触らないファイル

- iOS ソースコード
- API ソースコード
- `.github/workflows/ios-ci.yml`（実装済み）
- `.github/workflows/claude.yml`（実装済み）
- `.coderabbit.yml`（実装済み）

---

## 6. 実行手順

### Phase 0: システム要件確認

```bash
# macOS
brew install tmux jq coreutils

# Claude Code CLI（未インストールの場合）
npm install -g @anthropic-ai/claude-code

# 確認
tmux -V
jq --version
timeout --version
claude --version
```

### Phase 1: Ralph インストール（グローバル）

```bash
# 1. Ralph をクローン（最新の安定コミットを固定）
git clone --depth 1 https://github.com/frankbria/ralph-claude-code.git ~/ralph-claude-code

# 2. install.sh の内容を確認してからインストール
cat ~/ralph-claude-code/install.sh
cd ~/ralph-claude-code && ./install.sh

# 3. 確認
ralph --help
```

### Phase 2: プロジェクトセットアップ

```bash
# ワークツリーに移動
cd /Users/cbns03/Downloads/anicca-auto-dev

# Ralph セットアップ（既存プロジェクト用）
ralph-enable
```

### Phase 3: 設定ファイル作成・修正

1. `.ralphrc` を正しい形式 + セキュリティ制限付きに修正
2. `.ralph/PROMPT.md` を作成
3. `.ralph/AGENT.md` を作成
4. `.ralph/fix_plan.md` を作成（初期タスク）
5. セッションをリセット: `ralph --reset-session`

### Phase 4: GitHub Actions 修正

1. `claude-autofix.yml` に `startsWith(github.event.workflow_run.head_branch, 'feature/')` を追加
2. `claude-night-shift.yml` を削除

### Phase 5: 動作確認

```bash
# Ralph を実行（統合モニタリング付き、5分タイムアウト）
ralph --monitor --timeout 5

# ログ確認
cat .ralph/logs/latest.log
```

### Phase 6: コミット & プッシュ

```bash
git add -A
git commit -m "feat: Ralph セットアップ + セキュリティ修正"
git push origin feature/auto-dev-pipeline
```

---

## 7. コスト見積もり

| 項目 | 見積もり | 根拠 |
|------|---------|------|
| Claude API（Sonnet） | ~$0.03-0.15/call（~10k tokens） | $3/1M input + $15/1M output |
| Claude API（Opus） | ~$0.15-0.75/call（~10k tokens） | $15/1M input + $75/1M output |
| Ralph 100 calls/hour（Sonnet） | $3-15/hour | |
| 月間（4時間/日 × 20日、Sonnet） | **$240-1,200/month** | |
| GitHub Actions | 無料枠内 | 2,000 min/month |
| CodeRabbit | 無料（OSS） | |

**注意**: コストはトークン数に大きく依存する。実際の使用量を1週間モニタリングしてから本格運用する。

---

## 8. リスクと対策

| # | リスク | 深刻度 | 対策 |
|---|--------|--------|------|
| 1 | **プロジェクト外ファイルアクセス** | CRITICAL | ALLOWED_TOOLS で git/xcodebuild サブコマンドを制限（B1） |
| 2 | **任意ブランチで Auto-Fix 発火** | HIGH | `feature/*` ブランチのみに制限（B2） |
| 3 | **Ralph install.sh のサプライチェーン攻撃** | HIGH | `--depth 1` + install.sh の内容を事前確認（B3） |
| 4 | **Night Shift プロンプトインジェクション** | HIGH | Night Shift を削除（B4） |
| 5 | **API コスト超過** | MEDIUM | MAX_CALLS_PER_HOUR=100 で制限 |
| 6 | **無限ループ** | MEDIUM | Circuit Breaker (3回進捗なし/5回同エラー) |
| 7 | **壊れたコード生成** | MEDIUM | TDD 強制 + テスト PASS 必須 |
| 8 | **24/7 運用の前提** | INFO | Phase 1 は手動トリガー。常時起動マシンは Phase 2 で検討 |

---

## 9. ユーザー GUI 作業

| # | タスク | 状態 |
|---|--------|------|
| 1 | Supabase/Vercel/Netlify を anicca.ai リポジトリから外す | ✅ 完了 |

※ 他の GUI 作業は不要。全て CLI で完結。

---

## 10. レビュー履歴

### 第1回レビュー（3サブエージェント並列）

| レビュアー | Blocking | Advisory | 反映状態 |
|-----------|----------|----------|---------|
| Architecture | B1: タイトルと実装の乖離, B2: Auto-Fix フィードバック未定義 | A1-A5 | ✅ 反映済み |
| Tech Verification | B1: `ralph --version` 不在, B2: システム要件欠落 | A1-A5 | ✅ 反映済み |
| Security Audit | B1: ALLOWED_TOOLS 無制限, B2: autofix author未検証, B3: サプライチェーン, B4: Night Shift 削除推奨 | A1-A7 | ✅ 反映済み |

### Blocking Issue 対応詳細

| ID | 問題 | 対応 |
|----|------|------|
| Arch-B1 | タイトルが「24/7」だが手動トリガー | タイトルを「Phase 1: Ralph セットアップ + CI 自動化基盤」に変更 |
| Arch-B2 | Auto-Fix → Ralph フィードバック未定義 | Ralph は `git pull` でリモートの変更を取り込む。PROMPT.md に「`git pull` してから作業開始」を明記 |
| Tech-B1 | `ralph --version` が存在しない | `ralph --help` に変更 |
| Tech-B2 | システム要件の欠落 | Phase 0 セクション追加（tmux, jq, GNU coreutils） |
| Sec-B1 | ALLOWED_TOOLS がプロジェクト外アクセス可能 | git/xcodebuild サブコマンドを個別に制限 |
| Sec-B2 | autofix.yml に author 検証がない | `feature/*` ブランチ限定に変更 |
| Sec-B3 | Ralph install.sh の整合性チェックなし | `--depth 1` + 事前確認手順追加 |
| Sec-B4 | Night Shift のプロンプトインジェクションリスク | `claude-night-shift.yml` を削除 |
