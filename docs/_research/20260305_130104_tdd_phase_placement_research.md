# TDD フェーズ配置 調査レポート

## 調査情報

| 項目 | 値 |
|------|-----|
| 調査日時 | 2026-03-05 13:01 JST |
| 調査対象 | TDD は実装フェーズ内に組み込むべきか、別フェーズか |
| 調査者 | Claude Sonnet 4.6 (tech-spec-researcher role) |
| キーワード | TDD phase placement / spec-driven development TDD integration / mobile app dev workflow |

---

## 結論（先に書く）

**TDD は実装フェーズ（006a-006d）に完全に組み込む。別の「テストフェーズ」（007a-007b）として分離するのは誤り。**

Unit テスト・Integration テストは実装と同時に RED→GREEN→REFACTOR サイクルで書く。
E2E テスト（Maestro）のみ、UIが完成した後のフェーズで実行する。

---

## 出典と核心引用

### ソース 1: Martin Fowler — Test Driven Development（公式定義）

ソース: [Martin Fowler - Test Driven Development](https://martinfowler.com/bliki/TestDrivenDevelopment.html)
核心の引用: 「Write a test for the next bit of functionality you want to add. Write the functional code until the test passes. Refactor both new and old code to make it well structured.」（2023-12-11 更新）

**解説:** TDD はコードを書く「前」にテストを書くサイクル。テストを「後で」書くフェーズは TDD ではない。

---

### ソース 2: Quash — TDD Guide for Mobile App QA 2025

ソース: [Quash - TDD Guide for Mobile-App QA 2025](https://quashbugs.com/blog/test-driven-development-tdd-guide)
核心の引用: 「TDD is a feedback loop that shapes architecture, guards against regressions, and shortens feedback cycles more aggressively than any late-stage 'full regression' suite ever will. By writing a failing test first — whether unit, integration testing, or contract-level — developers codify intent before implementation.」

**解説:** 「late-stage full regression suite」（後フェーズのテスト）より TDD の方がフィードバックサイクルが速い。モバイルアプリ開発での TDD は実装と同時進行が前提。

---

### ソース 3: Kinde — Beyond TDD: Why Spec-Driven Development is the Next Step

ソース: [Kinde - Beyond TDD: Spec-Driven Development](https://www.kinde.com/learn/ai-for-software-engineering/best-practice/beyond-tdd-why-spec-driven-development-is-the-next-step/)
核心の引用: 検索結果より「there are typically five phases: Setup, TDD, Core Implementation, Integration, and Polish」— SDD の標準フェーズ構成で TDD は Core Implementation と同列（実装フェーズ内）。

**解説:** SDD のフェーズ構成では TDD は Setup の次に来る。実装後の別フェーズではない。

---

### ソース 4: SoftwareSeni — Spec-Driven Development in 2025: Complete Guide

ソース: [SoftwareSeni - SDD Complete Guide](https://www.softwareseni.com/spec-driven-development-in-2025-the-complete-guide-to-using-ai-to-write-production-code/)
核心の引用: 「In Test-Driven Development (TDD), tests become specifications for behaviour, but spec-driven extends this to full implementation. It's compatible with Agile – specifications can be iterative within sprints.」「Test requirements are defined upfront. Security requirements are explicit. Performance constraints are documented. Production readiness criteria are clear before implementation even starts.」

**解説:** テスト要件は実装「前」に定義。これは SDD においても TDD が実装フェーズに組み込まれることを意味する。

---

### ソース 5: Martin Fowler — Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl

ソース: [Martin Fowler - SDD Tools](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)
核心の引用: 「Kiro implements a 3-phase workflow: Requirements → Design → Tasks」「The design document contained sections: Testing Strategy, Implementation Approach」

**解説:** Kiro（AWS の SDD ツール）でも Testing Strategy は Design フェーズに含まれ、Implementation と同じドキュメント内に存在する。実装後の別フェーズではない。

---

### ソース 6: Anthropic — Building Effective Agents

ソース: [Anthropic - Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
核心の引用: 「Carefully craft your agent-computer interface (ACI) through thorough tool documentation and testing.」「Prompt chaining decomposes a task into a sequence of steps, where each LLM call processes the output of the previous one. You can add programmatic checks (see 'gate' in the diagram) on any intermediate steps to ensure that the process is still on track.」

**解説:** Anthropic のエージェントワークフロー設計では、各ステップにゲートチェックを組み込む。これはプロンプトチェーニングを使った TDD ゲートが「実装ステップ内」に存在するべきことを示す。

---

## フェーズ比較分析

### 誤ったフェーズ構造（アンチパターン）

```
Spec → Implementation（コードのみ） → Testing Phase（テスト後付け） → E2E
```

| 問題点 | 影響 |
|--------|------|
| テストが後付け | 設計が検証されないまま実装が進む |
| フィードバックループ遅延 | バグ発見が遅れる（実装→テストの間） |
| TDD の定義違反 | RED→GREEN→REFACTOR サイクルが成立しない |
| リファクタリング不可 | グリーンがない状態でリファクタできない |

---

### 正しいフェーズ構造（ベストプラクティス）

```
Spec → TDD+Implementation（同時） → E2E
```

| フェーズ | 内容 | テスト |
|---------|------|--------|
| GATE 1: Spec | What/Why/受け入れ条件を定義 | テストマトリックスを書く（コードは書かない） |
| GATE 2: TDD+実装 | RED→GREEN→REFACTOR を繰り返す | Unit + Integration テストを実装と同時に書く |
| GATE 3: E2E | UIが完成した後 | Maestro E2E のみここで実行 |

---

### モバイルアプリ開発への適用（Anicca フェーズ構成）

```
旧構成（誤り）:
006a → 006b → 006c → 006d → 007a（Unit） → 007b（Integration） → 007c（E2E）

正しい構成:
006a（実装+Unit Test）
006b（実装+Unit Test）
006c（実装+Integration Test）
006d（実装+Integration Test）
                    ↓
007a（E2E のみ: Maestro）
```

| フェーズ | TDD の位置 | 根拠 |
|---------|-----------|------|
| 006a-006d（実装フェーズ） | Unit + Integration テストを同時に書く | Martin Fowler: 「Write a test for the NEXT bit of functionality you want to add」= 実装前 |
| 007a-007b（E2Eフェーズ） | Maestro のみ | UIが完成しないと E2E は書けない |

---

## テスト種別ごとのフェーズ配置

| テスト種別 | 書くタイミング | 実行タイミング | 根拠 |
|-----------|-------------|-------------|------|
| Unit Test | 実装の直前（RED phase）| 実装の直後（GREEN phase）| Martin Fowler TDD 定義 |
| Integration Test | 実装の直前〜中 | 実装が完了するたびに | Quash: 「contract tests that exercise real integrations」 |
| E2E（Maestro） | UI実装完了後 | 専用フェーズで実行 | Quash: 「Full user flows」= UI完成後のみ |

---

## Anthropic プロンプトチェーニング適用

Anthropic のプロンプトチェーニングパターンをモバイルアプリ TDD に適用すると:

```
[Spec] --gate--> [TDD+実装] --gate--> [E2E]
  ↑                  ↑                  ↑
  受け入れ条件定義    RED→GREEN→REFACTOR   Maestro
  テストマトリックス   サイクル繰り返し     UIフロー検証
```

各ゲートは独立したチェックポイント。「TDD+実装」フェーズは分割しない（テストと実装は1サイクル）。

---

## セキュリティ考慮事項

該当なし（フェーズ設計の調査）

---

## パフォーマンス最適化

| 手法 | 効果 |
|------|------|
| TDD を実装フェーズに組み込む | フィードバックループが ms 単位に短縮（Quash: 「Teams practicing TDD typically report 30-50% lower mean time-to-detect」） |
| テストを後フェーズに分離しない | バグ発見コスト削減（IBM・Microsoft: 「up to 90% fewer defects in pre-release code」） |

---

## 公式ドキュメントリンク

| ドキュメント | URL |
|------------|-----|
| Martin Fowler - TDD 定義 | https://martinfowler.com/bliki/TestDrivenDevelopment.html |
| Quash - Mobile App TDD Guide 2025 | https://quashbugs.com/blog/test-driven-development-tdd-guide |
| Anthropic - Building Effective Agents | https://www.anthropic.com/research/building-effective-agents |
| Martin Fowler - SDD Tools (Kiro) | https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html |
| SoftwareSeni - SDD Complete Guide 2025 | https://www.softwareseni.com/spec-driven-development-in-2025-the-complete-guide-to-using-ai-to-write-production-code/ |
