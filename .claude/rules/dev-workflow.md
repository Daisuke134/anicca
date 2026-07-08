# 実装レビュー — vcsdd-adversary のみ（codex-review は廃止）

レビューゲートは VCSDD の fresh-context adversary（モデルは `~/.claude/CLAUDE.md` モデル分業表: Opus 4.8）に一本化する。OpenAI Codex CLI による codex-review は使わない（Dais 2026-07-08）。

| フェーズ | レビュー | 通過条件 |
|---|---|---|
| `vcsdd-spec-review` | fresh adversary | blocking 0 件 |
| `vcsdd-adversary`（実装レビュー） | fresh adversary + agent 自己完結 E2E green（maestro E2E or 実ブラウザ/実行検証、fresh evidence） | blocking 0 件 + E2E green |

| ルール | 値 |
|--------|-----|
| blocking 1件でも | 次フェーズ進行禁止 |
| 最大反復 | 5回 |
| adversary は毎 iteration | fresh spawn（文脈を持ち越さない） |

## `vcsdd-adversary`/`vcsdd-converge` での Maestro判定

| 条件 | アクション |
|------|-----------|
| E2E判定セクションなし | BLOCKING — Specに追記 |
| E2E必要なのにテストなし | BLOCKING — Maestro作成 |
| E2E不要（理由明記） | スキップ可 |

## Feature Flag

```swift
if FeatureFlags.isEnabled { showNewFeature() }
```
