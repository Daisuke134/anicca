# 3ゲート開発ワークフロー

**Spec（設計）→ TDD（正しさ）→ codex-review（品質）**

| Gate | 担保 | 通過条件 |
|------|------|---------|
| GATE 1: SPEC | 設計の漏れ・矛盾 | codex-review → ok: true |
| GATE 2: TDD | テストが正しさを証明 | RED → GREEN → REFACTOR |
| GATE 3: REVIEW | 品質・セキュリティ | codex-review → ok: true + ユーザー実機確認 |

## codex-review

| ルール | 値 |
|--------|-----|
| blocking 1件でも | 次ゲート進行禁止 |
| 最大反復 | 5回 |
| 実行タイミング | Spec更新後、5ファイル以上の実装後、コミット/PR/リリース前 |

## GATE 3 Maestro判定

| 条件 | アクション |
|------|-----------|
| E2E判定セクションなし | BLOCKING — Specに追記 |
| E2E必要なのにテストなし | BLOCKING — Maestro作成 |
| E2E不要（理由明記） | スキップ可 |

## Feature Flag

```swift
if FeatureFlags.isEnabled { showNewFeature() }
```
