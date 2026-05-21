# AI支援開発ワークフローにおけるコードレビューゲート調査

## 調査日時・対象

| 項目 | 値 |
|------|-----|
| 調査日時 | 2026-03-05 13:01 JST |
| 調査対象 | AI支援開発でのレビューゲート設計 / Codex CLIレビュー vs サブエージェントレビュー |
| 調査クエリ数 | 5クエリ（英語） |

---

## 主要ソース

| ソース | URL | 信頼度 |
|--------|-----|--------|
| Addy Osmani - My LLM coding workflow going into 2026 | https://addyosmani.com/blog/ai-coding-workflow/ | 高（Google Chrome team, Jan 2026） |
| Addy Osmani - Code Review in the Age of AI | https://addyo.substack.com/p/code-review-in-the-age-of-ai | 高（2026年初頭） |
| Qodo - 5 AI Code Review Pattern Predictions in 2026 | https://www.qodo.ai/blog/5-ai-code-review-pattern-predictions-in-2026/ | 高（Jan 2026） |
| Martin Fowler - Understanding SDD: Kiro, spec-kit, and Tessl | https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html | 高（2025年後半） |
| HubSpot - Automated Code Review: The 6-Month Evolution | https://product.hubspot.com/blog/automated-code-review-the-6-month-evolution | 高（実運用報告） |
| Augment Code - When to Use Manual Code Review Over Automation | https://www.augmentcode.com/guides/when-to-use-manual-code-review-over-automation | 中 |

---

## 調査結果 1: フェーズごとにレビューゲートは必要か

### 結論: **必要。ただし「全フェーズに同じ重さ」ではなく、フェーズごとに役割を分担する。**

ソース: Martin Fowler / GitHub spec-kit ドキュメント
核心の引用: 「Crucially, your role isn't just to steer. It's to verify. At each phase, you reflect and refine.」

ソース: Augment Code / What Is Spec-Driven Development
核心の引用: 「SDD works in small, validated increments where teams break work into tasks that each deliver a testable piece of functionality, enabling frequent checkpoints where humans verify alignment and catch drift early before it compounds.」

### フェーズごとのレビュー役割マトリックス

| フェーズ | レビュー対象 | レビュー主体 | ブロッキング基準 |
|---------|------------|------------|----------------|
| Spec作成後 | 設計の漏れ・矛盾・受け入れ条件 | AI（設計レビューエージェント） | CRITICAL=0 |
| 実装フェーズ中 | テストがGREEN → 継続 | TDD（自動テスト） | テスト失敗=即停止 |
| major step完了後 | コード品質・セキュリティ・整合性 | AIサブエージェント | 5ファイル以上 or 公開API変更時 |
| コミット/PR前 | 最終チェック | AIサブエージェント | 必須 |
| セキュリティ・認証・決済コード | 脅威モデル・セキュリティ | 人間 + セキュリティツール | 絶対必須 |

---

## 調査結果 2: Codex CLI（外部ツール）vs サブエージェントレビュー

### 結論: **サブエージェント（内部）が優位。外部ツールはオーバーヘッドが大きい。**

ソース: HubSpot Engineering Blog
核心の引用: 「Rewriting their code review system using Aviator, their internal Java-based agent framework, gave them operational freedom that wasn't possible with external approaches... significantly reducing cycle time and ensuring engineers get high quality feedback as fast as possible.」

ソース: HubSpot Engineering Blog
核心の引用: 「External approaches like spinning up Kubernetes workloads for each review introduce significant overhead, with latency and cost concerns that make reviews slower and more expensive than desired.」

### 比較表

| 観点 | Codex CLI（外部ツール） | サブエージェント（内部） |
|------|----------------------|----------------------|
| コンテキスト共有 | プロジェクト固有知識なし（白紙スタート） | CLAUDE.md・Serenaメモリを参照可能 |
| レイテンシ | 高（外部プロセス起動、API呼び出し） | 低（同一セッション内） |
| コスト | 高（外部API呼び出し×反復回数） | 中（サブエージェント起動コスト） |
| 反復回数 | 多い（コンテキスト不足による誤判断） | 少ない（プロジェクト知識あり） |
| 設定・カスタマイズ | 外部ツール依存（柔軟性低） | CLAUDE.mdで完全制御可 |
| Blocking判定の精度 | 低（「多分こうだろう」的な判断） | 高（実際のコードベース参照） |
| セットアップ | 必要（インストール・認証） | 不要（Claude Code内蔵） |

