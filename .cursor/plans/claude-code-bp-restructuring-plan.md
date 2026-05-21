# Claude Code ベストプラクティス再構築計画（2026-03-05、v3）

**ステータス: 計画完了 → 実装待ち**
**v3 更新: 公式ドキュメント7ページ深掘りで19個の新ギャップを発見・修正。Phase 12-15 新設。Phase 3 全面修正。**
**v2 更新: 14個のギャップを修正。BP repo 全11ファイルの全詳細を反映。**

## ソース

| # | ソース | URL |
|---|--------|-----|
| 1 | shanraisshan/claude-code-best-practice | https://github.com/shanraisshan/claude-code-best-practice |
| 2 | Zenn akasara — CC×OpenClaw責務分離 | https://zenn.dev/akasara/articles/b80fe3c8cc8569 |
| 3 | AnswerOverflow — CC+OpenClaw統合 | https://www.answeroverflow.com/m/1473453929403650209 |
| 4 | Anthropic公式 BP | https://code.claude.com/docs/en/best-practices |
| 5 | claude-settings.md（38設定 + 84環境変数） | BP repo best-practice/claude-settings.md |
| 6 | claude-cli-startup-flags.md（CLI flags全量） | BP repo best-practice/claude-cli-startup-flags.md |
| 7 | claude-skills.md（Skill frontmatter全量） | BP repo best-practice/claude-skills.md |
| 8 | claude-subagents.md（Agent frontmatter全量） | BP repo best-practice/claude-subagents.md |
| 9 | claude-commands.md（Command frontmatter全量） | BP repo best-practice/claude-commands.md |
| 10 | claude-mcp.md（推奨MCP 5つ） | BP repo best-practice/claude-mcp.md |
| 11 | claude-memory.md（Ancestor/Descendant Loading） | BP repo best-practice/claude-memory.md |
| 12 | reports/global-vs-project-settings.md | BP repo reports/ |
| 13 | reports/skills-for-larger-mono-repos.md | BP repo reports/ |
| 14 | tips/boris-tips-feb-26.md（12カスタマイズ） | BP repo tips/ |
| 15 | **【v3追加】** Anthropic公式 Skills docs | https://code.claude.com/docs/en/skills |
| 16 | **【v3追加】** Anthropic公式 Hooks Guide | https://code.claude.com/docs/en/hooks-guide |
| 17 | **【v3追加】** Anthropic公式 Sub-agents docs | https://code.claude.com/docs/en/sub-agents |
| 18 | **【v3追加】** Anthropic公式 Memory docs | https://code.claude.com/docs/en/memory |
| 19 | **【v3追加】** Anthropic公式 Plugins docs | https://code.claude.com/docs/en/plugins |
| 20 | **【v3追加】** Anthropic公式 Settings Reference | https://code.claude.com/docs/en/settings |

---

## Phase 1: CLAUDE.md スリム化（目標: 150行以下）

### TODO 1.1: `.claude/CLAUDE.md` を削除
- **ファイル**: `.claude/CLAUDE.md`
- **アクション**: git rm
- **理由**: ルートの CLAUDE.md と完全重複（277行×2=554行ロード）
- **ステータス**: pending

### TODO 1.2: `CLAUDE.md` を150行以下にリライト
- **対象ファイル**: `/Users/anicca/anicca-project/CLAUDE.md`
- **残すセクション**:
  - 根本原則（5行に圧縮: BP=答え、検索必須、引用必須）
  - 絶対ルール（10行: push即実行、テーブル出力、日本語、テスト範囲、コンテキスト管理）
  - 実行環境（3行: Mac Mini）
  - ブランチ & デプロイ（5行テーブル）
  - プロジェクト概要（8行テーブル）
  - ビルド・テスト・デプロイコマンド（10行）
  - コード構造（5行）
  - 参照先ポインタ（10行: rules/, skills/, agent_docs/）
  - Active Technologies（2行）
  - **【v2追加】デバッグヒント**（5行: BP repo CLAUDE.md に準拠）
  - **【v2追加】ワークフローBP**（3行: /compact at 50%, feature-specific agents, commands for workflows）

- **移すセクション**:
  - 0.0 Investigate Before Acting → rules/investigate-before-acting.md に統合
  - 0.1 オリジナリティ禁止 → rules/ に統合
  - 0.2 教訓の一般化 → rules/ に統合
  - 0.3 Serena メモリ → CLAUDE.md に2行で参照のみ
  - 0.7 スペック記述 → skills/spec-writing/
  - 0.10 スペックギャップ禁止 → skills/spec-writing/
  - 0.11 Chat内ビジュアル化 → 1行で残す
  - OpenClaw TUI トラブル → AGENTS.md
  - Investigate Before Acting（重複分）→ 削除

### TODO 1.3:【v2追加】CLAUDE.local.md 作成
- **ファイル**: `/Users/anicca/anicca-project/CLAUDE.local.md`
- **内容**: 個人好み（出力スタイル、特定ワークフロー等）
- **git**: .gitignore に追加
- **ソース**: claude-memory.md — 「CLAUDE.local.md for personal preferences」
- **ステータス**: pending

### TODO 1.4:【v3追加】`@import` 構文でCLAUDE.mdを分割

