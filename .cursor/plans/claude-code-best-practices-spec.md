# Claude Code ベストプラクティス導入スペック

**ソース:** `shanraisshan/claude-code-best-practice`（Star 1.9k）
**クローン先:** `/private/tmp/claude-code-best-practice/`
**日付:** 2026-02-09

---

## 0. スペック記述ルール

**このスペックおよび今後の全スペックに適用:**

| ルール | 詳細 |
|--------|------|
| 「任意」「optional」禁止 | 全項目 MUST。やるかやらないかの二択 |
| 「中期」「long-term」禁止 | 今やる。「後で」は永遠に来ない |
| 「検討」「考慮」禁止 | 決めて書く。曖昧な表現は不可 |
| 「推奨」「recommended」禁止 | MUSTかDO NOTの二択 |

---

## 1. CLAUDE.md ダイエット（298行 → 150行以下）

### Why
shanraisshan の知見: 150行超えると遵守率が落ちる。現在298行。半分以上を外部ファイルに移動する。

### 移動対象

| セクション | 現在の行数 | 移動先 | 理由 |
|-----------|-----------|--------|------|
| Serena メモリ一覧テーブル | 42-53行目 | `.claude/rules/serena-usage.md`（新規） | 毎セッション暗記不要。rules/で自動読み込み |
| Railway サービス名・環境変数・URL | 109-135行目 | `.cursor/plans/reference/infrastructure.md`（既存に統合） | デプロイ時のみ参照 |
| 後方互換ルール | 137-148行目 | `.claude/rules/api-compatibility.md`（新規） | API作業時のみ関連 |
| オンボーディング4ステップ詳細 | 221-228行目 | Serenaメモリ `ios_app_architecture` に既にある | CLAUDE.mdとの重複 |
| Nudgeシステムテーブル | 232-236行目 | Serenaメモリ `nudge_system` に既にある | CLAUDE.mdとの重複 |
| セッション管理セクション | 242-264行目 | `.claude/rules/session-management.md`（新規） | rules/で自動読み込み |
| 参照先インデックス | 268-281行目 | `.claude/rules/reference-index.md`（新規） | rules/で自動読み込み |
| MCP & OpenClaw セクション | 285-294行目 | `.claude/rules/mcp-openclaw.md`（既存に統合） | 既にrules/にある。IDだけ重複 |

### 残すもの（150行以内に収める）

| セクション | 理由 |
|-----------|------|
| 絶対ルール（0〜0.6） | 毎ターン遵守すべき核心ルール |
| 言語ルール | 毎ターン必要 |
| ブランチ構成（3行テーブルのみ） | 毎セッション確認 |
| Fastlane・Maestro（1行ずつ参照先のみ） | 毎セッション必要な禁止事項 |
| プロジェクト概要（技術スタック + 主要ディレクトリ） | 毎セッション文脈把握に必要 |
| コンテキスト管理ルール（新規追加） | 後述 Step 2 |

---

## 2. コンテキスト管理ルール追加

### Why
shanraisshan の実践知見。コンテキスト溢れがClaude Code最大の品質低下要因。

### 追加する3ルール（CLAUDE.md に直接追記、計5行）

| ルール | 内容 | 追加先 |
|--------|------|--------|
| 手動 /compact | **コンテキスト50%到達で `/compact` を手動実行する。** 自動compactまで待たない | CLAUDE.md 絶対ルール |
| サブタスク上限 | **サブタスクは50%コンテキスト以内で完了するサイズに分割する。** | CLAUDE.md 絶対ルール |
| 小タスク = vanilla CC | **5行以下の変更・単純バグ修正にはスキル/サブエージェント不要。** 直接実行する | `.claude/rules/skill-subagent-usage.md` に追記 |

---

## 3. settings.json 最適化

### 3a. settings.local.json のクリーンアップ

**現状:** 300行の allow リスト。ほとんどがワンオフの `Bash(git -C ...)` や `WebFetch(domain:...)` の残骸。

| やること | 詳細 |
|---------|------|
| ワンオフ allow を全削除 | 特定コミットメッセージ、特定パスの `git -C` 等 |
| 包括ルールに集約 | `Bash`, `mcp__*`, `Edit(*)`, `Write(*)`, `Read(*)` 等で既にカバーされている |
| deny はそのまま維持 | `sudo`, `~/.anicca/*` は正しい |

### 3b. settings.json（チーム共有）に追加

| 設定 | 値 | 理由 |
|------|-----|------|
| `language` | `"japanese"` | 日本語回答の安定化 |
| `defaultMode` | `"bypassPermissions"` | `/config` の don't-ask モード相当。ワンオフ allow の根本解決 |
| `alwaysThinkingEnabled` | `true`（既存確認） | グローバルで既に true |
| `plansDirectory` | `".cursor/plans"` | Plan Mode の出力先を統一 |

---

## 4. Hooks: macOS システム通知

### Why
shanraisshan は ElevenLabs TTS で音声通知を実装。ユーザーの要望: Cursor の「ポーン」のようなシンプル通知音。

### 実装方針

| 方式 | 詳細 |
|------|------|
| 音声再生 | macOS 標準 `afplay` + システムサウンド `/System/Library/Sounds/` |
| 通知音 | `Glass.aiff`（Cursor の「ポーン」に最も近い） |
| Python不要 | シンプルにシェルスクリプト1ファイルで完結 |