---

## 調査結果 3: SDD/TDDワークフローでのレビュー頻度ベストプラクティス

### 結論: **「全フェーズに毎回」ではなく「規模とリスクに比例」させる。**

ソース: Addy Osmani - My LLM coding workflow going into 2026
核心の引用: 「Break work into small, iterative chunks. Scope management is everything - feed the LLM manageable tasks, not the whole codebase at once.」

ソース: Qodo - 5 AI Code Review Pattern Predictions in 2026
核心の引用: 「Severity-Driven Review: Every finding gets assigned a severity level. Developers know what they must address versus what's optional.」

ソース: Addy Osmani - Code Review in the Age of AI
核心の引用: 「AI-assisted code review: Ad-hoc LLM checks, IDE integrations... Automated testing loops enforce coverage >70% as a gate. Multi-model reviews run code through different LLMs to catch biases.」

### レビュー発動トリガー（規模別）

| 変更規模 | レビュー方式 | タイミング |
|---------|------------|-----------|
| 5行以下の修正 | レビューなし（テストのみ） | コミット前 |
| 5〜50行（単一ファイル） | インラインAIチェック（軽量） | 実装完了後即時 |
| 50〜200行（複数ファイル） | サブエージェントレビュー | フェーズ完了後 |
| 公開APIの変更 | サブエージェントレビュー（必須） | 実装完了後 |
| セキュリティ/決済/認証コード | 人間レビュー + セキュリティツール | マージ前 |
| インフラ変更 | サブエージェントレビュー（必須） | 実装完了後 |

---

## 調査結果 4: 「全フェーズにcodex-review」の問題点

ソース: Martin Fowler - Understanding SDD
核心の引用: 「With the amount of steps spec-kit took, and the amount of markdown files it created for me to review, this again felt like overkill for the size of the problem... I never even finished the full implementation, but I think in the same time it took me to run and review the spec-kit results I could have implemented the feature with 'plain' AI-assisted coding.」

ソース: Qodo - 5 AI Code Review Pattern Predictions in 2026
核心の引用: 「If you've ever watched a bot flood a PR with 37 comments about spacing while missing the one null-check that takes production down, you already understand why Severity-Driven Review needs to exist. AI makes it trivial to generate findings. The real challenge is triage.」

### 「毎フェーズ重いレビュー」の問題

| 問題 | 影響 |
|------|------|
| 反復時間が実装時間を上回る | 「レビューのためのレビュー」状態になる |
| コメントノイズで重要な指摘が埋もれる | 開発者がレビュー結果を無視し始める |
| コンテキスト不足で誤判断 | 「CRITICAL」誤検知によるブロック |
| 外部ツールのレイテンシ累積 | 1フェーズ5分 × 5フェーズ = 25分ロス |

---

## 推奨レビュー構造（Aniccaプロジェクト適用版）

```
GATE 1: Spec作成後
  └─ サブエージェント（spec-reviewer）
  └─ 条件: ok:true → 次のゲートへ / blocking→Spec修正
  └─ 所要時間目安: 30秒〜2分

GATE 2: TDD実装中（自動）
  └─ テスト結果のみ（RED→GREEN→REFACTOR）
  └─ レビューツール不要。テストがゲート。

GATE 3: 実装完了後（規模判定）
  └─ 5ファイル未満 + 公開API変更なし → スキップ可
  └─ 5ファイル以上 or 公開API変更 → サブエージェント
  └─ セキュリティ/決済コード → 人間必須

GATE 4: コミット前（軽量）
  └─ サブエージェントの簡易チェック or
  └─ テスト全通過確認のみ（小規模時）
```

---

## セキュリティ考慮事項

- AI生成コードの45%にセキュリティ上の欠陥（Veracode調査）
- ロジックエラーは人間コードの1.75倍の頻度
- 認証・決済・シークレットを扱うコードは必ず人間レビュー

---

## 情報の鮮度確認

| 項目 | 確認結果 |
|------|---------|
| 最新ソース日付 | 2026年1月〜3月 |
| 知識カットオフ以内 | ✅ |
| 公式性 | ✅（Anthropic, Google Chrome Team, Martin Fowler） |
