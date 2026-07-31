# mobileapp-builder Best Practices Audit
# Date: 2026-03-05
# Sources: 17+ (Ralph variants, ManaLabs, rshankras, rudrankriyam, RevenueCat, Apple HIG, SonarQube, Greenlight, Maestro.dev)

## Audit Scope

| 項目 | 値 |
|------|-----|
| 対象 | mobileapp-builder パイプライン全体（US-001 ~ US-009） |
| 比較対象 | Ralph variants (harrymunro, snarktank, choo-choo, mischasigtermans), ManaLabs AppFactory, rshankras WORKFLOW, SpecKit SDD |
| 手法 | Firecrawl CLI + WebSearch で17+ソースをスクレイプ → US別比較 |

---

## Gap Summary（優先度順）

| # | 優先度 | Gap | 影響 | 対象US | 修正場所 |
|---|--------|-----|------|--------|---------|
| 1 | 🔴 P0 | `subscriptionAppStoreReviewSubmission` API 呼び出しが欠落 | Review screenshot アップロード後、サブスクが MISSING_METADATA のまま → リジェクト | US-008 Step 1h | `us-008-release.md` |
| 2 | 🟡 P1 | pricing ベストプラクティス（心理的価格設定、アンカリング）が未記載 | コンバージョン率が最適化されない | US-005b | `us-005b-monetization.md` + PRD pricing section |
| 3 | 🟡 P1 | onboarding 長さ・ペイウォール UI デザインのベストプラクティスが未記載 | トライアル開始率が最適化されない | US-004 / US-006 | `us-004-specs.md` UX_SPEC §6 + `us-006-implement.md` Step 2 |
| 4 | 🟡 P1 | Harvest Phase（アプリ完成後の学習抽出）が未定義 | progress.txt の知見が次アプリに伝播しない | Post-US-009 | CLAUDE.md + SKILL.md |
| 5 | 🟠 P2 | LLM-as-Judge（UI/UX 主観品質スコアリング）が未導入 | スクリーンショット・UI品質の自動評価ができない | US-008 Step 1 | `us-008-release.md` |
| 6 | 🟠 P2 | A/B テスト基盤（Paywall バリアント）が未実装 | 単一バリアントのみ → 最適化不可 | US-006 | 将来の US として追加 |
| 7 | ✅ 解決済 | ~~StoreKit Configuration 検証不十分~~ → RC Test Store で代替 | Maestro E2E で Simulate Success/Failure テスト | US-007 | `us-007-testing.md` + `maestro-ui-testing` |
| 8 | ⚪ P3 | CI/CD パイプライン（GitHub Actions）が未統合 | ローカルのみで検証 → 再現性リスク | 全US | 将来タスク |
| 9 | ⚪ P3 | Crash-free rate モニタリング（Sentry/Crashlytics）が未記載 | Post-launch バグ検出が手動 | Post-US-009 | 将来タスク |
| 10 | ⚪ P3 | App Store Connect API rate limiting 対策が未記載 | 大量 API 呼び出し時にスロットル | US-008 | `us-008-release.md` |

---

## US別 詳細比較

### US-001: Trend Discovery

| 観点 | 現状 | ベストプラクティス | ソース | ギャップ |
|------|------|-------------------|--------|---------|
| トレンド発見手法 | Apify + Web Search | ✅ 同等（ManaLabs: Sensor Tower + App Annie） | ManaLabs AppFactory README | なし |
| バリデーション基準 | TAM/SAM/SOM + 競合分析 | ✅ 同等 | product-agent SKILL.md | なし |
| アイデア選定 | LLM 評価 + Slack 報告 | ✅ 同等 | Ralph Playbook | なし |

### US-002: Product Planning

| 観点 | 現状 | ベストプラクティス | ソース | ギャップ |
|------|------|-------------------|--------|---------|
| PRD 生成 | product-plan.md → 手動 | ✅ 同等（SpecKit SDD pattern） | SpecKit GitHub | なし |
| 競合分析深度 | Feature comparison テーブル | ✅ 十分 | competitive-analysis SKILL.md | なし |

### US-003: Market Research

| 観点 | 現状 | ベストプラクティス | ソース | ギャップ |
|------|------|-------------------|--------|---------|
| キーワードリサーチ | Apify + manual | ✅ 同等 | aso-growth SKILL.md | なし |

### US-004: Specification Generation

