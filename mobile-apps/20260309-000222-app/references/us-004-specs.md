# US-004: Specification Generation

Source: Anthropic Complete Guide to Building Skills — 「Skills provide the recipes: step-by-step instructions for how to use those tools effectively.」
Source: [SpecKit SDD](https://github.com/feiskyer/claude-code-settings/blob/main/skills/speckit/SKILL.md) — 「Constitution → Specify → Clarify → Plan → Tasks → Analyze → Implement」
Source: rshankras implementation-spec — https://github.com/rshankras/claude-code-apple-skills/blob/main/skills/product/implementation-spec/SKILL.md

**このファイルが US-004 の唯一の正本。** 外部スキル（implementation-spec等）は実行前に必ず読むこと。

## Sub-Sessions (004a → 004b → 004-R)

| Sub-Session | Skill | Output |
|-------------|-------|--------|
| 004a (Core Spec) | `implementation-spec` | PRD.md, ARCHITECTURE.md, IMPLEMENTATION_GUIDE.md, TEST_SPEC.md, RELEASE_SPEC.md |
| 004b (UX Spec) | `ios-ux-design` (強化版) | UX_SPEC.md, DESIGN_SYSTEM.md + onboarding rules (references/onboarding.md) |
| 004-R (Spec Review) | code-quality-reviewer agent (.claude/agents/code-quality-reviewer.md) | CRITICAL=0 across all 7 docs |

## Skills to Read

| Sub-Session | スキル | いつ読む |
|-------------|--------|---------|
| 004a | `.claude/skills/implementation-spec/SKILL.md` | Core spec generation |
| 004b | `.claude/skills/ios-ux-design/SKILL.md` | UX/Design spec + onboarding (references/onboarding.md for mau.md 8 rules) |
| 004-R | code-quality-reviewer agent (.claude/agents/code-quality-reviewer.md) — NOT codex-review skill | Spec review |
| (参考) | `.claude/skills/prd-generator/SKILL.md` | PRD セクションの深掘りが必要な時 |
| (参考) | `.claude/skills/architecture-spec/SKILL.md` | ARCHITECTURE の設計パターン選定で迷った時 |

## Input → Output マッピング

| Input ファイル | 抽出フィールド | → Output ドキュメント | → Output セクション |
|---------------|--------------|---------------------|-------------------|
| `spec/01-trend.md` | `idea`, `one_liner` | PRD.md | §1 App Overview |
| `spec/01-trend.md` | `target_user` | PRD.md, UX_SPEC.md | §2 Target User, §1 User Personas |
| `spec/01-trend.md` | `problem_statement` | PRD.md | §3 Problem Statement |
| `spec/01-trend.md` | `mvp_scope` | PRD.md, IMPLEMENTATION_GUIDE.md | §6 MVP Features, §2 Phase Breakdown |
| `spec/01-trend.md` | `monetization_model` | PRD.md | §8 Monetization |
| `spec/01-trend.md` | `platform` | ARCHITECTURE.md | §1 Platform Requirements |
| `product-plan.md` | §1 Target User | UX_SPEC.md | §1 Personas + §2 User Flows |
| `product-plan.md` | §2 Problem | PRD.md | §3 Problem Statement（深掘り版） |
| `product-plan.md` | §3 Solution | PRD.md, ARCHITECTURE.md | §5 Solution, §3 System Architecture |
| `product-plan.md` | §4 Monetization（prices） | PRD.md, RELEASE_SPEC.md | §8 Pricing, §2 Metadata |
| `product-plan.md` | §5 MVP Scope | IMPLEMENTATION_GUIDE.md | §2 Phase Breakdown |
| `product-plan.md` | §6 Localization | RELEASE_SPEC.md | §2 Localized Metadata |
| `competitive-analysis.md` | §3 Feature Comparison | PRD.md | §6 Feature Priority（競合差別化） |
| `competitive-analysis.md` | §6 Feature Gap | ARCHITECTURE.md | §4 Dependencies（差別化技術の選定根拠） |
| `market-research.md` | §2 TAM/SAM/SOM | PRD.md | §9 Market Context |

---

## Design Principles（設計原則 — 全ドキュメント共通）

Source: SpecKit SDD — 「Constitution phase: core values, technical principles, decision framework」
Source: Anthropic Skills Guide — 「Provide explicit principles that guide decision-making within the skill」

| 原則 | 適用 | 根拠 |
|------|------|------|
| **PRD が SSOT** | 全ドキュメントが PRD の値を参照する。PRD と矛盾する記述は禁止 | Single Source of Truth |
| **Rule 反映必須** | Rule 17（Mixpanel禁止）、Rule 20（自前PaywallView）、Rule 20b（ATT禁止）、Rule 21（AI API禁止）を対応ドキュメントに反映 | CLAUDE.md CRITICAL Rules |
| **相互参照 ID** | PRD の Feature ID → IMPL_GUIDE の Phase → TEST_SPEC のテスト名 で追跡可能 | トレーサビリティ |
| **実装可能な具体性** | 「〜を実装する」ではなく、型名・関数シグネチャ・ファイルパスまで記載 | Anthropic「Be Specific and Actionable」 |
| **引用必須** | 技術選定・設計判断には必ずソースを付ける | CLAUDE.md Rule 0.0 |

---

## Rule → ドキュメント マッピング

| Rule | 内容 | 反映先ドキュメント | 反映セクション |
|------|------|-------------------|---------------|
| **Rule 17** | Mixpanel 禁止（アナリティクス SDK 一切不可） | ARCHITECTURE.md, IMPLEMENTATION_GUIDE.md, TEST_SPEC.md | 依存関係リスト、禁止事項、Greenlight チェック |
| **Rule 20** | 自前 SwiftUI PaywallView + `Purchases.shared.purchase(package:)` | UX_SPEC.md, IMPLEMENTATION_GUIDE.md, TEST_SPEC.md | Paywall ワイヤーフレーム、実装手順、E2E テスト |
| **Rule 20 (RevenueCatUI禁止)** | `import RevenueCatUI` 禁止 | ARCHITECTURE.md, IMPLEMENTATION_GUIDE.md | 依存関係リスト（RevenueCat のみ、RevenueCatUI 除外） |
| **Rule 20b** | ATT 禁止（AppTrackingTransparency 不使用） | PRD.md, ARCHITECTURE.md, RELEASE_SPEC.md | Privacy セクション、PrivacyInfo.xcprivacy |
| **Rule 21** | AI API / 外部 API コスト禁止（OpenAI, Anthropic, Gemini, Apple FoundationModels 一切不可。アプリは完全自己完結。ローカル・静的コンテンツのみ。理由: 月収 $29 vs コスト $300+） | ARCHITECTURE.md, IMPLEMENTATION_GUIDE.md, TEST_SPEC.md | 依存関係リスト（AI SDK 除外）、禁止事項、Greenlight チェック |
| **Rule 21** | AI API / AI モデル / 外部 AI サービス禁止（月額収益 $29 vs API コスト $300+。Apple FoundationModels も iOS 26+ のみでユーザーベース皆無） | PRD.md, ARCHITECTURE.md, IMPLEMENTATION_GUIDE.md, TEST_SPEC.md | Technical Constraints、Dependencies、Phase Breakdown、Greenlight チェック |

---

## Process: 3 Phases（フェーズバイフェーズ）

Source: SpecKit SDD — 「Each phase has clear entry/exit criteria and file artifacts」
Source: Anthropic Skills Guide — 「Break complex workflows into clear phases with validation between each」

```
Phase 1: Foundation（PRD.md）
    ↓ Gate 1: PRD 品質チェック PASS
Phase 2: Design（ARCHITECTURE.md + UX_SPEC.md + DESIGN_SYSTEM.md）
    ↓ Gate 2: 設計整合性チェック PASS
Phase 3: Execution（IMPLEMENTATION_GUIDE.md + TEST_SPEC.md + RELEASE_SPEC.md）
    ↓ Gate 3: 全ドキュメント相互参照チェック PASS
```

---

### Phase 1: Foundation — PRD.md

**入力:** spec/01-trend.md + product-plan.md + competitive-analysis.md + market-research.md
**出力:** docs/PRD.md
**依存:** なし（最初に作成。全ドキュメントの SSOT）

#### PRD.md セクション構造（14セクション）

```markdown
# Product Requirements Document: {APP_NAME}

## 1. App Overview
（app_name, bundle_id, one_liner, platform, iOS minimum version）

## 2. Target User
（ICP 1文要約 + Demographics テーブル）

## 3. Problem Statement
（problem_statement の深掘り版 + 統計データ1-2個）

## 4. Goals & Success Metrics
（KPI テーブル: metric / target / measurement method）

## 5. Solution Overview
（solution の1段落要約）

## 6. MVP Features
（Feature ID付きテーブル: F-001, F-002... / Feature / Priority / Description）
（Feature ID は IMPLEMENTATION_GUIDE.md の Phase と対応必須）

## 7. User Stories
（US-001〜 テーブル: ID / As a / I want to / So that）

## 8. Monetization
（subscription prices: monthly + annual + trial period）
（Free tier の制限内容）

### Paywall Design Best Practices
Source: https://blog.funnelfox.com/effective-paywall-screen-designs-mobile-apps/
Source: https://adapty.io/blog/how-to-design-ios-paywall/
Source: https://appagent.com/blog/mobile-app-onboarding-5-paywall-optimization-strategies/

| Element | Requirement | Conversion Impact | Source |
|---------|------------|-------------------|--------|
| **Pricing Plans** | 3 plans minimum (weekly + monthly + annual) | 3 products vs 2: +44% | Adapty iOS Paywall Guide |
| **Discount Badge** | "Save 50%" badge + strikethrough original price | +20% to +30% | Adapty iOS Paywall Guide |
| **CTA Copy** | Benefit-driven ("Start my plan" / "Unlock full access") NOT generic ("Subscribe") | Outperforms generic CTAs | Funnelfox Paywall Guide |
| **Paywall Placement** | Immediately after onboarding (100% visibility rate) | Up to +234% | Appagent Paywall Optimization |
| **Paywall Length** | Long-form with benefits + FAQ + social proof | Up to 12× revenue | Appagent Paywall Optimization |
| **Social Proof** | Include review count, average rating, user testimonials | Boosts credibility | Funnelfox Paywall Guide |
| **Animation** | Add subtle motion on CTAs, benefit carousels | 2.9× higher conversion | Adapty iOS Paywall Guide |
| **Message Consistency** | Ad → Onboarding → Paywall must use same tone, visuals, promise | Increases conversions | Funnelfox Paywall Guide |

**Mandatory Paywall Elements:**
1. Clear headline reflecting value (not feature list)
2. 3-5 bullet points of specific benefits (tangible outcomes)
3. Pricing grid: highlight "Best Value" / "Most Popular"
4. Discount percentage visible ("Save 50%")
5. Benefit-driven CTA button
6. FAQ section (billing details, cancellation policy)
7. Social proof (review count, rating, testimonials)
8. Privacy Policy + Terms links

## 9. Market Context
（TAM/SAM/SOM 1行サマリー + 競合差別化ポイント1文）

## 10. Privacy & Compliance
（データ収集: None / ATT: No — Rule 20b / PrivacyInfo: UserDefaults CA92.1 のみ）

## 11. Localization
（対応言語テーブル: en-US, ja）

## 12. Technical Constraints
（Rule 17: no analytics SDK / Rule 20: custom PaywallView / Rule 20b: no ATT）

## 13. Out of Scope
（MVP に含まない機能リスト）

## 14. App Store Metadata
（app_name, subtitle, keywords, description, promotional_text — en-US + ja）
```

#### 🔴 PRD CRITICAL フィールド（US-005b が依存）

| フィールド | 用途 | 例 |
|-----------|------|-----|
| `app_name` | ASC アプリ作成、bundle_id 生成 | DeskStretch |
| `bundle_id` | Xcode プロジェクト、ASC 登録 | com.aniccafactory.deskstretch |
| `monthly_price` | IAP 作成、Paywall 表示 | $3.99 |
| `annual_price` | IAP 作成、Paywall 表示 | $29.99 |
| `trial_days` | RevenueCat Offering 設定 | 7 |
| `free_tier_limit` | Paywall トリガー条件 | 3 stretches/day |

#### Gate 1: PRD 品質チェック

```bash
# 全 CRITICAL フィールドが存在するか
grep -q "app_name" docs/PRD.md && echo "PASS" || echo "FAIL: app_name missing"
grep -q "bundle_id" docs/PRD.md && echo "PASS" || echo "FAIL: bundle_id missing"
grep -qE '\$[0-9]+\.[0-9]+' docs/PRD.md && echo "PASS: prices" || echo "FAIL: prices missing"
FEAT_COUNT=$(grep -c "F-00" docs/PRD.md); [ "$FEAT_COUNT" -ge 3 ] && echo "PASS: $FEAT_COUNT features" || echo "FAIL: only $FEAT_COUNT features (need ≥3)"
grep -q "Rule 17\|Rule 20\|Mixpanel" docs/PRD.md && echo "PASS: rules" || echo "FAIL: Rules not reflected"
grep -q "free_tier_limit\|Free.*limit\|free.*per day" docs/PRD.md && echo "PASS: free_tier_limit" || echo "FAIL: free_tier_limit missing"
```

**Gate 1 全 PASS → Phase 2 に進む。1つでも FAIL → PRD を修正してから進む。**

---

### Phase 2: Design — ARCHITECTURE.md → DESIGN_SYSTEM.md → UX_SPEC.md

**入力:** docs/PRD.md（SSOT）+ product-plan.md
**出力:** docs/ARCHITECTURE.md, docs/DESIGN_SYSTEM.md, docs/UX_SPEC.md
**依存:** Phase 1 完了（PRD.md が存在すること）

**🔴 生成順序（厳守）:**

```
1. ARCHITECTURE.md（最初 — Services/Models が UX の画面設計に必要）
    ↓
2. DESIGN_SYSTEM.md（2番目 — Color Tokens が UX のワイヤーフレームに必要）
    ↓
3. UX_SPEC.md（最後 — ARCH の Services + DS の Color Tokens を参照して画面設計）
```

**なぜこの順序か:** UX_SPEC §5 ワイヤーフレームは DESIGN_SYSTEM §1 Color Tokens を参照し、UX_SPEC §2 Information Architecture は ARCHITECTURE §6 Services を参照する。逆順だと参照先が存在しない。

#### ARCHITECTURE.md セクション構造（12セクション）

```markdown
# Architecture: {APP_NAME}

## 1. Platform Requirements
（iOS minimum, Xcode version, Swift version）

## 2. System Architecture Diagram
（ASCII 図: App Layer → Service Layer → Data Layer）

## 3. Directory Structure
（{APP_NAME}ios/ 配下のフォルダ構成）

## 4. Dependencies
（SPM パッケージテーブル: Package / Version / Purpose）
（🔴 RevenueCat のみ。RevenueCatUI 禁止 — Rule 20）
（🔴 Mixpanel / Analytics SDK 禁止 — Rule 17）

## 5. Data Models
（Swift struct 定義 + Codable 準拠）

## 6. Services
（各 Service の責務 + 公開メソッドシグネチャ）

## 7. Storage
（UserDefaults キーテーブル: key / type / default / purpose）

## 8. AI Integration
（🔴 Rule 21: AI API / 外部 API 一切禁止。静的コンテンツのみ。Apple FoundationModels も禁止 — iOS 26+ = ユーザー基盤が小さすぎ）

## 9. Networking
（API エンドポイントリスト — 該当する場合のみ）

## 10. Notifications
（ローカル通知スケジュール方式）

## 11. Privacy
（PrivacyInfo.xcprivacy: NSPrivacyAccessedAPICategoryUserDefaults CA92.1）
（ATT 不使用 — Rule 20b）

## 12. Error Handling
（エラー種別テーブル: type / handling / user message）
```

#### UX_SPEC.md セクション構造（9セクション）

```markdown
# UX Specification: {APP_NAME}

## 1. User Personas
（PRD §2 を展開: persona name, goals, frustrations）

## 2. Information Architecture
（画面遷移図 — ASCII）

## 3. Navigation Structure
（Tab Bar / Navigation Stack 構成）

## 4. Screen Inventory
（全画面テーブル: Screen ID / Name / Tab / Description）

## 5. Wireframes
（各画面の ASCII ワイヤーフレーム — 主要画面のみ）

## 6. Onboarding Flow
（ステップバイステップ: PRD §6 MVP Features から主要フローを導出）
（🔴 最終画面 = ソフトペイウォール — Rule 20: [Maybe Later] で閉じれる）
（フロー構成はアプリ固有。PRD の Feature 優先度に従って設計する）

## 7. Accessibility
（accessibilityIdentifier テーブル: ID / Screen / Element）
（Maestro E2E で使用するため ID は必須）

## 8. Interaction Patterns
（スワイプ、タップ、長押し等の操作定義）

## 9. Localization Notes
（en-US / ja の文字列長差異、レイアウト考慮点）
```

#### DESIGN_SYSTEM.md セクション構造（7セクション）

```markdown
# Design System: {APP_NAME}

## 1. Color Tokens
（カラーテーブル: Token / Light / Dark / Usage）

## 2. Typography
（フォントスケールテーブル: Style / Size / Weight / Line Height / Usage）

## 3. Spacing & Layout
（spacing scale: 4, 8, 12, 16, 24, 32, 48）

## 4. Components
（再利用コンポーネントテーブル: Name / Props / Usage）

## 5. Icons
（SF Symbols テーブル: Name / Symbol / Usage）

## 6. Animations
（アニメーション定義: trigger / duration / type）

## 7. Accessibility
（コントラスト比、Dynamic Type サポート、VoiceOver ラベル）
```

#### Gate 2: 設計整合性チェック

```bash
# ARCHITECTURE.md が PRD の Feature を全カバーしているか
FEAT_IN_ARCH=$(grep -c "F-00" docs/ARCHITECTURE.md)
[ "$FEAT_IN_ARCH" -ge 1 ] && echo "PASS: $FEAT_IN_ARCH features in ARCH" || echo "FAIL: no Feature IDs in ARCH"

# RevenueCatUI が混入していないか（Rule 20）
RCUI=$(grep -c "RevenueCatUI" docs/ARCHITECTURE.md)
[ "$RCUI" -eq 0 ] && echo "PASS: no RevenueCatUI" || echo "FAIL: RevenueCatUI found ($RCUI)"

# Mixpanel / Analytics が混入していないか（Rule 17）
ANALYTICS=$(grep -cE "Mixpanel|Analytics|Firebase" docs/ARCHITECTURE.md)
[ "$ANALYTICS" -eq 0 ] && echo "PASS: no analytics" || echo "FAIL: analytics found ($ANALYTICS)"

# UX_SPEC に Paywall 画面があるか（Rule 20）
grep -q "PaywallView\|Paywall\|Maybe Later" docs/UX_SPEC.md && echo "PASS: Paywall in UX" || echo "FAIL: Paywall missing in UX"

# DESIGN_SYSTEM にカラートークンがあるか
COLOR_COUNT=$(grep -c "#[0-9A-Fa-f]" docs/DESIGN_SYSTEM.md)
[ "$COLOR_COUNT" -ge 5 ] && echo "PASS: $COLOR_COUNT colors" || echo "FAIL: only $COLOR_COUNT colors (need ≥5)"

# Phase 2 生成順序確認: ARCH → DS → UX の順に作成されているか
test -f docs/ARCHITECTURE.md && test -f docs/DESIGN_SYSTEM.md && test -f docs/UX_SPEC.md && echo "PASS: all 3 files" || echo "FAIL: missing files"
```

**Gate 2 全 PASS → Phase 3 に進む。1つでも FAIL → 該当ファイルを修正してから進む。**

---

### Phase 3: Execution — IMPLEMENTATION_GUIDE.md + TEST_SPEC.md + RELEASE_SPEC.md

**入力:** docs/PRD.md + docs/ARCHITECTURE.md + docs/UX_SPEC.md + docs/DESIGN_SYSTEM.md
**出力:** docs/IMPLEMENTATION_GUIDE.md, docs/TEST_SPEC.md, docs/RELEASE_SPEC.md
**依存:** Phase 1 + Phase 2 完了

#### IMPLEMENTATION_GUIDE.md セクション構造（8セクション）

```markdown
# Implementation Guide: {APP_NAME}

## 1. Prerequisites
（Xcode version, SPM packages, 環境セットアップ手順）
（🔴 Xcode Signing: Team ID + Provisioning Profile の設定手順を含める）
（🔴 RevenueCat API Key: `.env` ファイルに保管。コードにハードコード禁止。`ProcessInfo.processInfo.environment["RC_API_KEY"]` または `Bundle.main.infoDictionary` 経由で読む）

## 2. Phase Breakdown
（Phase テーブル: Phase / Features (F-ID) / Files / Estimated Complexity）
（🔴 PRD の Feature ID と 1:1 対応必須）

## 3. Phase 1: Project Setup
（Xcode プロジェクト作成、SPM 追加、PrivacyInfo.xcprivacy）

## 4. Phase 2: Core Features
（各 Feature の実装手順: ファイル、クラス名、主要メソッド）

## 5. Phase 3: Monetization
（🔴 RevenueCat SDK 実装 — Purchases.shared.purchase(package:)）
（🔴 自前 PaywallView — RevenueCatUI 禁止）
（Product ID テーブル: id / type / price / trial）

## 6. Phase 4: Polish
（ローカライズ、アニメーション、エラーハンドリング）

## 7. Phase 5: Testing & Release Prep
（Unit Test → Integration Test → E2E の順序）

## 8. Build & Run
（fastlane コマンドテーブル: task / command）
```

#### TEST_SPEC.md セクション構造（7セクション）

```markdown
# Test Specification: {APP_NAME}

## 1. Test Strategy
（ピラミッド: Unit 70% / Integration 20% / E2E 10%）

## 2. Unit Tests
（テストテーブル: Test Name / Target / What It Verifies）
（最低 30 テスト、全 Service + Model をカバー）

## 3. Integration Tests
（Service 間連携テスト一覧）

## 4. E2E Tests (Maestro)
（YAML ファイルテーブル: File / Scenario / Key Assertions）
（🔴 accessibilityIdentifier は UX_SPEC.md §7 と一致必須）

## 5. Greenlight Checks
（🔴 Rule 17: grep -r "Mixpanel|Analytics|Firebase" → 0）
（🔴 Rule 20: grep -r "RevenueCatUI" → 0）
（🔴 Rule 20b: grep -r "ATTrackingManager" → 0）
（🔴 Rule 21: grep -rE "OpenAI|Anthropic|GoogleGenerativeAI|FoundationModels" → 0。AI API / AI モデル / 外部 AI サービス完全禁止。月額収益 $29 vs API コスト $300+。Apple FoundationModels も iOS 26+ のみでユーザーベース皆無）

## 6. Performance Targets
（起動時間、メモリ使用量、バッテリー消費の目標値）

## 7. Test Commands
（fastlane test / maestro test maestro/）
```

#### RELEASE_SPEC.md セクション構造（11セクション）

```markdown
# Release Specification: {APP_NAME}

## 1. Pre-Submission Checklist
（9 ゲートテーブル: Gate / Command / Pass Criteria）

## 2. App Store Metadata
（en-US + ja: app_name, subtitle, keywords, description, promotional_text）
（🔴 PRD §14 と完全一致必須）

## 3. Screenshots
（デバイステーブル + スクリーンショットリスト + キャプチャコマンド）

## 4. Privacy
（PrivacyInfo.xcprivacy + App Privacy 回答テーブル）

## 5. Build & Archive
（fastlane コマンドシーケンス）

## 6. TestFlight
（ベータテスト計画 + セットアップコマンド）

## 7. Submission
（レビュー情報 + コンプライアンス回答テーブル）

## 8. Review Notes
（審査官向けメモ: AI使用、サブスク管理、オフライン動作）

## 9. Age Rating
（22 項目全て NONE — 該当する場合のみ値を変更）

## 10. Hotfix Protocol
（バージョンバンプ → テスト → リリース手順）

## 11. Version History
（バージョンテーブル: Version / Date / Changes）
```

#### Gate 3: 全ドキュメント相互参照チェック

```bash
# PRD Feature ID → IMPLEMENTATION_GUIDE Phase 追跡
for FID in $(grep -oE "F-[0-9]+" docs/PRD.md | sort -u); do
  grep -q "$FID" docs/IMPLEMENTATION_GUIDE.md && echo "PASS: $FID in IMPL" || echo "FAIL: $FID missing in IMPL"
done

# UX_SPEC accessibilityIdentifier → TEST_SPEC Maestro
grep -oE '"[a-z_]+"' docs/UX_SPEC.md | head -5  # ID 存在確認

# PRD prices → RELEASE_SPEC metadata
grep -oE '\$[0-9]+\.[0-9]+' docs/PRD.md | sort -u > /tmp/prd_prices.txt
grep -oE '\$[0-9]+\.[0-9]+' docs/RELEASE_SPEC.md | sort -u > /tmp/release_prices.txt
diff /tmp/prd_prices.txt /tmp/release_prices.txt && echo "PASS: prices match" || echo "FAIL: price mismatch"

# RevenueCat SDK が IMPLEMENTATION_GUIDE に存在するか
grep -q "Purchases.shared.purchase" docs/IMPLEMENTATION_GUIDE.md && echo "PASS" || echo "FAIL: RevenueCat SDK missing"

# Rule 違反の最終チェック（全ドキュメント横断）
grep -rlE "Mixpanel|Analytics|Firebase" docs/ && echo "FAIL: Rule 17 violation" || echo "PASS: Rule 17"
grep -rl "RevenueCatUI" docs/ && echo "FAIL: Rule 20 violation" || echo "PASS: Rule 20"
grep -rl "ATTrackingManager\|requestTrackingAuthorization" docs/ && echo "FAIL: Rule 20b violation" || echo "PASS: Rule 20b"
grep -rlE "OpenAI|GoogleGenerativeAI|Anthropic|FoundationModels" docs/ && echo "FAIL: Rule 21 violation" || echo "PASS: Rule 21"
```

---

## Cross-Reference Integrity Matrix

Source: Perforce SRS — 「Each requirement should be traceable to a specific design element and test case.」

| Source Document | Field/ID | Must Appear In | Section |
|----------------|----------|---------------|---------|
| PRD.md | `app_name` | ARCHITECTURE, UX_SPEC, DESIGN_SYSTEM, IMPL_GUIDE, TEST_SPEC, RELEASE_SPEC | タイトル行 |
| PRD.md | `bundle_id` | ARCHITECTURE §1, RELEASE_SPEC §3 | Platform, Screenshots |
| PRD.md | Feature ID (F-001...) | IMPL_GUIDE §2, TEST_SPEC §2 | Phase Breakdown, Unit Tests |
| PRD.md | prices ($X.XX) | IMPL_GUIDE §5, RELEASE_SPEC §2 | Monetization, Metadata |
| PRD.md | §12 Technical Constraints | ARCHITECTURE §4, TEST_SPEC §5 | Dependencies, Greenlight |
| UX_SPEC.md | accessibilityIdentifier | TEST_SPEC §4 | Maestro E2E |
| UX_SPEC.md | Screen Inventory | IMPL_GUIDE §2 | Phase の実装対象 |
| ARCHITECTURE.md | Data Models | TEST_SPEC §2 | Unit Test 対象 |
| ARCHITECTURE.md | Services | TEST_SPEC §2-3 | Unit + Integration Test 対象 |
| DESIGN_SYSTEM.md | Color Tokens | UX_SPEC §5 | ワイヤーフレーム内の色指定 |
| ARCHITECTURE.md | §7 UserDefaults keys | TEST_SPEC §2 | Unit Test で保存/読み出し検証 |
| PRD.md | §8 trial_days | IMPL_GUIDE §5 | RevenueCat Offering の trial period |
| PRD.md | §11 Localization | RELEASE_SPEC §2 | ローカライズ対応言語一致 |
| ARCHITECTURE.md | §10 Notifications | TEST_SPEC §4 | E2E で通知スケジュール検証 |
| DESIGN_SYSTEM.md | §4 Components | IMPL_GUIDE §4 | SwiftUI コンポーネント実装 |
| PRD.md | §7 User Stories | TEST_SPEC §2 | 各 US に対応する Unit Test |

---

## Error Handling（ロールバック手順）

Source: Anthropic Skills Guide — 「Include error handling and recovery paths in your skill instructions」

| エラー | 原因 | 対処 |
|--------|------|------|
| PRD に prices がない | product-plan.md に §4 Monetization がない | US-002 に戻って product-plan.md を修正 |
| ARCHITECTURE に RevenueCatUI が混入 | LLM のハルシネーション | grep で検出 → 該当行を削除 → RevenueCat のみに修正 |
| Feature ID の不一致 | PRD 更新後に IMPL_GUIDE を更新し忘れ | Gate 3 の for ループで検出 → IMPL_GUIDE を PRD に合わせて修正 |
| 行数不足（スカスカ） | テンプレートのセクションを埋めていない | 目標行数テーブルを確認 → 不足セクションを補完 |
| 7ファイル中1つが欠落 | Phase をスキップした | `ls docs/*.md | wc -l` で 7 を確認 → 欠落ファイルを生成 |

---

## Output 目標行数

| ドキュメント | 目標行数 | 最低行数 | 根拠 |
|-------------|---------|---------|------|
| PRD.md | 300-400 | 200 | 14セクション、メタデータ含む |
| ARCHITECTURE.md | 200-300 | 150 | 12セクション、ASCII図含む |
| UX_SPEC.md | 250-350 | 200 | 9セクション、ワイヤーフレーム含む |
| DESIGN_SYSTEM.md | 150-200 | 100 | 7セクション、トークンテーブル |
| IMPLEMENTATION_GUIDE.md | 400-500 | 300 | 8セクション、全Phase詳細 |
| TEST_SPEC.md | 200-300 | 150 | 7セクション、30+テスト一覧 |
| RELEASE_SPEC.md | 250-350 | 200 | 11セクション、メタデータ全文 |
| **合計** | **1750-2400** | **1300** | — |

---

## Source Citation Rules

Source: [Anthropic Reduce Hallucinations](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations) — 「Citation-based responses significantly reduce hallucination rates.」

| ルール | 詳細 |
|--------|------|
| 技術選定の引用 | SwiftUI vs UIKit、RevenueCat vs StoreKit2 等の判断にソース |
| 設計パターンの引用 | MVVM、Repository Pattern 等の選択理由 |
| Apple ガイドラインの引用 | HIG、App Review Guidelines の該当条項 |
| フォーマット | `Source: [Name](URL) — 「原文」` |
| 最低引用数 | PRD: 3+、ARCHITECTURE: 3+、他: 各1+ |

---

## Acceptance Criteria

| # | 基準 | 検証コマンド |
|---|------|-------------|
| 1 | docs/PRD.md が存在する | `test -f docs/PRD.md && echo PASS` |
| 2 | PRD に app_name が含まれる | `grep -q "app_name\|App Name" docs/PRD.md && echo PASS` |
| 3 | PRD に bundle_id が含まれる | `grep -q "bundle_id\|com\." docs/PRD.md && echo PASS` |
| 4 | PRD に subscription prices が含まれる | `grep -cE '\$[0-9]+\.[0-9]+' docs/PRD.md` ≥ 2 |
| 5 | PRD に Feature ID が含まれる | `grep -c "F-00" docs/PRD.md` ≥ 3 |
| 6 | docs/ARCHITECTURE.md が存在する | `test -f docs/ARCHITECTURE.md && echo PASS` |
| 7 | ARCHITECTURE に RevenueCatUI がない | `grep -c "RevenueCatUI" docs/ARCHITECTURE.md` = 0 |
| 8 | ARCHITECTURE に Mixpanel がない | `grep -cE "Mixpanel\|Analytics\|Firebase" docs/ARCHITECTURE.md` = 0 |
| 9 | docs/UX_SPEC.md が存在する | `test -f docs/UX_SPEC.md && echo PASS` |
| 10 | UX_SPEC に accessibilityIdentifier がある | `grep -c "accessibilityIdentifier\|accessibility" docs/UX_SPEC.md` ≥ 1 |
| 11 | UX_SPEC に Paywall 画面がある | `grep -q "PaywallView\|Paywall\|Maybe Later" docs/UX_SPEC.md && echo PASS` |
| 12 | docs/DESIGN_SYSTEM.md が存在する | `test -f docs/DESIGN_SYSTEM.md && echo PASS` |
| 13 | DESIGN_SYSTEM にカラートークンがある | `grep -c "#[0-9A-Fa-f]" docs/DESIGN_SYSTEM.md` ≥ 5 |
| 14 | docs/IMPLEMENTATION_GUIDE.md が存在する | `test -f docs/IMPLEMENTATION_GUIDE.md && echo PASS` |
| 15 | IMPL_GUIDE に RevenueCat SDK 参照がある | `grep -q "Purchases.shared\|import RevenueCat" docs/IMPLEMENTATION_GUIDE.md && echo PASS` |
| 16 | IMPL_GUIDE に Mock がない（テストセクション除外） | `sed '/## .*[Tt]est/,/^## /d' docs/IMPLEMENTATION_GUIDE.md \| grep -c "Mock"` = 0 |
| 17 | docs/TEST_SPEC.md が存在する | `test -f docs/TEST_SPEC.md && echo PASS` |
| 18 | TEST_SPEC に Greenlight チェックがある | `grep -q "greenlight\|Greenlight" docs/TEST_SPEC.md && echo PASS` |
| 19 | docs/RELEASE_SPEC.md が存在する | `test -f docs/RELEASE_SPEC.md && echo PASS` |
| 20 | RELEASE_SPEC に en-US + ja メタデータがある | `grep -c "en-US\|ja" docs/RELEASE_SPEC.md` ≥ 4 |
| 21 | 全7ファイルが存在する | `ls docs/*.md \| wc -l` = 7 |
| 22 | 全ドキュメント横断で Rule 17 違反なし | `grep -rlE "Mixpanel\|Analytics\|Firebase" docs/` = 空 |
| 23 | 全ドキュメント横断で Rule 20 違反なし | `grep -rl "RevenueCatUI" docs/` = 空 |
| 24 | 全ドキュメント横断で Rule 20b 違反なし | `grep -rl "ATTrackingManager" docs/` = 空 |
| 25 | 全ドキュメント横断で Rule 21 違反なし | `grep -rlE "OpenAI\|GoogleGenerativeAI\|Anthropic\|FoundationModels" docs/` = 空 |
| 26 | 合計行数が 1300 行以上 | `wc -l docs/*.md \| tail -1` ≥ 1300 |
