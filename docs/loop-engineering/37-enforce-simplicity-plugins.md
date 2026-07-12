# 37 — 車輪の再発明防止 + シンプルさ強制の skill/plugin/hook 調査 (2026-07-13)

## 結論（先に）

- **#1（既存解を先に探させる）= 未導入、要インストール**: `gaupoit/programming-advisor`
- **#2（シンプルさ強制）= 既に導入済み・未活用**: `code-simplification`（addy-agent-skills, `agent-skills:code-simplify`）+ built-in `simplify` skill
- 「hook で機械的に強制」（gate/block）してくれる純粋な仕組みは **見つからなかった**。両方とも「skill の自動トリガー」（description マッチで自動起動）方式であり、Claude Code の hook（PreToolUse で exit 2 して止める）ほど硬い強制ではない。

## 1. 既存実装を先に探させる仕組み

### 採用候補: `gaupoit/programming-advisor`
- ソース: https://github.com/gaupoit/programming-advisor
- 核心の引用: 「This skill acts as a "Reinventing the Wheel" detector. When you describe something you want to build, it will: 1. Search for existing solutions... 2. Estimate vibe coding costs... 3. Present a comparison table... 4. Calculate total cost of ownership... 5. Make a recommendation... 6. Plan the integration」
- 自動トリガー: 「The skill triggers automatically when you describe something you want to build」（"I want to build a PDF generator" 等の発話で発火）
- 実データ: stars=12、pushedAt=2025-12-31（動いているコード、デモ repo `gaupoit/dont-reinvent-the-wheel-demo` あり、vaporware ではない）
- インストール:
  ```bash
  /plugin marketplace add gaupoit/programming-advisor
  /plugin install programming-advisor
  ```

### 他候補（参考、programming-advisor ほど直接的ではない）
- `scodge-24/cba-searching` — https://github.com/scodge-24/cba-searching
  核心の引用: 「searches GitHub for every similar project and counts the field... a blunt, evidence-backed call on whether you've found a gap or just rebuilt a wheel.」
  手動発火 `/cba-searching` のみ（自動トリガーなし）。しかも自己適用した結果、自分より優れた競合 `r14dd/patent` を検出して「作るな」と自己否定した経緯あり。
- `r14dd/patent`（Rust CLI, cargo install） — https://github.com/r14dd/patent
  核心の引用: 「patent takes a plain-English dev-tool idea and searches 16 sources... ranked by semantic similarity and summarised as Open, Crowded, or Saturated.」
  Claude Code 統合ではなく単体 CLI（cargo install patent）。CI green、crates.io 公開済みで cba-searching より成熟。ただし Claude Code の skill/hook ではないため、今回の要求（Claude Code に対する統合）には programming-advisor の方が適合。
- 既存 `~/.claude/plugins/marketplaces/ecc/.kiro/skills/search-first/SKILL.md`（ECC marketplace 内、既にインストール済みだが `.kiro/skills/` 配下で通常の skill 探索対象外の可能性あり、要確認）
  核心の引用: 「Systematizes the "search for existing solutions before implementing" workflow... 0. Does this already exist in the repo?... 4. Is there a GitHub implementation/template?」

## 2. シンプルさを強制する仕組み

### 既に導入済み・未活用
- `agent-skills:code-simplification`（`~/.claude/plugins/marketplaces/addy-agent-skills/skills/code-simplification/SKILL.md`）
  出典元コメント: 「Inspired by the Claude Code Simplifier plugin」→ https://github.com/anthropics/claude-plugins-official/blob/main/plugins/code-simplifier/agents/code-simplifier.md（Anthropic公式）
  Five Principles: Preserve Behavior Exactly / Follow Project Conventions / Prefer Clarity Over Cleverness 等
- built-in `simplify` skill（Claude Code 標準、marketplace 外）: 「Review the changed code for reuse, simplification, efficiency, and altitude cleanups, then apply the fixes.」

→ どちらも **既にこの環境にある**。追加インストール不要、呼び出すだけでよい。

## 3. hook による機械的強制（見つからなかった）

`AdeAnima/coding-toolkit` の `worktree-gate` が唯一の「PreToolUse hook で毎 Edit/Write に発火する deterministic gate」の実例だったが、これは worktree 隔離の warn-only nudge であり、simplicity/reinvention とは無関係。
核心の引用: 「The worktree nudge is a gate — it has to fire before an edit, every time... Only a hook guarantees that. Skills undertrigger; advisory memory is ignorable.」
→ この構造（hook=deterministic gate、skill=on-demand judgment）自体は流用可能な設計思想だが、「search-first」「simplicity」を hook で機械判定するテンプレは gh 上に実在しなかった（判断が意味論的で hook 側では検証不能なため）。

## 4. 環境確認結果

- `~/.claude/plugins/` に既にインストール済み: addy-agent-skills, callstack-agent-skills, ccteams, claude-plugins-official, ecc, fablize, goal-setter, show-me-the-money, superpowers-marketplace, ui-ux-pro-max-skill, vcsdd-claude-code, ww-w-ai, alexgreensh-token-optimizer
- 自作の `investigate-before-acting` skill（`~/anicca-project/.claude/skills/investigate-before-acting/SKILL.md`）は既に「search→cite→execute」の prose protocol を持つが、hook 強制ではなく、build-intent 発話への自動トリガー最適化もされていない。programming-advisor はこの隙間（「build」と言った瞬間に反射的に探す」）を埋める。
