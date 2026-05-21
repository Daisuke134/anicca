# Verification Hooks & Best Practices 実装仕様書

## 概要

### 何を解決するか（What）
Claude Code が自己検証できる仕組みがない。編集後にテストを忘れる、コミット前にチェックを忘れる、UI 変更の視覚的検証がない。

### なぜ必要か（Why）
Claude Code Best Practices の最重要ポイント:
> "Include tests, screenshots, or expected outputs so Claude can check itself. This is the single highest-leverage thing you can do."

現状、検証は手動依存。Hooks で自動化することで、例外なく検証が実行される。

---

## 受け入れ条件（テスト可能な形式）

| # | 条件 | 検証方法 |
|---|------|---------|
| AC1 | Swift ファイル編集後、swiftlint が自動実行される | Edit で `.swift` を編集 → lint 結果が表示される |
| AC2 | TypeScript ファイル編集後、eslint + tsc が自動実行される | Edit で `.ts` を編集 → lint 結果が表示される |
| AC3 | `git commit` 前に、変更パスに応じたテストが実行される | iOS 変更 → iOS テストのみ、API 変更 → API テストのみ |
| AC4 | テスト失敗時、コミットがブロックされる | テスト失敗 → commit 不可 |
| AC5 | View ファイル変更時、Maestro 検証の推奨メッセージが表示される | `*View.swift` 編集 → メッセージ表示 |
| AC6 | `/ui-verify` でスクリーンショット比較ワークフローが実行できる | スキル呼び出し → Before/After 比較 |

---

## As-Is（現状）

### ファイル構成

```
.claude/
├── hooks/
│   └── session-end-daily-log.sh  ← セッション終了時のみ
├── rules/
│   └── skill-subagent-usage.md
├── skills/
│   ├── decisive-agent/SKILL.md   ← 作成済み
│   └── ...
└── (settings.json なし)
```

### 問題点

1. **検証の自動化なし** - 編集後に lint/test を忘れる
2. **コミット前チェックなし** - バグをそのままコミット
3. **UI 検証なし** - 視覚的変更の確認が手動のみ
4. **パスベース分離なし** - iOS/API を区別せず全テスト実行（遅い）

---

## To-Be（変更後の設計）

### ファイル構成

```
.claude/
├── settings.json                        ← 新規
├── hooks/
│   ├── session-end-daily-log.sh         ← 既存
│   ├── post-edit-verify.sh              ← 新規
│   └── pre-commit-check.sh              ← 新規
├── skills/
│   ├── decisive-agent/SKILL.md          ← 作成済み
│   └── ui-verify/SKILL.md               ← 新規
└── rules/
    └── skill-subagent-usage.md          ← 更新済み
```

### 1. `.claude/settings.json`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "command": ".claude/hooks/post-edit-verify.sh"
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash(git commit:*)",
        "command": ".claude/hooks/pre-commit-check.sh"
      }
    ]
  }
}
```

### 2. `.claude/hooks/post-edit-verify.sh`

**入力**: stdin から JSON（tool_name, file_path）

**処理フロー**:
```
ファイル拡張子を判定
  ├─ .swift → swiftlint lint --path $FILE
  ├─ .ts/.tsx → eslint $FILE && tsc --noEmit
  └─ *View.swift → 追加メッセージ「Maestro 検証推奨: /ui-verify」

結果を stdout に出力（警告のみ、exit 0）
```

**出力例**:
```
⚠️ Lint warnings in NudgeCardView.swift:
  Line 42: Trailing whitespace

