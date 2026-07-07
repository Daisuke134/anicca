# codex-review — VCSDDフェーズ内の位置づけ

開発方式の正本 = プロジェクト `CLAUDE.md`「開発の道具立て」の VCSDD フェーズ表（`vcsdd-init`→`vcsdd-spec`→`vcsdd-spec-review`→`vcsdd-tdd`→`vcsdd-impl`→`vcsdd-adversary`→`vcsdd-harden`→`vcsdd-converge`）。本ファイルは **codex-review（OpenAI Codex CLI、`vcsdd-adversary`とは別モデルによる独立視点）** がその中のどこに挟まるかだけを定義する。codex-review は `vcsdd-adversary` を置き換えない——追加の視点として重ねる。

| VCSDDフェーズ | codex-review を挟むタイミング | 通過条件 |
|---|---|---|
| `vcsdd-spec-review` | spec更新直後 | codex-review → ok: true（fresh-context adversary に加えて） |
| `vcsdd-adversary`（実装レビュー） | 5ファイル以上の実装後、commit/PR/release前 | codex-review → ok: true + agent 自己完結 E2E green（maestro E2E or simulator/実機スクリーンショット検証、fresh evidence） |

| ルール | 値 |
|--------|-----|
| blocking 1件でも | 次フェーズ進行禁止 |
| 最大反復 | 5回 |

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