| 観点 | 現状 | ベストプラクティス | ソース | ギャップ |
|------|------|-------------------|--------|---------|
| ドキュメント数 | 7ファイル（PRD, ARCH, UX, DESIGN, IMPL, TEST, RELEASE） | ✅ 業界標準以上 | SpecKit SDD, rshankras | なし |
| 相互参照 | Feature ID → Phase → Test Name | ✅ トレーサビリティ確保 | Perforce SRS | なし |
| **onboarding 設計** | UX_SPEC §6 にフロー記載あり。ただし長さ・ペイウォールデザインのBP未参照 | 🟡 オンボーディング長さ（3-5画面）、ペイウォール配置のBPを引用すべき | Revenuecat Blog, Superwall | **P1 Gap** |

### US-005a: Infrastructure

| 観点 | 現状 | ベストプラクティス | ソース | ギャップ |
|------|------|-------------------|--------|---------|
| App 作成 | asc apps create | ✅ 同等 | asc-app-create-ui SKILL.md | なし |
| Bundle ID | com.aniccafactory.<slug> | ✅ 命名規則統一 | Apple Developer Docs | なし |

### US-005b: Monetization

| 観点 | 現状 | ベストプラクティス | ソース | ギャップ |
|------|------|-------------------|--------|---------|
| IAP 作成フロー | group → subscription → locale → availability → pricing | ✅ 順序正しい | asc-ppp-pricing SKILL.md | なし |
| 175カ国価格設定 | equalization API → CSV → import | ✅ 一括設定 | rudrankriyam asc-ppp-pricing | なし |
| RC API v2 セットアップ | 全自動（WAITING_FOR_HUMAN は SK Key のみ） | ✅ 自動化度高い | RevenueCat API v2 Docs | なし |
| **価格戦略** | ハードコード ($4.99/$29.99) | 🟡 心理的価格設定、アンカリング、ディスカウント表示のBP未記載 | RevenueCat Pricing Guide, Superwall Blog | **P1 Gap** |

### US-006: Implementation

| 観点 | 現状 | ベストプラクティス | ソース | ギャップ |
|------|------|-------------------|--------|---------|
| PaywallView | 自前 SwiftUI + RC SDK | ✅ Rule 20 準拠 | Josh Holtz RC gist | なし |
| Greenlight ループ | CRITICAL=0 まで反復 | ✅ 厳格 | Greenlight README | なし |
| Mock ゼロ検証 | grep -r 'Mock' | ✅ Evidence-based | snarktank/ralph | なし |
| **ペイウォール UI デザイン** | accessibility ID 5つのみ規定 | 🟡 レイアウト・コピー・CTA配置のBP未記載 | Superwall, RevenueCat Blog | **P1 Gap** |

### US-007: Testing

| 観点 | 現状 | ベストプラクティス | ソース | ギャップ |
|------|------|-------------------|--------|---------|
| テストピラミッド | Unit 70% / Integration 20% / E2E 10% | ✅ 業界標準 | Martin Fowler Test Pyramid | なし |
| StoreKit テスト | RC Test Store + Maestro 6 flows | ✅ RC Test Store で Simulate Success/Failure（StoreKit Configuration 不要） | RevenueCat Test Store Docs | 解決済 |

### US-008: Release Preparation

| 観点 | 現状 | ベストプラクティス | ソース | ギャップ |
|------|------|-------------------|--------|---------|
| スクリーンショット | AXe + asc screenshots capture + upload | ✅ 自動化済み | asc-shots-pipeline SKILL.md | なし |
| メタデータ同期 | en-US + ja | ✅ 2ロケール対応 | asc-metadata-sync SKILL.md | なし |
| Review Screenshot | asc subscriptions review-screenshots create | ⚠️ アップロードのみ。API 後処理なし | Apple ASC API Docs | **🔴 P0** |
| **subscriptionAppStoreReviewSubmission** | **❌ 欠落** | **POST /v1/subscriptionAppStoreReviewSubmissions が必須** | Apple ASC API: subscriptionAppStoreReviewSubmissions | **🔴 P0 CRITICAL** |
| validate | asc validate Errors=0 | ✅ Gate 7 追加済み（2026-03-05） | validate.sh | なし |

### US-009: Submission

| 観点 | 現状 | ベストプラクティス | ソース | ギャップ |
|------|------|-------------------|--------|---------|
| 依存チェック | US-001~008 全 passes:true 確認 | ✅ 厳格 | Azure Pipelines Stages | なし |
| apple-appstore-reviewer | P0/P1=0 までループ | ✅ 厳格 | apple-appstore-reviewer SKILL.md | なし |
| App Privacy | asc web privacy apply + publish | ✅ 自動 | us-009-submit.md | なし |
| 提出コマンド | submissions-create → items-add → submissions-submit | ✅ 3ステップ正しい | asc-submission-health SKILL.md | なし |