💡 UI file detected. Consider running /ui-verify for visual validation.
```

### 3. `.claude/hooks/pre-commit-check.sh`

**入力**: stdin から JSON（tool_input containing commit command）

**処理フロー**:
```
git diff --cached --name-only でステージングファイル取得
  │
  ├─ aniccaios/** を含む → run_ios_tests=true
  ├─ apps/api/** を含む → run_api_tests=true
  └─ 両方含む → 両方 true

テスト実行:
  iOS: cd aniccaios && fastlane test
  API: cd apps/api && npm test

結果:
  全て PASS → exit 0（コミット許可）
  いずれか FAIL → exit 1（コミットブロック）
```

**出力例（成功）**:
```
✅ Pre-commit checks passed

📱 iOS Tests: 42 passed, 0 failed
🌐 API Tests: skipped (no changes)

Proceeding with commit...
```

**出力例（失敗）**:
```
❌ Pre-commit checks failed

📱 iOS Tests: 41 passed, 1 failed
  FAILED: testNudgeSelection_requiresAtLeastOneProblem

Fix the failing tests before committing.
```

### 4. `.claude/skills/ui-verify/SKILL.md`

```markdown
---
name: ui-verify
description: UI変更後にMaestro MCPでスクリーンショット検証を実行
---

# UI Verification Workflow

## When to Use
- SwiftUI View ファイルを編集した後
- レイアウト変更後の視覚的確認
- post-edit-verify.sh が「Maestro 検証推奨」と表示した時

## Workflow

### Step 1: デバイス確認
mcp__maestro__list_devices でシミュレータ確認

### Step 2: アプリ起動
mcp__maestro__launch_app で対象アプリを起動

### Step 3: Before スクリーンショット
mcp__maestro__take_screenshot で変更前の状態を保存

### Step 4: 編集を適用
（この時点で既に編集済みの場合はビルド＆再起動）

### Step 5: After スクリーンショット
mcp__maestro__take_screenshot で変更後の状態を保存

### Step 6: 差分レポート
Before/After を比較し、以下を報告:
- 変更された UI 要素
- 意図しない変更がないか
- レイアウト崩れがないか

## Output Format

| 項目 | Before | After | Status |
|------|--------|-------|--------|
| ボタン位置 | (100, 200) | (100, 200) | ✅ 変化なし |
| テキスト色 | #333333 | #000000 | ⚠️ 変更あり |
| フォントサイズ | 16pt | 18pt | ⚠️ 変更あり（意図的？） |
```

---

## To-Be チェックリスト

| # | To-Be 項目 | 完了 |
|---|-----------|------|
| 1 | `.claude/settings.json` 作成 | ⬜ |
| 2 | `post-edit-verify.sh` 作成 | ⬜ |
| 3 | Swift lint 実行ロジック | ⬜ |
| 4 | TypeScript lint 実行ロジック | ⬜ |
| 5 | View ファイル検出 & メッセージ | ⬜ |
| 6 | `pre-commit-check.sh` 作成 | ⬜ |
| 7 | パスベーステスト分岐 | ⬜ |
| 8 | iOS テスト実行 | ⬜ |
| 9 | API テスト実行 | ⬜ |
| 10 | テスト失敗時ブロック | ⬜ |
| 11 | `ui-verify/SKILL.md` 作成 | ⬜ |
| 12 | Maestro MCP ワークフロー定義 | ⬜ |
| 13 | `CLAUDE.md` プルーニング | ⬜ |
| 14 | 動作確認テスト | ⬜ |

---

## テストマトリックス

| # | To-Be | テスト名 | カバー |
|---|-------|----------|--------|
| 1 | Swift lint 実行 | `test_post_edit_swift_runs_swiftlint` | ⬜ |
| 2 | TS lint 実行 | `test_post_edit_ts_runs_eslint` | ⬜ |
| 3 | View 検出 | `test_post_edit_view_shows_maestro_hint` | ⬜ |
| 4 | iOS パス検出 | `test_precommit_detects_ios_changes` | ⬜ |
| 5 | API パス検出 | `test_precommit_detects_api_changes` | ⬜ |
| 6 | 両方検出 | `test_precommit_detects_both_changes` | ⬜ |
| 7 | テスト失敗ブロック | `test_precommit_blocks_on_failure` | ⬜ |
| 8 | テスト成功許可 | `test_precommit_allows_on_success` | ⬜ |

**検証方法**: 手動テスト（Hooks のユニットテストは複雑なため、実際の動作で確認）

---

## E2E シナリオ

| # | シナリオ | 検証項目 |
|---|---------|---------|
| E2E-1 | Swift ファイル編集フロー | Edit → lint 警告表示 → 修正 → 警告消える |
| E2E-2 | View ファイル編集フロー | Edit → Maestro 推奨表示 → /ui-verify → 比較レポート |
| E2E-3 | iOS のみ変更コミット | iOS ファイル変更 → commit → iOS テストのみ実行 |
| E2E-4 | API のみ変更コミット | API ファイル変更 → commit → API テストのみ実行 |
| E2E-5 | テスト失敗コミット | テスト失敗コード → commit → ブロック → 修正 → 成功 |

---

## Skills / Sub-agents 使用マップ

| ステージ | 使用するもの | 用途 |
|---------|-------------|------|
| 実装前 | `/plan` | この仕様書の作成 |
| Hook 実装 | 直接実装 | シェルスクリプト作成 |
| 動作確認 | 手動テスト | 各シナリオを実行 |
| UI 検証 | `mcp__maestro__*` | スクリーンショット取得・比較 |
| コードレビュー | `/codex-review` | 実装完了後 |

---

## 境界（Boundaries）

### やること
- `.claude/` 配下の設定・Hook・スキル作成
- CLAUDE.md のプルーニング

### やらないこと
- iOS アプリコードの変更
- API コードの変更
- CI/CD パイプラインの変更（GitHub Actions 等）
- 既存テストの修正

### 触るファイル
- `.claude/settings.json`（新規）
- `.claude/hooks/post-edit-verify.sh`（新規）
- `.claude/hooks/pre-commit-check.sh`（新規）
- `.claude/skills/ui-verify/SKILL.md`（新規）
- `.claude/rules/skill-subagent-usage.md`（更新済み）
- `CLAUDE.md`（プルーニング）

### 触らないファイル
- `aniccaios/**`（iOS アプリ）
- `apps/api/**`（API）
- `.github/**`（CI/CD）

---

## ローカライズ

なし（開発者向けツールのため英語のみ）

---

## 実行手順

### 1. 設定ファイル作成
```bash
# settings.json 作成
touch .claude/settings.json
```

### 2. Hook スクリプト作成
```bash
# スクリプト作成
touch .claude/hooks/post-edit-verify.sh
touch .claude/hooks/pre-commit-check.sh
chmod +x .claude/hooks/*.sh
```

### 3. スキル作成
```bash
mkdir -p .claude/skills/ui-verify
touch .claude/skills/ui-verify/SKILL.md
```

### 4. 動作確認
```bash
# Swift ファイル編集テスト
# → lint 警告が表示されるか確認

# コミットテスト
git add .
git commit -m "test"
# → パスベーステストが実行されるか確認
```

---

## ユーザー作業

### 実装前
なし

### 実装中
なし

### 実装後

| # | タスク | 確認項目 |
|---|--------|---------|
| 1 | Swift ファイルを編集してみる | lint 警告が表示されるか |
| 2 | View ファイルを編集してみる | Maestro 推奨メッセージが表示されるか |
| 3 | コミットしてみる | テストが自動実行されるか |
| 4 | `/ui-verify` を実行してみる | スクリーンショット比較が動くか |

---

## レビューチェックリスト

### Spec レビュー
- [x] 全 To-Be がテストマトリックスに含まれているか
- [x] 受け入れ条件がテスト可能な形式か
- [x] 設計（シグネチャ、データモデル）が明確か
- [x] 境界（やらないこと）が定義されているか
- [x] 後方互換性は保たれるか → 新規ファイルのみなので影響なし
- [x] As-Is の問題が To-Be で解決されるか

### 実装レビュー（実装後に確認）
- [ ] settings.json の構文が正しいか
- [ ] Hook スクリプトに実行権限があるか
- [ ] パス判定ロジックが正しいか
- [ ] エラーハンドリングがあるか
- [ ] 出力メッセージが分かりやすいか

---

## 参考資料

- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices)
- [Pre-Commit or CI/CD - Medium](https://motlin.medium.com/pre-commit-or-ci-cd-5779d3a0e566)
- [Testing strategies for monorepos - Graphite](https://graphite.dev/guides/testing-strategies-for-monorepos)
- [Visual Testing Best Practices - BrowserStack](https://www.browserstack.com/guide/visual-testing-best-practices)

---

最終更新: 2026-01-26