**ソース**: [Anthropic Memory docs](https://code.claude.com/docs/en/memory) — 「Use @path/to/file syntax in CLAUDE.md to import additional instruction files」

- **アクション**: CLAUDE.md 150行以下を維持しつつ、詳細ルールを `@` でインポート
- **パターン**:
```markdown
# CLAUDE.md（150行以下）
## 根本原則
@.claude/rules/core-principles.md
## ビルド & テスト
@agent_docs/building_and_testing.md
## 参照先
@.claude/rules/reference-index.md
```
- **メリット**: CLAUDE.md は目次的に軽量、詳細は別ファイルでオンデマンドロード
- **ステータス**: pending

### TODO 1.5:【v3追加】Path-specific rules 設計（`paths` frontmatter）

**ソース**: [Anthropic Memory docs](https://code.claude.com/docs/en/memory) — 「Rules can use paths frontmatter to only load when working on matching files」

- **アクション**: rules/*.md に `paths` frontmatter を追加し、無関係なルールのロードを防止
- **設計**:

| ルールファイル | paths フィルター | 効果 |
|--------------|----------------|------|
| api-compatibility.md | `paths: ["apps/api/**"]` | API作業時のみロード |
| worktree.md | なし（常時ロード） | 全作業に適用 |
| git-workflow.md | なし（常時ロード） | 全作業に適用 |
| security.md | なし（常時ロード） | 全作業に適用 |
| dev-workflow.md | なし（常時ロード） | 全作業に適用 |

- **ステータス**: pending

---

## Phase 2: rules/ スリム化

### TODO 2.1: 残すファイル（5つ、~250行）

| ファイル | 現行行数 | 目標行数 | アクション | ステータス |
|---------|---------|---------|-----------|----------|
| api-compatibility.md | 11 | 11 | 変更なし | pending |
| git-workflow.md | 125 | 50 | 圧縮（commit format, PR flow, semverのみ残す） | pending |
| dev-workflow.md | 78 | 40 | 圧縮（3ゲートフロー図のみ残す） | pending |
| security.md | 36 | 36 | 変更なし | pending |
| worktree.md | 141 | 60 | 圧縮（基本フローとルールのみ残す） | pending |

### TODO 2.2: skills/ に移行するファイル（7つ）

| 元ファイル | 新スキルパス | SKILL.md frontmatter | ステータス |
|-----------|-------------|---------------------|-----------|
| testing-strategy.md (330行) | .claude/skills/testing-strategy/SKILL.md | name: testing-strategy, description: "Comprehensive testing strategy and TDD workflow. Use when writing tests, setting up test infrastructure, or reviewing test coverage." | pending |
| tool-usage.md (218行) | .claude/skills/tool-usage/SKILL.md | name: tool-usage, description: "Tool, MCP, and Fastlane usage rules. Use when selecting tools, configuring MCPs, or running builds." | pending |
| deployment.md (227行) | .claude/skills/deployment/SKILL.md | name: deployment, description: "Device deployment, App Store submission, and release procedures. Use when deploying to device, simulator, App Store, or Netlify.", disable-model-invocation: true | pending |
| spec-writing.md (132行) | .claude/skills/spec-writing/SKILL.md | name: spec-writing, description: "Spec file writing rules and templates. Use when creating or updating specification documents." | pending |
| skill-subagent-usage.md (189行) | .claude/skills/subagent-guide/SKILL.md | name: subagent-guide, description: "Skill and subagent delegation rules. Use when deciding whether to delegate to subagents or skills." | pending |
| skill-authoring.md (77行) | .claude/skills/skill-authoring-guide/SKILL.md | name: skill-authoring-guide, description: "Skill creation and management rules. Use when creating or updating Claude Code skills." | pending |
| persona.md (46行) | .claude/skills/persona/SKILL.md | name: persona, description: "Anicca target persona details. Use when creating marketing copy, UX content, or user-facing text." | pending |

### TODO 2.3: 削除するファイル

| ファイル | 理由 | ステータス |
|---------|------|-----------|
| coding-style.md | agent_docs/code_conventions.md に移行 + SwiftLint/ESLint に委譲 | pending |
| testing.md | testing-strategy に統合済み | pending |
| session-management.md | CLAUDE.md に3行で統合 | pending |
| reference-index.md | CLAUDE.md の参照先セクションに統合 | pending |
| serena-usage.md | CLAUDE.md に2行で統合 | pending |
| mcp-openclaw.md | AGENTS.md に移動 | pending |
| openclaw-vps-absolute.md | AGENTS.md に移動 | pending |

---

## Phase 3: OpenClaw 責務分離【v3修正: Aniccaの実在地を反映】

**発見（2026-03-05）: Aniccaは `anicca-project/` に住んでいない。**

```
Aniccaの家: /Users/anicca/.openclaw/
├── workspace/
│   ├── IDENTITY.md   ← 既に存在（「俺は誰か」）
│   ├── SOUL.md       ← 既に存在（行動規範）
│   ├── AGENTS.md     ← 既に存在（iOS開発ガイド）
│   ├── MEMORY.md     ← 既に存在
│   ├── TOOLS.md      ← 既に存在
│   ├── BOOTSTRAP.md  ← 既に存在
│   ├── HEARTBEAT.md  ← 既に存在
│   ├── USER.md       ← 既に存在（ダイスの情報）
│   └── skills/       ← 30個のOpenClawスキル
└── .git → Daisuke134/anicca (PRIVATE)

Claude Codeの作業場: /Users/anicca/anicca-project/
├── .claude/skills/   ← 176個のCC専用スキル
├── aniccaios/        ← iOSアプリ
├── apps/api/         ← APIサーバー
└── .git → Daisuke134/anicca-products (PUBLIC)
```

**結論**: `anicca-project/` に IDENTITY.md/SOUL.md/AGENTS.md を新規作成するのは間違い。
Aniccaの設定は `.openclaw/workspace/` の既存ファイルを更新する。
`anicca-project/` にはCC（Claude Code）用の設定だけ置く。

### TODO 3.1: `.openclaw/workspace/AGENTS.md` 更新（既存ファイル）

- **ファイル**: `/Users/anicca/.openclaw/workspace/AGENTS.md`
- **現状**: iOS開発ガイドが書かれている（古い内容含む、VPS言及あり）
- **アクション**: Mac Mini時代に合わせて更新 + CC連携プロトコル追加
- **追加内容**:
  - MCP & ツール（Mixpanel projID: 3970220, RevenueCat projID: projbb7b9d1b）
  - Mac Mini 絶対ルール（SSH禁止、bind: loopback）
  - OpenClaw TUI トラブルシューティング（gateway, port 18789）
  - Cron 運用（jobs.json, restart必須）
- **CC側の対応**: `anicca-project/` の `mcp-openclaw.md`, `openclaw-vps-absolute.md` は削除（Phase 2.3 で実施）
- **ステータス**: pending

### TODO 3.2: `.openclaw/workspace/SOUL.md` 更新（既存ファイル）

- **ファイル**: `/Users/anicca/.openclaw/workspace/SOUL.md`
- **アクション**: 以下の原則を統合
  - Investigate Before Acting プロトコル
  - オリジナリティ禁止ルール
  - 教訓の一般化ルール
  - 高リスク操作ゲート（破壊的git操作禁止）
  - Secret管理ルール
- **ステータス**: pending

### TODO 3.3: `.openclaw/workspace/IDENTITY.md` 更新（既存ファイル）

- **ファイル**: `/Users/anicca/.openclaw/workspace/IDENTITY.md`
- **現状**: 古い内容（VPS言及、古いリポURL `anicca.ai`）
- **アクション**: 最新状態に更新
  - Mac Mini 稼働中（VPS削除）
  - リポURL: `Daisuke134/anicca` (PRIVATE)
  - 55+ OpenClawスキル、60+ Cronジョブ
  - ペルソナ参照（persona skill へのポインタ）
- **ステータス**: pending

### TODO 3.4: `anicca-project/` にはCC用ルールのみ残す

- **原則**: `anicca-project/` に OpenClaw 設定を置かない
- **削除対象**（Phase 2.3 と連動）:
  - `mcp-openclaw.md` → `.openclaw/workspace/AGENTS.md` に移動済み
  - `openclaw-vps-absolute.md` → `.openclaw/workspace/AGENTS.md` に移動済み
- **CLAUDE.md に残す**: OpenClaw CLI コマンド参照（2行のみ）
- **ステータス**: pending

---

## Phase 4: agent_docs/ 作成

### TODO 4.1: ディレクトリ + 5ファイル作成

| ファイル | 内容 | 移動元 | ステータス |
|---------|------|--------|-----------|
| agent_docs/building_and_testing.md | ビルドコマンド、テスト実行方法、Fastlane lane一覧 | testing-strategy + deployment + tool-usage | pending |
| agent_docs/code_conventions.md | コード規約の要約 + SwiftLint/ESLint への参照 | coding-style.md | pending |
| agent_docs/service_architecture.md | iOS/API/DB/決済/分析の構造 | CLAUDE.md プロジェクト概要拡張 | pending |
| agent_docs/openclaw_integration.md | CC↔OpenClaw 統合プロトコル、sentinel strings、PTY パターン | AnswerOverflow スレッドのBP | pending |
| agent_docs/tool_reference.md | MCP/ツール/スキル選択ガイド | tool-usage.md | pending |

---

## Phase 5: Hooks 全面活用【v2大幅拡張】

**ソース**: claude-settings.md — 16 hook events、boris-tips — Hook #9

### TODO 5.1: hooks スクリプト作成（全8スクリプト）

| # | スクリプト | 場所 | Hook Event | 内容 | ステータス |
|---|-----------|------|-----------|------|-----------|
| 1 | session-start.sh | .claude/hooks/scripts/ | SessionStart | コンテキスト初期化、環境チェック、`once: true` | pending |
| 2 | pre-tool-lint.sh | .claude/hooks/scripts/ | PreToolUse | matcher: `Edit\|Write` → SwiftLint + ESLint 自動実行。exit 2 でブロック | pending |
| 3 | post-tool-sound.sh | .claude/hooks/scripts/ | PostToolUse | matcher: `Bash` → macOS afplay でサウンド通知 | pending |
| 4 | notification-sound.sh | .claude/hooks/scripts/ | Notification | 通知時のサウンドアラート | pending |
| 5 | stop-continue.sh | .claude/hooks/scripts/ | Stop | type: `prompt` — タスク未完了なら自動続行判定 | pending |
| 6 | pre-compact-backup.sh | .claude/hooks/scripts/ | PreCompact | compaction前のコンテキストバックアップ | pending |
| 7 | subagent-stop-validate.sh | .claude/hooks/scripts/ | SubagentStop | サブエージェント完了後のバリデーション | pending |
| 8 | user-prompt-context.sh | .claude/hooks/scripts/ | UserPromptSubmit | プロンプト送信時に追加コンテキスト注入 | pending |

### TODO 5.2: .claude/settings.json に hooks 設定追加（全イベント）

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/scripts/session-start.sh",
            "timeout": 5000,
            "once": true
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/scripts/pre-tool-lint.sh",
            "timeout": 10000
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/scripts/post-tool-sound.sh",
            "timeout": 3000
          }
        ]
      }
    ],
    "Notification": [
      {
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/scripts/notification-sound.sh",
            "timeout": 3000
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Evaluate if the task is complete. If not, respond with instructions to continue.",
            "timeout": 10000
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/scripts/pre-compact-backup.sh",
            "timeout": 5000
          }
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/scripts/subagent-stop-validate.sh",
            "timeout": 5000
          }
        ]
      }
    ]
  }
}
```

### TODO 5.3:【v2追加】Hook exit code パターン文書化

| Exit Code | 動作 | 使用例 |
|-----------|------|--------|
| 0 | 成功、続行 | 全通常フック |
| 1 | エラー（ログ、続行） | lint警告 |
| 2 | 操作をブロック | lint CRITICAL → Edit ブロック |

**ソース**: claude-settings.md — Hook Exit Codes

**ステータス**: pending

### TODO 5.4:【v3追加】SessionStart + `compact` matcher でコンテキスト再注入

**ソース**: [Anthropic Hooks Guide](https://code.claude.com/docs/en/hooks-guide) — 「Use SessionStart hook with compact matcher to re-inject critical context after compaction」

- **アクション**: compaction後に失われる重要コンテキストを自動再注入するhook追加
- **設定**:
```json
{
  "SessionStart": [
    {
      "matcher": "compact",
      "hooks": [
        {
          "type": "command",
          "command": "cat .claude/context/post-compact-essentials.md",
          "timeout": 3000
        }
      ]
    }
  ]
}
```
- **post-compact-essentials.md 内容**: 実行環境、現在のブランチ、進行中タスクのポインタ
- **ステータス**: pending

### TODO 5.5:【v3追加】Hook type 全3種の活用設計

**ソース**: [Anthropic Hooks Guide](https://code.claude.com/docs/en/hooks-guide) — 「Three hook types: command, prompt, http」

| Hook Type | 説明 | v2カバレッジ | v3アクション |
|-----------|------|------------|-------------|
| `command` | シェルコマンド実行 | ✅ 全8スクリプト | そのまま |
| `prompt` | LLM評価で判定 | ⚠️ Stop のみ | UserPromptSubmit にも追加（プロンプト品質チェック） |
| `http` | 外部URLにPOST | ❌ なし | Slack webhook通知に活用 |

**追加する prompt hook:**
```json
{
  "UserPromptSubmit": [
    {
      "hooks": [
        {
          "type": "prompt",
          "prompt": "Check if the user's request is clear enough to act on. If ambiguous, suggest clarification.",
          "timeout": 5000
        }
      ]
    }
  ]
}
```

**追加する http hook:**
```json
{
  "Stop": [
    {
      "hooks": [
        {
          "type": "http",
          "url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
          "timeout": 5000
        }
      ]
    }
  ]
}
```

- **ステータス**: pending

---

## Phase 6: CC↔OpenClaw 統合プロトコル

### TODO 6.1: Sentinel strings 定義

- **OPENCLAW_NEEDS_INPUT**: <question>
- **OPENCLAW_DONE**: <summary>
- **OPENCLAW_ERROR**: <description>
- **ステータス**: pending

### TODO 6.2: OpenClaw code-manager agent 作成

- **場所**: `~/.openclaw/agents/code-manager/`
- **ファイル**: AGENTS.md + skills/cc-integration/SKILL.md
- **ステータス**: pending

### TODO 6.3: STATUS.md / PLAN.md テンプレート

- 各 worktree に自動配置するテンプレート
- **ステータス**: pending

---

## Phase 7: 172スキル + 10エージェント + 20コマンド 監査【v2大幅拡張】

### TODO 7.1: スキル description 品質チェック

| チェック項目 | BP ソース | ステータス |
|-------------|---------|-----------|
| 三人称で書いてあるか | claude-skills.md | pending |
| `Use when ...` があるか | claude-skills.md | pending |
| 1024文字以内か | claude-skills.md | pending |
| 「プロアクティブ」表現がないか → あれば削除 | skill-authoring.md | pending |

### TODO 7.2:【v2追加】スキル frontmatter 全項目監査

**全172スキルに対して以下の frontmatter を監査・適用する:**

| frontmatter 項目 | 説明 | 適用基準 | ステータス |
|-----------------|------|---------|-----------|
| `name` | スキル名 | 全スキル必須 | pending |
| `description` | 三人称 + Use when | 全スキル必須 | pending |
| `argument-hint` | 引数のヒント | 引数を取るスキルに追加 | pending |
| `disable-model-invocation: true` | 手動のみ | deploy, commit 等の副作用ありスキル | pending |
| `user-invocable: false` | 自動のみ | Agent Skill パターン（背景知識） | pending |
| `allowed-tools` | 使えるツール制限 | read-only スキルに制限 | pending |
| `model` | モデルオーバーライド | 軽量タスクに haiku 指定 | pending |
| `context: fork` | フォークコンテキスト | 重いスキルに適用 | pending |
| `agent` | スキル実行エージェント | 専用エージェントが必要なスキルに | pending |
| `hooks` | スキル専用フック | バリデーション必要なスキルに | pending |

**ソース**: claude-skills.md — Skill frontmatter reference

### TODO 7.3:【v2追加】10エージェント frontmatter 全項目監査

**全10エージェント（.claude/agents/*.md）に対して以下を監査・適用する:**

| frontmatter 項目 | 説明 | 現状 | ステータス |
|-----------------|------|------|-----------|
| `name` | エージェント名 | あり | pending |
| `description` | 説明 | あり | pending |
| `tools` | 使えるツール | あり | pending |
| `disallowedTools` | 禁止ツール | なし → 追加 | pending |
| `model` | モデル | なし → 追加（haiku/sonnet/opus） | pending |
| `permissionMode` | 権限モード | なし → 追加 | pending |
| `maxTurns` | 最大ターン | なし → 追加 | pending |
| `skills` | プリロードスキル | なし → 追加（Agent Skill パターン） | pending |
| `mcpServers` | エージェント専用MCP | なし → 追加 | pending |
| `hooks` | エージェント専用フック | なし → 追加 | pending |
| `memory` | メモリスコープ (user/project/local) | なし → 追加 | pending |
| `background` | バックグラウンド実行 | なし → 必要なエージェントに追加 | pending |
| `isolation: worktree` | ワークツリー隔離 | なし → 必要なエージェントに追加 | pending |
| `color` | エージェント色 | なし → 追加 | pending |

**ソース**: claude-subagents.md — Agent frontmatter reference

**対象エージェント:**
1. architect.md
2. build-error-resolver.md
3. code-quality-reviewer.md
4. deploy-checker.md
5. planner.md
6. refactor-cleaner.md
7. security-auditor.md
8. tdd-guide.md
9. tech-spec-researcher.md
10. test-automation-engineer.md

### TODO 7.3a:【v3追加】`Agent(agent_type)` 制限構文の設計

**ソース**: [Anthropic Sub-agents docs](https://code.claude.com/docs/en/sub-agents) — 「Use Agent(agent_type) syntax in tools field to restrict which subagent types can be spawned」

- **アクション**: 各エージェントの `tools` フィールドで `Agent(specific_type)` を使い、スポーン可能なサブエージェント型を制限
- **設計**:

| エージェント | 許可するサブエージェント | 理由 |
|------------|----------------------|------|
| architect.md | `Agent(Explore)`, `Agent(Plan)` | 読み取り系のみ |
| tdd-guide.md | `Agent(Explore)` | テストコード探索のみ |
| security-auditor.md | `Agent(Explore)` | 脆弱性探索のみ |
| deploy-checker.md | なし（Agent禁止） | デプロイは自己完結 |

- **ステータス**: pending

### TODO 7.3b:【v3追加】Agent `skills:` preloading 設計（Agent Skill パターン）

**ソース**: [Anthropic Sub-agents docs](https://code.claude.com/docs/en/sub-agents) — 「Use skills field to preload skills into agents. Skills with user-invocable: false act as always-available context」

- **アクション**: 各エージェントに `skills:` フィールドで関連スキルをプリロード
- **設計**:

| エージェント | プリロードスキル | パターン |
|------------|----------------|---------|
| tdd-guide.md | `testing-strategy` | Agent Skill（`user-invocable: false`） |
| deploy-checker.md | `deployment` | Agent Skill |
| security-auditor.md | `security` rulesのスキル版 | Agent Skill |
| code-quality-reviewer.md | `coding-style` rulesのスキル版 | Agent Skill |

- **ステータス**: pending

### TODO 7.4:【v2追加】20コマンド frontmatter 全項目監査

**全20コマンド（.claude/commands/*.md）に対して以下を監査・適用する:**

| frontmatter 項目 | 説明 | 現状 | ステータス |
|-----------------|------|------|-----------|
| `description` | 説明 | あり | pending |
| `argument-hint` | 引数ヒント | なし → 追加 | pending |
| `allowed-tools` | ツール制限 | なし → 追加（read-onlyコマンド等） | pending |
| `model` | モデルオーバーライド | なし → 追加（軽量タスクにhaiku） | pending |

**【v2追加】String substitutions 活用:**

| パターン | 説明 | 適用先 |
|---------|------|--------|
| `$ARGUMENTS` | コマンド引数全体 | 全コマンド |
| `$1`, `$2` | 個別引数 | 引数2つ以上のコマンド |
| `${CLAUDE_SESSION_ID}` | セッションID | ログ系コマンド |
| `` !`command` `` | 動的コンテキスト注入 | git status, branch名 等 |

**ソース**: claude-commands.md — Command frontmatter + string substitutions

### TODO 7.5: 未使用スキル特定・削除

- **ステータス**: pending

---

## Phase 8: .mcp.json 作成【v2拡張】

### TODO 8.1: プロジェクトレベル MCP 設定ファイル作成

- **ファイル**: `/Users/anicca/anicca-project/.mcp.json`
- **内容（BPで推奨される5つ + 既存4つ）**:

| # | MCP | 用途 | ソース |
|---|-----|------|--------|
| 1 | **Serena** | コード検索・編集・メモリ | 既存 |
| 2 | **Maestro** | iOS E2Eテスト | 既存 |
| 3 | **Apple Docs** | Apple公式ドキュメント | 既存 |
| 4 | **Mixpanel** | 分析 | 既存 |
| 5 | **RevenueCat** | 課金 | 既存 |
| 6 | **Context7** | ライブラリドキュメント | BP推奨（claude-mcp.md） |
| 7 | **Playwright** | ブラウザ自動化 | BP推奨（claude-mcp.md） |
| 8 | **DeepWiki** | GitHub repo理解 | BP推奨（claude-mcp.md） |
| 9 | **Excalidraw** | ダイアグラム作成 | BP推奨（claude-mcp.md） |

**ソース**: claude-mcp.md — 5 recommended MCPs

- **ステータス**: pending

---

## Phase 9:【v2新規】settings.json 全面設定

**ソース**: claude-settings.md（38設定 + 84環境変数）、boris-tips（12カスタマイズ）

### TODO 9.1: .claude/settings.json をBP準拠に全面書き換え

```json
{
  "model": "opus",
  "language": "japanese",
  "alwaysThinkingEnabled": true,
  "plansDirectory": ".cursor/plans",
  "autoUpdatesChannel": "stable",

  "permissions": {
    "allow": [
      "Edit(*)",
      "Write(*)",
      "Bash(cd aniccaios && fastlane *)",
      "Bash(git *)",
      "Bash(npm run *)",
      "Bash(npx *)",
      "Bash(ssh *)",
      "mcp__serena__*",
      "mcp__maestro__*",
      "mcp__apple-docs__*",
      "mcp__context7__*"
    ],
    "ask": [
      "Bash(rm *)",
      "Bash(git push --force *)",
      "Bash(git reset --hard *)"
    ],
    "deny": [
      "Read(.env)",
      "Read(./secrets/**)",
      "Bash(xcodebuild *)"
    ],
    "defaultMode": "acceptEdits"
  },

  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "excludedCommands": ["git", "ssh", "fastlane", "ios-deploy"],
    "network": {
      "allowLocalBinding": true
    }
  },

  "statusLine": {
    "type": "command",
    "command": "echo \"$(git branch --show-current 2>/dev/null) | ctx: $(cat /dev/stdin | jq -r '.context_window.used_percentage')%\"",
    "padding": 0
  },

  "spinnerVerbs": {
    "mode": "replace",
    "verbs": ["実装中", "検索中", "分析中", "構築中", "最適化中", "テスト中", "デプロイ中", "瞑想中"]
  },

  "spinnerTipsOverride": {
    "tips": [
      "コンテキスト50%で /compact を実行",
      "大きなタスクはサブエージェントに委任",
      "Fastlane以外のビルドコマンドは禁止",
      "編集したら即push。確認不要"
    ],
    "excludeDefault": true
  },

  "attribution": {
    "commit": "Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>",
    "pr": "🤖 Generated with [Claude Code](https://claude.com/claude-code)"
  },

  "enableAllProjectMcpServers": true,
  "autoMemoryEnabled": true,
  "claudeMdExcludes": ["node_modules/**", ".build/**", "Pods/**"],

  "env": {
    "FASTLANE_SKIP_UPDATE_CHECK": "1",
    "FASTLANE_OPT_OUT_CRASH_REPORTING": "1",
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "50",
    "CLAUDE_CODE_EFFORT_LEVEL": "high",
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",
    "SLASH_COMMAND_TOOL_CHAR_BUDGET": "20000",
    "CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD": "1"
  },

  "showTurnDuration": true,
  "terminalProgressBarEnabled": true,
  "respectGitignore": true
}
```

### TODO 9.2:【v2追加】settings.local.json 作成

- **ファイル**: `.claude/settings.local.json`
- **内容**: 個人設定（git-ignored）
- **.gitignore に追加**: `settings.local.json`
- **ソース**: claude-settings.md — Settings Hierarchy Priority 2
- **ステータス**: pending

---

## Phase 10:【v2新規】Boris 12カスタマイズ完全適用

**ソース**: tips/boris-tips-feb-26.md — Boris Cherny's 12 customizations

| # | カスタマイズ | アクション | ステータス |
|---|-----------|-----------|-----------|
| 1 | Terminal設定 | `/terminal-setup` 実行（shift+enter有効化） | pending |
| 2 | Effort Level | `/model` → Opus → High（Phase 9 env で設定済み） | pending |
| 3 | Plugins | `/plugin` で利用可能なプラグイン確認・インストール | pending |
| 4 | Custom Agents | Phase 7.3 で監査済み | pending |
| 5 | Pre-approve Permissions | Phase 9.1 permissions で設定済み | pending |
| 6 | Sandbox | Phase 9.1 sandbox で設定済み | pending |
| 7 | Status Line | Phase 9.1 statusLine で設定済み | pending |
| 8 | Keybindings | `/keybindings` でカスタムキーバインド設定 | pending |
| 9 | Hooks | Phase 5 で全面設定済み | pending |
| 10 | Spinner Verbs | Phase 9.1 spinnerVerbs で設定済み | pending |
| 11 | Output Styles | `/config` で Explanatory or Custom 設定 | pending |
| 12 | settings.json in git | Phase 9.1 で .claude/settings.json をコミット | pending |

---

## Phase 11:【v2新規】CLI Flags & 環境変数の活用

**ソース**: claude-cli-startup-flags.md

### TODO 11.1: 頻用 CLI flags ドキュメント化

| Flag | 用途 | 適用場面 |
|------|------|---------|
| `--agent <NAME>` | デフォルトエージェント指定 | ralph-autonomous-dev 起動時 |
| `--worktree` / `-w` | ワークツリー隔離 | 並列開発時 |
| `--permission-mode acceptEdits` | 編集自動承認 | 自律開発モード |
| `--continue` / `-c` | 直前のセッション再開 | 中断復帰 |
| `--resume` / `-r` | 特定セッション再開 | 長期タスク復帰 |
| `--mcp-config <PATH>` | MCP設定ファイル指定 | 特殊MCP構成 |
| `--max-turns <N>` | ターン数制限 | print mode |
| `--max-budget-usd <N>` | 予算制限 | print mode |

### TODO 11.2: 環境変数の settings.json env への統合

Phase 9.1 の `env` キーに以下を追加済み:
- `FASTLANE_SKIP_UPDATE_CHECK`
- `FASTLANE_OPT_OUT_CRASH_REPORTING`
- `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50`
- `CLAUDE_CODE_EFFORT_LEVEL=high`
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
- `SLASH_COMMAND_TOOL_CHAR_BUDGET=20000`

**ステータス**: pending

---

## Phase 12:【v3新規】Plugin システム活用

**ソース**: [Anthropic Plugins docs](https://code.claude.com/docs/en/plugins) — 「Plugins extend Claude Code with additional capabilities. Use /plugin to browse marketplace」

### TODO 12.1: Plugin marketplace 調査・インストール

| # | アクション | 内容 | ステータス |
|---|-----------|------|-----------|
| 1 | `/plugin` 実行 | marketplace の利用可能プラグイン一覧取得 | pending |
| 2 | Code intelligence plugin | Swift + TypeScript のシンボルナビゲーション強化 | pending |
| 3 | 評価・インストール | 有用なプラグインをインストール | pending |

### TODO 12.2: Code intelligence plugin 設定

**ソース**: [Anthropic Plugins docs](https://code.claude.com/docs/en/plugins) — 「Code intelligence plugins give Claude precise symbol navigation」

- **目的**: Serena MCP と補完する形で、Claude 内蔵のコードインテリジェンスを強化
- **ステータス**: pending

---

## Phase 13:【v3新規】Bundled Skills 活用

**ソース**: [Anthropic Skills docs](https://code.claude.com/docs/en/skills) — 「Bundled skills: /simplify, /batch, /debug are built-in and always available」

### TODO 13.1: Bundled skills の活用ルール文書化

| Bundled Skill | 用途 | 現在の活用 | v3アクション |
|---------------|------|----------|-------------|
| `/simplify` | コードのリファクタ・品質改善 | ❌ 未使用 | tool-usage rules に追加 |
| `/batch` | 大規模変更の一括実行 | ❌ 未使用 | 大規模リファクタ時に使用ルール追加 |
| `/debug` | トラブルシューティング | ❌ 未使用 | ビルドエラー時のフローに追加 |

### TODO 13.2: Dynamic context injection（`` !`command` ``）活用設計

**ソース**: [Anthropic Skills docs](https://code.claude.com/docs/en/skills) — 「Use !`command` syntax for dynamic context injection in skills and commands」

- **設計**: 以下のスキル/コマンドに動的コンテキスト注入を追加

| スキル/コマンド | 注入するコンテキスト | 構文 |
|---------------|-------------------|------|
| deploy スキル | 現在のブランチ | `` !`git branch --show-current` `` |
| code-review コマンド | git diff | `` !`git diff --stat HEAD~1` `` |
| tdd コマンド | テスト結果 | `` !`cd aniccaios && fastlane test 2>&1 \| tail -20` `` |

### TODO 13.3:【v3追加】`context: fork` スキル設計

**ソース**: [Anthropic Skills docs](https://code.claude.com/docs/en/skills) — 「Use context: fork to run skills in a subagent with isolated context」

- **アクション**: 重いスキルに `context: fork` を追加してメインコンテキスト汚染防止
- **対象候補**:

| スキル | 理由 | context: fork |
|--------|------|--------------|
| codex-review | 大量のコード分析でコンテキスト消費 | ✅ 追加 |
| recursive-improver | 再帰ループでコンテキスト膨張 | ✅ 追加 |
| competitive-ads-extractor | 外部データ大量取得 | ✅ 追加 |
| content-research-writer | リサーチでコンテキスト消費 | ✅ 追加 |

- **ステータス**: pending

---

## Phase 14:【v3新規】`/init` と自動メモリ最適化

**ソース**: [Anthropic Best Practices](https://code.claude.com/docs/en/best-practices) — 「Use /init to generate a starter CLAUDE.md」

### TODO 14.1: `/init` 出力とのギャップ分析

- **アクション**: `/init` を実行し、生成されるCLAUDE.mdと我々のv3計画を比較
- **目的**: 公式推奨構造に合わせる最終調整
- **ステータス**: pending

### TODO 14.2: `autoMemoryEnabled` 最適化

**ソース**: [Anthropic Settings](https://code.claude.com/docs/en/settings) — 「autoMemoryEnabled controls automatic memory file creation」

- **アクション**: Phase 9.1 で `autoMemoryEnabled: true` 設定済み。auto memory ディレクトリの整理ルールを策定
- **ステータス**: pending

---

## Phase 15:【v3新規】Git構造 & スキルOSS化

**発見（2026-03-05）: 2つのリポ + 2つの住所が存在する。整理が必要。**

### 現状

| リポ | 可視性 | 場所 | 内容 |
|------|--------|------|------|
| `Daisuke134/anicca` | PRIVATE | `/Users/anicca/.openclaw/` | Aniccaの家（OpenClaw全体） |
| `Daisuke134/anicca-products` | PUBLIC | `/Users/anicca/anicca-project/` | iOS + API + CC skills 176個 |
| `Daisuke134/mobileapp-builder` | PUBLIC | 個別リポ | OSSスキル（1個だけ） |

### TODO 15.1: OSS対象スキルの特定

- **アクション**: 176 CC skills + 30 OpenClaw skills から汎用的で再利用可能なものを選定
- **命名規則**: `*-builder` → `*-factory` にリネーム（全スキルが factory）
- **ステータス**: pending

### TODO 15.2: 個別リポ作成 & git submodule 紐付け

- **構造**:
```
anicca-products/（モノリポ）
├── aniccaios/
├── apps/api/
├── .claude/skills/           ← CC専用（OSS不要なもの）
└── packages/                 ← OSSスキル（git submodule）
    ├── mobileapp-factory/       → Daisuke134/mobileapp-factory
    ├── web-app-factory/         → Daisuke134/web-app-factory
    └── ...（各スキルが個別リポ）
```
- **各OSSリポの構造**:
```
Daisuke134/<skill-name>/
├── SKILL.md
├── references/
├── scripts/
├── package.json（npm公開用）
└── README.md
```
- **ステータス**: pending

### TODO 15.3: `mobileapp-builder` → `mobileapp-factory` リネーム

- **GitHub**: リポ名変更（GitHub が自動リダイレクト）
- **submodule**: `packages/mobileapp-factory/` として紐付け
- **ステータス**: pending

---

## 実行順序（依存関係）【v3更新】

```
Phase 14（/init ギャップ分析）──→ Phase 1 ──→ Phase 2 ──→ Phase 4
                                    │            │
                                    │            ├──→ Phase 7（監査 + Agent制限 + skills preload）
                                    │            │
                                    │            └──→ Phase 13（Bundled skills + context:fork）
                                    │
                                    ├──→ Phase 3 ──→ Phase 6
                                    │
                                    ├──→ Phase 5（Hooks全面 + compact再注入 + 3type活用）
                                    │
                                    ├──→ Phase 9（settings.json + autoMemory + claudeMdExcludes）
                                    │        │
                                    │        └──→ Phase 10（Boris 12）──→ Phase 11（CLI flags）
                                    │
                                    ├──→ Phase 12（Plugins）
                                    │
                                    └──→ Phase 15（Git構造 & スキルOSS化）

Phase 8（.mcp.json — 独立、いつでも実行可）
```

**詳細:**
- Phase 14（`/init`）は Phase 1 の前に実行（公式推奨構造を把握してからスリム化）
- Phase 1（CLAUDE.md スリム化 + @import + paths）は Phase 2 の前提条件
- Phase 2（rules/ → skills/ 移行）は Phase 4, 7, 13 の前提条件
- Phase 3（AGENTS.md 作成）は Phase 6 の前提条件
- Phase 9（settings.json）は Phase 10, 11 の前提条件
- Phase 5, 8, 12 は独立

---

## 禁止事項

- 「うちのやり方の方がいい」禁止
- 「でもうちの場合は…」で例外を作ること禁止
- BPに100%従う。オリジナルゼロ。

---

## 最終目標【v3更新】

| メトリック | 現状 | 目標 | 達成度 |
|-----------|------|------|--------|
| **CLAUDE.md 行数** | 277行 | 150行以下（`@import`活用） | 0% |
| **rules/ ファイル数** | 17個 | 5個（`paths` frontmatter付き） | 0% |
| **コンテキストロード削減** | 2,485行 | ~400行（84%削減） | 0% |
| **スキル品質スコア** | 未監査 | 172スキル全て frontmatter 準拠 + `context:fork` | 0% |
| **エージェント frontmatter** | 基本のみ | 10エージェント全14項目 + `Agent(type)` 制限 + `skills:` preload | 0% |
| **コマンド frontmatter** | 基本のみ | 20コマンド全4項目 + `!`command`` 動的注入 | 0% |
| **Hooks カバレッジ** | 2/16 | 10/16（command + prompt + http 3type） | 0% |
| **settings.json 設定数** | ~5 | 38設定中25+ 活用（autoMemory, claudeMdExcludes含む） | 0% |
| **Boris 12カスタマイズ** | 0/12 | 12/12 | 0% |
| **.mcp.json MCPサーバー** | 0 | 9 | 0% |
| **Plugin** | 0 | Code intelligence + marketplace調査済み | 0% |
| **Bundled skills活用** | 0/3 | 3/3（/simplify, /batch, /debug） | 0% |
| **CC↔OpenClaw統合完成度** | - | 100% | 0% |
| **Git構造 & OSS化** | 1個別リポのみ | 全factory skill 個別リポ + submodule | 0% |
| **Phase 3 修正** | anicca-project に新規作成（間違い） | .openclaw/workspace/ の既存ファイル更新 | 0% |

---

## v2→v3 変更サマリ（16個の新ギャップ修正）

| # | ギャップ | 追加先 Phase | ソース |
|---|---------|-------------|--------|
| 1 | `@import` 構文でCLAUDE.md分割 | Phase 1（TODO 1.4） | Anthropic Memory docs |
| 2 | Path-specific rules（`paths` frontmatter） | Phase 1（TODO 1.5） | Anthropic Memory docs |
| 3 | `claudeMdExcludes` 設定 | Phase 9（settings.json） | Anthropic Memory docs |
| 4 | Bundled skills（/simplify, /batch, /debug） | Phase 13（新設） | Anthropic Skills docs |
| 5 | Prompt-based hooks 拡張 | Phase 5（TODO 5.5） | Anthropic Hooks Guide |
| 6 | HTTP hooks | Phase 5（TODO 5.5） | Anthropic Hooks Guide |
| 7 | SessionStart + compact matcher | Phase 5（TODO 5.4） | Anthropic Hooks Guide |
| 8 | Plugin システム | Phase 12（新設） | Anthropic Plugins docs |
| 9 | Code intelligence plugins | Phase 12（TODO 12.2） | Anthropic Plugins docs |
| 10 | `Agent(agent_type)` 制限構文 | Phase 7（TODO 7.3a） | Anthropic Sub-agents docs |
| 11 | Agent `skills:` preloading | Phase 7（TODO 7.3b） | Anthropic Sub-agents docs |
| 12 | `autoMemoryEnabled` 設定 | Phase 9（settings.json） | Anthropic Settings |
| 13 | `/init` コマンド活用 | Phase 14（新設） | Anthropic Best Practices |
| 14 | `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` | Phase 9（env） | Anthropic Memory docs |
| 15 | `context: fork` スキル設計 | Phase 13（TODO 13.3） | Anthropic Skills docs |
| 16 | Dynamic context injection 活用設計 | Phase 13（TODO 13.2） | Anthropic Skills docs |
| 17 | Phase 3 修正: Aniccaの実在地反映 | Phase 3（全面書き換え） | 実機調査（.openclaw/workspace/） |
| 18 | Git構造 & スキルOSS化 | Phase 15（新設） | GitHub monorepo BP + npm workspaces |
| 19 | SDD スキルインストール | `.claude/skills/spec-driven-development/` | 89jobrien/steve@spec-driven-development |

---

**最終更新**: 2026-03-05 v3
**計画者**: Claude Code
**実行者**: TBD