### 通知する Hook イベント

| イベント | 音 | 理由 |
|---------|-----|------|
| `Stop` | `Glass.aiff` | **タスク完了通知（最重要）** — ユーザーが別作業中に気づける |
| `PreCompact` | `Purr.aiff` | コンテキスト圧縮警告 |
| `Notification` | `Glass.aiff` | Claude からの通知 |
| `SubagentStop` | `Pop.aiff` | サブエージェント完了 |

### 不要なイベント（音を鳴らさない）

| イベント | 理由 |
|---------|------|
| `PreToolUse` / `PostToolUse` | 頻繁すぎてうるさい |
| `UserPromptSubmit` | ユーザー自身が送信したので自明 |
| `SessionStart` / `SessionEnd` | 不要 |

### ファイル構成

```
.claude/hooks/
├── scripts/
│   └── notify.sh          # メインスクリプト（afplay + macOS通知）
├── config/
│   └── hooks-config.json  # イベント別の有効/無効設定
└── README.md              # 使い方
```

### notify.sh の仕様

```bash
#!/bin/bash
# stdin から JSON を読み、hook_event_name に応じて音を鳴らす
# macOS の afplay を使用（バックグラウンド実行で Claude をブロックしない）
# 設定ファイルで個別に無効化可能
```

---

## 5. スペック記述ルール（CLAUDE.md + spec-writing.md に追加）

### 追加内容

CLAUDE.md に1ルール追加:

```markdown
### 0.7 スペック記述ルール（絶対ルール）

**スペック・TODO・計画書に以下の表現を使うことを禁止する:**

| 禁止表現 | 代替 |
|---------|------|
| 「任意」「optional」「nice-to-have」 | 全て MUST。やらないなら書かない |
| 「中期」「長期」「将来」「later」 | 今やる。やらないなら削除 |
| 「検討する」「考慮する」 | 決定して書く |
| 「推奨」「recommended」 | MUST か DO NOT |
| 「低」「中」「高」（優先度） | 全て同じ優先度。順序で表現する |

**理由:** 「任意」と書かれた項目は100%実行されない。全項目MUSTで書き、不要なら削除する。
```

`.claude/rules/spec-writing.md` にも同じルールを追記。

---

## 6. Command → Agent → Skills パターン導入

### Why
shanraisshan の核心パターン。Command（エントリーポイント）→ Agent（オーケストレーター、skill プリロード）→ Skills（ドメイン知識）の3層構造。

### 現状の問題
今はスキルを直接呼び出しているため、複数スキルの連携ワークフローが場当たり的。

### 導入する Command

| Command | Agent | Skills | 用途 |
|---------|-------|--------|------|
| `/deploy-check` | `deploy-checker` | `testing-strategy`, `deployment` | テスト→ビルド→確認の一連フロー |

### ファイル構成

```
.claude/
├── agents/
│   └── deploy-checker.md    # Agent定義（skills プリロード）
├── commands/
│   └── deploy-check.md      # Command定義（エントリーポイント）
```

### Agent定義の例

```yaml
---
name: deploy-checker
description: Use this agent PROACTIVELY when deploying to device or simulator
tools: Bash, Read, Glob
model: haiku
skills:
  - testing-strategy
  - deployment
---
```

---

## 7. settings.local.json の defaultMode 変更

### 現状
300行の allow リストが肥大化。毎回「許可しますか？」→ 許可 → allow に追加 の繰り返し。

### 変更

| 設定 | Before | After |
|------|--------|-------|
| `defaultMode` | なし（default） | `"bypassPermissions"` |
| allow リスト | 300行 | **最小限に削減**（deny で制御） |
| deny リスト | 4行 | そのまま維持 + 必要に応じて追加 |

### deny に追加するもの

| パターン | 理由 |
|---------|------|
| `Bash(sudo:*)` | 既存。維持 |
| `Edit(~/.anicca/*)` | 既存。維持 |
| `Write(~/.anicca/*)` | 既存。維持 |

---

## テスト方法

| # | テスト | 確認方法 |
|---|--------|---------|
| 1 | CLAUDE.md が150行以下 | `wc -l CLAUDE.md` |
| 2 | 移動したルールが rules/ で読み込まれる | 新セッションで確認 |
| 3 | 通知音が Stop で鳴る | Claude にタスク実行させて待つ |
| 4 | 通知音が PreCompact で鳴る | `/compact` 実行 |
| 5 | settings.local.json がクリーン | 50行以下 |
| 6 | 日本語で回答される | `language: "japanese"` 設定後に確認 |

---

## 参照ファイル

| ファイル | 場所 |
|---------|------|
| shanraisshan リポジトリ（クローン済み） | `/private/tmp/claude-code-best-practice/` |
| hooks.py（参考実装） | `/private/tmp/claude-code-best-practice/.claude/hooks/scripts/hooks.py` |
| settings レポート | `/private/tmp/claude-code-best-practice/reports/claude-settings.md` |
| CLAUDE.md for monorepos レポート | `/private/tmp/claude-code-best-practice/reports/claude-md-for-larger-mono-repos.md` |
| Command → Agent → Skills 実例 | `/private/tmp/claude-code-best-practice/.claude/agents/weather.md` |
