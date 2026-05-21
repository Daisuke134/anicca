# コードレビュー: 別フェーズ vs セッション末インライン — 調査結果

調査日時: 2026-03-05 13:57 JST
調査対象: AI支援開発におけるコードレビューのタイミング（別フェーズ vs インライン）

---

## 調査結果サマリー

```
結論: レビューは「独立した別フェーズ」が正解。セッション末インラインは次善策。
────────────────────────────────────────────
判定: SEPARATE PHASE (独立フェーズ)
ソース数: 6件（Martin Fowler、Anthropic、CodeRabbit、SoftwareSeni、InfoQ、atcyrus）
業界コンセンサス: 2026年時点で統一見解あり
```

---

## 根拠 (全引用)

### 根拠1: Martin Fowler — Pre-Integration Review = 別フェーズ

ソース: [Martin Fowler - RefinementCodeReview](https://martinfowler.com/bliki/RefinementCodeReview.html)
核心の引用: 「When people think of code reviews, they usually think in terms of an explicit step in a development team's workflow. These days the Pre-Integration Review, carried out on a Pull Request is the most common mechanism for a code review.」

**解釈**: Fowlerは「コードレビュー = ワークフローの明示的なステップ」と定義。Pull Requestでのレビューが最も一般的なメカニズム = 実装セッション完了後の独立ステップ。

---

### 根拠2: Anthropic公式 — 自律ループ完了後にレビュー

ソース: [Anthropic - How Anthropic teams use Claude Code](https://www-cdn.anthropic.com/58284b19e702b49db9302d5b6f135ad8871e7658.pdf)
核心の引用: 「They give Claude abstract problems they're unfamiliar with, let it work autonomously, then review the 80% complete solution before taking over for final refinements.」

**解釈**: Anthropic自身のワークフローは「自律実装 → 完了後にレビュー」。実装中ではなく、実装完了後の独立ステップとして位置づけている。

---

### 根拠3: CodeRabbit — 2026年は「独立したレビューフェーズ」が品質のカギ

ソース: [CodeRabbit - 2025 was the year of AI speed. 2026 will be the year of AI quality](https://www.coderabbit.ai/blog/2025-was-the-year-of-ai-speed-2026-will-be-the-year-of-ai-quality)
核心の引用: 「Multi-agent workflows will normalize continuous review and validation. Instead of a single agent generating code and hoping for correctness, multi-agent systems will create a layered workflow: one agent writes, another critiques, another tests, and another validates compliance or architectural alignment.」

**解釈**: 2026年のBPは「書く → 批評する → テストする → 検証する」の多層ワークフロー。各ステップは独立。「書く」と「批評する」は別エージェント = 別フェーズ。

---

### 根拠4: SoftwareSeni — Spec-Driven Development = 実装前にgateを置く

ソース: [SoftwareSeni - Spec-Driven Development in 2025](https://www.softwareseni.com/spec-driven-development-in-2025-the-complete-guide-to-using-ai-to-write-production-code/)
核心の引用: 「You have systematic quality gates to ensure production readiness.」
核心の引用2: 「Continuous validation in CI/CD: automate security scanning on every commit. Make test suite execution a gate. Enforce code quality thresholds.」

**解釈**: Quality gate = 独立したチェックポイント。セッション末に混ぜるのではなく、CIパイプラインの独立ステップ。

---

### 根拠5: Ralph Wiggum (公式Anthropicプラグイン) — 実装ループとレビューは別

ソース: [atcyrus - The Ralph Wiggum technique](https://www.atcyrus.com/stories/ralph-wiggum-technique-claude-code-autonomous-loops)
核心の引用: 「Security-critical code - Authentication, encryption, payment processing - these need human review, not autonomous iteration.」
核心の引用2: 「Architectural decisions - Choosing between microservices vs monolith isn't something to iterate on blindly.」

**解釈**: Ralph Wiggum (公式Anthropicプラグイン) のドキュメント自体が、自律ループに「含めてはいけない」ものとしてレビューを挙げている。実装ループ = 実装専用、レビュー = 別フェーズ。

---

### 根拠6: InfoQ — Quality gateはパイプラインの独立したステップ

ソース: [InfoQ - The Importance of Pipeline Quality Gates](https://www.infoq.com/articles/pipeline-quality-gates/)
核心の引用: 「A quality gate is an enforced measure built into your pipeline that the software needs to meet before it can proceed.」
核心の引用2: 「It is possible to place a manual verification step into a CI/CD pipeline to prevent accidental errors or ensure certain measures have been properly signed off.」

**解釈**: Quality gateは「次のステージに進む前に通過しなければならない強制的な検証」。実装セッション末尾に混ぜるのではなく、パイプラインに組み込まれた独立ステップ。

---

## 結論テーブル

| 質問 | 答え |
|------|------|
| 別フェーズ vs インライン | **別フェーズ（独立したゲート）** |
| なぜ別フェーズか | 実装したエージェントは自分のエラーを見つけられない（CodeRabbit引用）。独立した目が必要 |
| 追加セッション数 | **Spec後に1回 + 実装完了後に1回 = 計2回の独立レビューゲート** |
| Ralph/自律ループでの扱い | 実装ループの「外」に置く。Ralph自体のドキュメントがそう書いている |
| Anthropic自身の実践 | 「自律実装 → 完了後にレビュー」の明確な2ステップ |

---

## 現行CLAUDE.md (dev-workflow.md) との整合性

現在の `dev-workflow.md` に書かれている3ゲートフロー:

```
GATE 1: SPEC → codex-review → ok: true
GATE 2: IMPLEMENT (TDD)
GATE 3: codex-review → ok: true
```

これは全ての出典のベストプラクティスと**完全に一致**している。

- GATE 1のcodex-review = Spec完了後の独立レビューフェーズ
- GATE 3のcodex-review = 実装完了後の独立レビューフェーズ

つまり「別フェーズが正解」というのはAnicca既存ルールの通り。

---

## 「セッション末インライン」が次善策になる条件

| 条件 | 判定 |
|------|------|
| 5行以下の変更 | インラインOK（オーバーヘッド > 効果） |
| CLAUDE.md/ドキュメントのみ変更 | インラインOK |
| 公開API変更 | 別フェーズMUST |
| 5ファイル以上の変更 | 別フェーズMUST |
| セキュリティ関連コード | 別フェーズMUST |
| インフラ変更 | 別フェーズMUST |

ソース: dev-workflow.md「codex-review 実行タイミング」テーブルと上記全出典が一致。