---

## Pipeline-Wide Patterns（全US共通）

### 現状で正しく実装されているパターン

| パターン | 実装 | ソース |
|---------|------|--------|
| 1 US = 1 iteration | ✅ Rule 21 | ghuntley.com/ralph |
| Evidence Over Assertion | ✅ CLAUDE.md | harrymunro/ralph-wiggum |
| 3-Attempt Limit（Circuit Breaker） | ✅ CLAUDE.md | harrymunro/ralph-wiggum |
| Quality Gate（外部検証） | ✅ validate.sh | SonarQube pattern |
| Greenlight preflight + scan | ✅ Gate 1 + Gate 2 | RevylAI/greenlight |
| Consolidate Patterns（学習蓄積） | ✅ progress.txt | mischasigtermans/ralph |
| WAITING_FOR_HUMAN | ✅ Slack 通知 | Ralph Playbook |

### 欠落しているパターン

| パターン | 説明 | ソース | 優先度 |
|---------|------|--------|--------|
| Harvest Phase | アプリ完成後に progress.txt → skills/CLAUDE.md に知見を抽出 | choo-choo-ralph | P1 |
| LLM-as-Judge | スクリーンショット・UI品質の自動スコアリング | Ralph Playbook | P2 |
| CI/CD 統合 | GitHub Actions で自動実行 | SonarQube, Greenlight README | P3 |

---

## Sources（全17+ソース）

| # | ソース | URL | 用途 |
|---|--------|-----|------|
| 1 | harrymunro/ralph-wiggum | https://github.com/harrymunro/ralph-wiggum | Quality gate, evidence, 3-attempt |
| 2 | snarktank/ralph | https://github.com/snarktank/ralph | Story ordering, acceptance criteria |
| 3 | mischasigtermans/ralph | https://github.com/mischasigtermans/ralph | Progress consolidation |
| 4 | ghuntley.com/ralph | https://ghuntley.com/ralph/ | 1 item per loop |
| 5 | ManaLabs AppFactory | https://github.com/ManaLabsSF/AppFactory | Pipeline architecture |
| 6 | rshankras WORKFLOW | https://github.com/rshankras/claude-code-apple-skills | 6-phase iOS workflow |
| 7 | rudrankriyam asc-* skills | https://github.com/rudrankriyam/app-store-connect-cli-skills | ASC CLI best practices |
| 8 | RevenueCat API v2 | https://www.revenuecat.com/docs/api-v2 | Monetization setup |
| 9 | RevenueCat Pricing Guide | https://www.revenuecat.com/blog/growth/app-pricing-strategy | Pricing best practices |
| 10 | Superwall Blog | https://superwall.com/blog | Paywall design patterns |
| 11 | Apple HIG | https://developer.apple.com/design/human-interface-guidelines | UI/UX standards |
| 12 | Apple ASC API | https://developer.apple.com/documentation/appstoreconnectapi | subscriptionAppStoreReviewSubmission |
| 13 | SonarQube | https://docs.sonarsource.com/sonarqube-cloud | Quality gate pattern |
| 14 | RevylAI/greenlight | https://github.com/RevylAI/greenlight | Pre-submission compliance |
| 15 | Maestro.dev | https://maestro.dev | E2E testing |
| 16 | SpecKit SDD | https://github.com/speckit | Spec-driven development |
| 17 | Martin Fowler | https://martinfowler.com/articles/practical-test-pyramid.html | Test pyramid |

---

## Next Actions

| # | アクション | 優先度 | 対象ファイル |
|---|-----------|--------|-------------|
| 1 | `subscriptionAppStoreReviewSubmission` API 呼び出しを Step 1h 末尾に追加 | 🔴 P0 | `us-008-release.md` |
| 2 | pricing ベストプラクティスセクション追加 | 🟡 P1 | `us-005b-monetization.md` |
| 3 | onboarding/paywall デザイン BP セクション追加 | 🟡 P1 | `us-004-specs.md` + `us-006-implement.md` |
| 4 | Harvest Phase 定義を SKILL.md/CLAUDE.md に追加 | 🟡 P1 | `SKILL.md` + `CLAUDE.md` |
| 5 | LLM-as-Judge 導入検討 | 🟠 P2 | `us-008-release.md` |
