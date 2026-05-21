# DeskStretch 改善計画（統合版）

**Date:** 2026-03-06（v5 — Phase C 進捗更新 + 未解決問題追加 + 20セッション構成）
**Sources:**
- [Martin Fowler - Test Driven Development](https://martinfowler.com/bliki/TestDrivenDevelopment.html) — 「Write a test → Write code → Refactor」
- [Anthropic Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) — 「Prompt chaining with programmatic gates」
- [HubSpot - Automated Code Review](https://product.hubspot.com/blog/automated-code-review-the-6-month-evolution) — 「Internal agent > external tool」
- [RevenueCat Test Store](https://www.revenuecat.com/docs/test-and-launch/sandbox/test-store)
- [Quash - TDD Guide for Mobile-App QA](https://quashbugs.com/blog/test-driven-development-tdd-guide)
- [Martin Fowler - RefinementCodeReview](https://martinfowler.com/bliki/RefinementCodeReview.html) — 「code reviews = an explicit step in workflow」
- [Anthropic Skills Guide](https://www.anthropic.com/engineering/claude-code-best-practices) — 「Keep SKILL.md focused on core instructions」
- [Mau - Prayer Lock $25k/month](mau.md) — オンボーディング8ルール

---

## Phase C 進捗状況（2026-03-06 最終版）

### ALL DONE

| # | 項目 | コミット | 内容 |
|---|------|---------|------|
| 1 | ios-ux-design スキル強化 | `5d0bfddb` | 772→219行 + references/ 分割 + mau.md 統合 |
| 2 | tdd-feature スキル強化 | `88ca599d` | Canon TDD + iOS パターン + Fastlane コマンド |
| 3 | maestro-ui-testing スキル強化 | `7cce3aae` | Fix Loop + RC Test Store |
| 4 | us-006-implement.md 書き直し | `61aaa32e` | 399→161行。スキル参照 + 変数 + Gate のみ |
| 5 | us-007-testing.md 書き直し | `61aaa32e` | 57→82行。E2E のみ（Unit/Int は 006 完了済み）|
| 6 | us-004-specs.md 更新 | `524a5ddd` | サブセッション表追加 |
| 7 | us-005b-monetization.md 更新 | `524a5ddd` | RC Test Store セクション追加 |
| 8 | SKILL.md 更新 | `524a5ddd` | スキル割り当て + Rule 4 Fastlane 必須化 |
| 9 | CLAUDE.md 更新 | `524a5ddd` | セッション分割反映 |
| 10 | prd.json US-007 AC 更新 | `524a5ddd` | 6 Maestro flows 反映 |
| 11 | best-practices-audit.md 更新 | `524a5ddd` | Gap #7 解決済みに変更 |
| 12 | Fix Loop 修正 | `5fabee9b` | us-007: 重複削除、maestro skill: 上限なし |
| 13 | "読まなくても" → "MUST READ" | `5fabee9b` | us-001, us-003, us-004 の3ファイル |
| 14 | SKILL.md 004-R, 006-R 追加 | `5fabee9b` | US表に review フェーズ行追加 |
| 15 | us-004 Mixpanel 警告削除 | `5fabee9b` | SKILL.md Rule 12 で十分 |
| 16 | prd.json 20分割 | (本コミット) | US-004→3分割、US-006→5分割、計20エントリ |
| 17 | 1US=1スキル統合 | (本コミット) | US-001,003,005b,008a,008c,008e を単一スキルに |
| 18 | CLAUDE.md Mixpanel 注記 | (本コミット) | 「Anicca専用。factory アプリには入れない」追記 |
| 19 | validate.sh 20セッション対応 | (本コミット) | US-006 → US-006-R に変更 |
| 20 | 34件トレーサビリティ検証 | (本コミット) | 全34件 PASS（下記参照） |

### Fat→Thin レシピ（DEFERRED to Phase E）

| レシピ | 行数 | 状態 | 理由 |
|--------|------|------|------|
| us-006-implement.md | 161 | THIN | スキル参照 + 変数 + Gate のみ |
| us-007-testing.md | 94 | THIN | スキル参照 + 変数 + Gate のみ |
| us-005a-infra.md | 151 | THIN | 十分薄い |
| us-005b-monetization.md | 332 | THICK | RC API v2 curl 手順。rc-monetization-setup スキル作成で thin 化可能 |
| us-001-trend.md | 380 | THICK | 5-Lens 手順。外部スキル idea-generator を補完するファクトリー固有手順 |
| us-002-planning.md | 246 | THICK | 4-Agent 手順。外部スキル prd-generator を補完 |
| us-003-research.md | 292 | THICK | iTunes API + TAM/SAM/SOM。外部スキル competitive-analysis を補完 |
| us-008-release.md | 393 | THICK | AXe + ASC CLI 手順。asc-shots-pipeline スキルと一部重複 |
| us-009-submit.md | 133 | THIN | 十分薄い |

**判断:** THICK レシピの手順は外部スキル（rshankras等）を補完するファクトリー固有コンテンツ。
新規ラッパースキル作成は Phase E（新アプリ検証）で実際に走らせた後に判断する。
現時点で重複している内容（us-008 内の asc-shots-pipeline 手順等）は Phase E で特定・除去する。

### アーキテクチャ原則（Phase C 残作業の指針）

**「Juice goes in skills」**: 再利用可能な手順 → スキル（SKILL.md + references/）。アプリ固有 → レシピ .md。
**レシピ = thin**: 「スキル X を読め」+ 変数 + Gate チェック。手順の重複禁止。
**SSOT in skills**: スキルに書いたらレシピに書くな。2か所に書いたら2か所直す羽目になる。

---

## 全体フロー（Phase A → B → C → D → E → F）

```
Phase A: SDD Spec（修正仕様書を書く — 3セッション）      ← DeskStretch 固有
    |
Phase B: TDD Fix（仕様に従って修正する — 6セッション）    ← DeskStretch 固有
    |
Phase C: レシピ更新（学びを skills + references/ に反映） ← 完了（20/20 DONE + fat→thin DEFERRED）
    |
Phase D: DeskStretch US-008a〜009 完走                    ← 未着手
    |
Phase E: 新アプリで検証（US-001〜009 フル実行）           ← 未着手
    |
Phase F: Cron テスト（15:00 JST 自動実行）               ← 未着手
```

### prd.json セッション構成（全20セッション）

| # | US | Title | スキル |
|---|-----|-------|--------|
| 1 | US-001 | Trend research + idea selection | idea-generator |
| 2 | US-002 | Product planning | prd-generator |
| 3 | US-003 | Market research | competitive-analysis |
| 4 | US-004a | Core Spec (PRD, ARCH, IMPL) | implementation-spec |
| 5 | US-004b | UX Spec (UX, DESIGN, TEST, RELEASE) | frontend-design |
| 6 | US-004-R | Spec Review | code-quality-reviewer (subagent) |
| 7 | US-005a | Privacy Policy + ASC app creation | asc-cli-usage |
| 8 | US-005b | IAP + pricing + RevenueCat setup | asc-ppp-pricing |
| 9 | US-006a | TDD Data Layer | tdd-feature |
| 10 | US-006b | TDD Onboarding + Monetization | tdd-feature |
| 11 | US-006c | TDD Core Screens | tdd-feature |
| 12 | US-006d | TDD Polish + Resources | tdd-feature |
| 13 | US-006-R | Code Review | code-quality-reviewer (subagent) |
| 14 | US-007 | E2E Testing (Maestro) | maestro-ui-testing |
| 15 | US-008a | Screenshots (capture + upload + review) | asc-shots-pipeline |
| 16 | US-008b | ASC metadata sync (en-US + ja) | asc-metadata-sync |
| 17 | US-008c | IPA build + upload + version attach | asc-xcode-build |
| 18 | US-008d | ASC compliance | asc-release-flow |
| 19 | US-008e | Preflight + TestFlight + Slack | release-review |
| 20 | US-009 | App Store submission | asc-submission-health |

### スキル割り当て（1フェーズ = 1スキルのみ — DeskStretch 固有セッション）

| フェーズ | スキル | 根拠 |
|---------|--------|------|
| 004a (Core Spec) | `implementation-spec` | マスターオーケストレーター |
| 004b (UX Spec) | `frontend-design` | デザイン思考 + 美学 |
| 004-R (レビュー) | code-quality-reviewer | 内部サブエージェント |
| 006a (Data Layer) | `tdd-feature` | Canon TDD + iOS |
| 006b (Onboarding + Monetization) | `tdd-feature` | Canon TDD + iOS |
| 006c (Core Screens) | `tdd-feature` | Canon TDD + iOS |
| 006d (Polish + Resources) | `tdd-feature` | Canon TDD + iOS |
| 006-R (レビュー) | code-quality-reviewer | 内部サブエージェント |
| 007 (E2E) | `maestro-ui-testing` | Maestro 専門 |

---

## 1. 現状の問題（コード監査結果 — 21件）

### 🔴 CRITICAL（1件）

| # | 問題 | ファイル | 詳細 |
|---|------|---------|------|
| 1 | **RC API Key ハードコード** | `DeskStretchApp.swift:9` | `appl_OnzEebYgDRvFDkPgGmi...` 直接コード。xcconfig / Info.plist 必須 |

### 🔴 HIGH（12件）

| # | 問題 | カテゴリ | ファイル | 詳細 |
|---|------|---------|---------|------|
| 2 | **URL force-unwrap → クラッシュ** | Security | `SettingsView.swift:66` | `URL(string: "...")!` — nil 時クラッシュ |
| 3 | **URL force-unwrap → クラッシュ** | Security | `PaywallView.swift:84` | Terms リンク同上 |
| 4 | **「AI-personalized」虚偽表示** | UI/UX | `PaywallView.swift:33` | Rule 21 + Apple 虚偽広告違反 |
| 5 | **Offerings ロード失敗 → 永遠スピナー** | UI/UX | `PaywallView.swift:54` | タイムアウト/エラー表示なし |
| 6 | **「Upgrade」ボタン空** | UI/UX | `SettingsView.swift:49-51` | タップしても何も起きない |
| 7 | **ProblemEmpathy Hook 弱い** | UI/UX | `ProblemEmpathyView.swift` | UX_SPEC と不一致 |
| 8 | **通知許可ステップなし** | UI/UX | `OnboardingContainerView.swift` | 3ステップのみ |
| 9 | **無効ボタンの理由非表示** | UI/UX | `PainAreaSelectionView.swift:45` | ヘルパーテキストなし |
| 10 | **intervalMinutes=0 → ゼロ除算** | UI/UX | `TimerView.swift:86` | `totalSeconds = 0` でクラッシュ |
| 11 | **StretchLibraryService 二重初期化** | Code | `TimerView.swift:11-16` | メモリ浪費 + 状態不整合 |
| 12 | **accessibilityIdentifier 不整合** | Accessibility | 複数ファイル | 6箇所で TEST_SPEC と不一致 |
| 13 | **SubscriptionService テスト不可** | Code | `SubscriptionService.swift:5` | Protocol 化なし |

### 📌 MEDIUM（8件）

| # | 問題 | カテゴリ | ファイル | 詳細 |
|---|------|---------|---------|------|
| 14 | **JSON ロード失敗 = サイレント** | UI/UX | `StretchLibraryService.swift:7-11` | エクササイズ 0 件でもエラー表示なし |
| 15 | **ISO8601DateFormatter 毎フレーム生成** | Performance | `ProgressDashboardView.swift:102` | ループ外に移動必須 |
| 16 | **曜日ラベル "T"/"T" 区別不能** | UI/UX | `ProgressDashboardView.swift` | "Tu"/"Th" に変更 |
| 17 | **AppState が God Object** | Code | `AppState.swift` | 全状態 + 全永続化が1ファイル |
| 18 | **メインスレッドタイマー** | Code | `TimerView.swift:86` | バックグラウンドで停止 |
| 19 | **DESIGN_SYSTEM トークン未適用** | UI/UX | 全 View | `.accentColor` のみ使用 |
| 20 | **duration 入力バリデーションなし** | Security | `ProgressService` | 負数/巨大値でクラッシュ |
| 21 | **ローカライズファイル欠落** | i18n | 全 View | `.xcstrings` なし |

---

## 2. accessibilityIdentifier 不整合マッピング

| TEST_SPEC / Maestro ID | 実コード ID | ファイル | 修正 |
|------------------------|------------|---------|------|
| `paywall_maybe_later` | `paywall_skip` | PaywallView.swift:72 | → `paywall_maybe_later` |
| `timer_stretch_now` | `stretch_now` | TimerView.swift:59 | → `timer_stretch_now` |
| `timer_countdown` | `timer_ring` | TimerView.swift:36 | → `timer_countdown` |
| `session_exercise_name` | なし | StretchSessionView.swift:56 | 追加必須 |
| `session_skip` | `stretch_skip` | StretchSessionView.swift:80 | → `session_skip` |
| `pain_area_neck` | なし | PainAreaCard.swift | `pain_area_\(painArea.rawValue)` 追加 |
| `onboarding_continue` | ✅ 一致 | PainAreaSelectionView.swift:47 | OK |
| `onboarding_get_started` | ✅ 一致 | ProblemEmpathyView.swift:31 | OK |

---

## 3. Phase A: SDD Spec（3セッション）

### 004a: Core Spec

**Skill:** `implementation-spec`

| # | 成果物 | 修正する問題 | 内容 |
|---|--------|-------------|------|
| 1 | PRD.md（修正版） | #4 | Rule 21（AI 禁止）を明記 |
| 2 | ARCHITECTURE.md | #13 | SubscriptionService Protocol 化を設計 |
| 3 | ARCHITECTURE.md | #17 | AppState → MVVM 分割を設計 |
| 4 | IMPLEMENTATION_GUIDE.md | #1 | xcconfig で API Key 管理 |

**Gate:** fastlane build PASS

### 004b: UX Spec

**Skill:** `frontend-design`

| # | 成果物 | 修正する問題 | 内容 |
|---|--------|-------------|------|
| 1 | UX_SPEC.md | #7 | Onboarding Hook 強化（mau.md 3幕構成） |
| 2 | UX_SPEC.md | #8 | 通知許可ステップ追加 |
| 3 | UX_SPEC.md | #9 | 無効ボタン理由表示 |
| 4 | DESIGN_SYSTEM.md | #19 | トークン定義（色、フォント、スペーシング） |
| 5 | TEST_SPEC.md | #12 | accessibilityIdentifier 正規マッピング |
| 6 | TEST_SPEC.md | TODO #28,#29 | AI 参照削除 + 性能基準修正 |
| 7 | RELEASE_SPEC.md | — | リリース設定 |

**Gate:** Spec 整合性確認

### 004-R: REVIEW（004a + 004b 両方）

**Tool:** code-quality-reviewer サブエージェント

**Gate:** CRITICAL=0

---

## 4. Phase B: TDD Fix（6セッション）

### TDD サイクル（006a-d 共通）

```
機能 N を実装:
  1. [RED]      テストを書く → fastlane test → FAIL 確認
  2. [GREEN]    最小コードで通す → fastlane test → PASS 確認
  3. [REFACTOR] クリーンアップ → fastlane test → PASS 維持
  4. 次の機能へ
```

### 006a: TDD Data Layer

**Skill:** `ios-ux-design`

| # | 修正内容 | 問題# | テスト |
|---|---------|-------|--------|
| 1 | xcconfig で API Key 分離 | #1 | Unit: config から読み込み確認 |
| 2 | SubscriptionService Protocol 化 | #13 | Unit: Mock で購入フロー |
| 3 | StretchLibraryService エラーハンドリング | #14 | Unit: JSON 失敗時の挙動 |
| 4 | Models に正しい accessibilityIdentifier | #12 | Unit: ID 存在確認 |
| 5 | ProgressService 入力バリデーション | #20 | Unit: 負数/巨大値ガード |

**Gate:** fastlane test PASS

### 006b: TDD Onboarding + Monetization

**Skill:** `ios-ux-design`

| # | 修正内容 | 問題# | テスト |
|---|---------|-------|--------|
| 1 | AppState → MVVM 分割 | #17 | Unit: ViewModel 状態遷移 |
| 2 | Onboarding 通知許可ステップ追加 | #8 | Unit: フロー遷移 |
| 3 | Onboarding Hook を UX_SPEC 準拠に | #7 | Unit: Hook テキスト |
| 4 | PaywallView: offerings エラー表示 | #5 | Integration: offerings 読み込み |
| 5 | PaywallView: 「AI-personalized」削除 | #4 | Unit: テキスト確認 |
| 6 | PaywallView: DESIGN_SYSTEM トークン適用 | #19 | Unit: トークン使用 |
| 7 | URL force-unwrap → optional binding | #2, #3 | Unit: nil URL ハンドリング |

**Gate:** fastlane test PASS

### 006c: TDD Core Screens

**Skill:** `ios-ux-design`

| # | 修正内容 | 問題# | テスト |
|---|---------|-------|--------|
| 1 | Timer: バックグラウンドタイマー対応 | #18 | Unit: バックグラウンド復帰 |
| 2 | Timer: ゼロ除算ガード | #10 | Unit: intervalMinutes=0 |
| 3 | Timer: StretchLibraryService 二重初期化修正 | #11 | Unit: singleton 確認 |
| 4 | Settings: Upgrade → PaywallView 遷移 | #6 | Unit: 遷移確認 |
| 5 | ProgressDashboard: DateFormatter 最適化 | #15 | Unit: 性能 |
| 6 | ProgressDashboard: 曜日ラベル "Tu"/"Th" | #16 | Unit: 表示確認 |

**Gate:** fastlane test PASS

### 006d: TDD Polish + Resources

**Skill:** `ios-ux-design`

| # | 修正内容 | 問題# | テスト |
|---|---------|-------|--------|
| 1 | 全 View に DESIGN_SYSTEM トークン適用 | #19 | Integration: トークン一貫性 |
| 2 | 全 a11y ID を TEST_SPEC 準拠に修正 | #12 | Integration: ID 存在確認 |
| 3 | PrivacyInfo.xcprivacy 作成 | #21 | Integration: ファイル存在 |
| 4 | ローカライズファイル（.xcstrings）作成 | #21 | Integration: ファイル存在 |
| 5 | PainAreaSelectionView: 無効ボタン理由表示 | #9 | Unit: ヘルパーテキスト |

**Gate:** fastlane test PASS + fastlane build PASS

### 006-R: REVIEW

**Tool:** code-quality-reviewer サブエージェント（006a-d 全体を対象）

**Gate:** CRITICAL=0

### 007: E2E Maestro + Payment

**Skill:** `maestro-ui-testing`

| # | フロー | 内容 |
|---|--------|------|
| 1 | 01-onboarding.yaml | 全オンボーディングフロー |
| 2 | 02-timer.yaml | タイマー起動→ストレッチ |
| 3 | 03-settings.yaml | 設定画面遷移 |
| 4 | 04-payment-success.yaml | RC Test Store → Simulate Success |
| 5 | 05-payment-failure.yaml | RC Test Store → Simulate Failure |

**Gate:** maestro test maestro/ PASS

---

## 5. 決済 E2E テスト — RC Test Store + Maestro

### RC Test Store の仕組み

```
通常の購入フロー:
  ユーザー → 「Monthly $3.99」タップ → Apple StoreKit ダイアログ → Face ID → 購入完了

RC Test Store フロー（テスト用）:
  ユーザー → 「Monthly $3.99」タップ → RC モーダル表示:
      [Simulate Success]  ← 購入成功シミュレート
      [Simulate Failure]  ← 購入失敗シミュレート
      [Cancel]            ← キャンセル
```

### 前提条件

| 条件 | 値 |
|------|-----|
| RC SDK | >= 5.43.0 |
| API Key | Test Store API Key（Debug）/ Platform Key（Release） |
| RC Dashboard | Test Store に products + offerings 登録済み |

### Maestro 決済成功テスト

```yaml
# maestro/04-payment-success.yaml
appId: com.aniccafactory.deskstretch
tags:
  - payment
  - smokeTest
---
- clearState
- clearKeychain
- launchApp
- extendedWaitUntil:
    visible:
      id: "onboarding_get_started"
    timeout: 30000
- tapOn:
    id: "onboarding_get_started"
- tapOn:
    id: "pain_area_neck"
- tapOn:
    id: "onboarding_continue"
- extendedWaitUntil:
    visible:
      id: "paywall_plan_monthly"
    timeout: 10000
- tapOn:
    id: "paywall_plan_monthly"
- extendedWaitUntil:
    visible: "Simulate Success"
    timeout: 10000
- tapOn: "Simulate Success"
- extendedWaitUntil:
    visible:
      id: "timer_ring"
    timeout: 10000
- takeScreenshot: "04-payment-success"
```

### Maestro 決済失敗テスト

```yaml
# maestro/05-payment-failure.yaml
appId: com.aniccafactory.deskstretch
tags:
  - payment
---
- clearState
- clearKeychain
- launchApp
- extendedWaitUntil:
    visible:
      id: "onboarding_get_started"
    timeout: 30000
- tapOn:
    id: "onboarding_get_started"
- tapOn:
    id: "pain_area_neck"
- tapOn:
    id: "onboarding_continue"
- extendedWaitUntil:
    visible:
      id: "paywall_plan_monthly"
    timeout: 10000
- tapOn:
    id: "paywall_plan_monthly"
- extendedWaitUntil:
    visible: "Simulate Failure"
    timeout: 10000
- tapOn: "Simulate Failure"
- extendedWaitUntil:
    visible:
      id: "paywall_plan_monthly"
    timeout: 5000
- takeScreenshot: "05-payment-failure"
```

---

## 6. Phase C: レシピ更新（学びの反映 — 34件 + 14件未解決）

**進捗:** 20/20 DONE。Fat→thin は Phase E に DEFERRED（冒頭「Phase C 進捗状況」参照）。

### 34件トレーサビリティ検証結果（ALL PASS）

| # | TODO | 検証先ファイル | 結果 |
|---|------|--------------|------|
| 1 | Skill references 複数→1 | SKILL.md US表 | PASS: 全US が 1スキル |
| 2 | 変数セクション追加 | us-006:7-15, us-007:9-15 | PASS |
| 3 | Gate 0 追加 | us-006:17-24, us-007:17-22 | PASS |
| 4 | build → fastlane build | us-006:137-138 | PASS |
| 5 | test → fastlane test | us-006:141 | PASS |
| 6 | all-test → maestro test maestro/ | us-007:73 | PASS |
| 7 | xcodegen generate | us-006:61-65 | PASS |
| 8 | Fastfile テンプレート | tdd-feature SKILL.md | PASS: スキルに Fastlane lanes 記載 |
| 9 | env vars | tdd-feature SKILL.md | PASS: スキルに env 設定記載 |
| 10 | TestTarget Info.plist | us-006:70 | PASS: GENERATE_INFOPLIST_FILE: YES |
| 11 | StoreKit Configuration 削除 | us-005b:296, us-007:61 | PASS: 禁止明記 |
| 12 | RC Test Store 手順 | us-005b:285-328 | PASS |
| 13 | Products.storekit 削除 | us-005b:296 | PASS |
| 14 | TDD→006統合 | us-006:1,59 | PASS: Title + Canon TDD |
| 15 | Unit/Int を実装中に | us-006:59 | PASS: RED→GREEN→REFACTOR |
| 16 | 実行順序 | us-006:28 | PASS: Models→Services→ViewModels→Integration |
| 17 | Swift Testing | tdd-feature SKILL.md:82-141 | PASS: @Test, #expect, @Suite |
| 18 | Parameterized tests | tdd-feature SKILL.md:385 | PASS |
| 19 | Coverage 80%+ | tdd-feature SKILL.md:406 | PASS |
| 20 | maestro/ ディレクトリ | us-007:59 | PASS |
| 21 | clearState+clearKeychain | us-007:42-43, 79-82 | PASS |
| 22 | extendedWaitUntil | us-007:45-48 | PASS: 30000ms |
| 23 | takeScreenshot | us-007:50, 84-87 | PASS |
| 24 | id: selectors | us-007:62, maestro SKILL.md | PASS |
| 25 | tags | us-007:26-33 | PASS |
| 26 | maestro test maestro/ | us-007:73 | PASS |
| 27 | CI timeout 30000ms | us-007:47, maestro SKILL.md | PASS |
| 28 | FoundationModels 削除 | us-004:72-73, 223, 396 | PASS: Rule 21 enforcement |
| 29 | Performance < 500ms | us-004: Rule 21 全体 | PASS: AI generation 自体を禁止 |
| 30 | テスト名 testGenerate | us-004: Rule 21 全体 | PASS: AI Service 自体を禁止 |
| 31 | code-quality-reviewer 独立 | SKILL.md US表, prd.json | PASS: 004-R, 006-R |
| 32 | Edge Case→Test mapping | us-004:58, 481 | PASS: Feature ID→Test 相互参照 |
| 33 | Mock grep 精度 | us-006:144 | PASS: grep -rw 'class Mock' |
| 34 | セッション分割 | SKILL.md, prd.json | PASS: 20エントリ |

### 更新対象ファイル

| # | ファイル | 更新内容 | 件数 |
|---|---------|---------|------|
| 1 | `references/us-004-specs.md` | フェーズ分割（004a/004b/004-R）、mau.md ルール、スキル: `implementation-spec` → `frontend-design` | 5件 |
| 2 | `references/us-006-implement.md` | TDD 統合、006a-d 分割、Fastlane 必須化、スキル: `ios-ux-design` のみ | 8件 |
| 3 | `references/us-007-testing.md` | E2E のみ（Unit/Integration は 006 完了）、Maestro BP、RC Test Store | 11件 |
| 4 | `references/us-005b-monetization.md` | StoreKit Configuration 削除、RC Test Store 手順追加 | 3件 |
| 5 | `validate.sh` | 新フェーズ構成に合わせたゲート更新 | 全面 |
| 6 | `SKILL.md` | スキル割り当てテーブル更新、Rule 21 強化 | 3件 |
| 7 | `CLAUDE.md` | セッション分割の反映 | 2件 |
| 8 | `prd.json` | US-004/006/007 の分割反映 | 構造変更 |
| 9 | `references/best-practices-audit.md` | DeskStretch 修正で発見した新パターン | 追記 |

### レシピ改善 TODO 詳細（34件）

#### Recipe Structure（3件）

| # | TODO | 現状 | 修正後 |
|---|------|------|--------|
| 1 | Skill references: 複数 → 1/phase | 4スキル参照 | 1フェーズ1スキル |
| 2 | 変数セクション追加 | `<AppName>`, `$UDID` 未定義 | `APP_SCHEME=DeskStretch`, UDID 自動取得 |
| 3 | 依存チェック（Gate 0）追加 | チェックなし | `find` でソースファイル存在確認 |

#### Build Tools → Fastlane（7件）

| # | TODO | 現状 | 修正後 |
|---|------|------|--------|
| 4 | Quality Gate build | `xcodebuild -scheme` | `xcodegen generate && fastlane build` |
| 5 | Step 2 test | `xcodebuild test` | `fastlane test` |
| 6 | Step 5 all-test | `xcodebuild test` + `maestro test flows/` | `fastlane test` + `maestro test maestro/` |
| 7 | xcodegen generate 追加 | 未記載 | Quality Gate 最初に追加 |
| 8 | Fastfile テンプレート追加 | なし | `test`, `build`, `build_for_simulator` lanes |
| 9 | env vars 追加 | `FASTLANE_OPT_OUT_CRASH_REPORTING` 欠落 | 全 Fastlane コマンドに追加 |
| 10 | TestTarget Info.plist | 未記載 | `GENERATE_INFOPLIST_FILE: YES` |

#### StoreKit → RC Test Store（3件）

| # | TODO | 現状 | 修正後 |
|---|------|------|--------|
| 11 | StoreKit Configuration 削除 | Step 3: Products.storekit | 完全削除。RC Test Store で代替 |
| 12 | RC Test Store 手順追加 | なし | Test Store API Key + 切り替え手順 |
| 13 | AC から Products.storekit 削除 | 存在チェック | 「RC Test Store purchase flow verified」 |

#### TDD → 実装フェーズ統合（6件）

| # | TODO | 現状 | 修正後 |
|---|------|------|--------|
| 14 | TDD を 006 に統合 | 007 で後付け | 006a-d 内で RED → GREEN → REFACTOR |
| 15 | Unit/Integration を実装中に書く | 別フェーズ | 各機能の実装直前に書く |
| 16 | 実行順序指定 | 順序なし | Models → Services → Integration |
| 17 | Swift Testing framework | 未記載 | `@Test`, `#expect`, `@Suite` 使用 |
| 18 | Parameterized tests | 未記載 | `@Test(arguments:)` で enum 反復 |
| 19 | Coverage check 追加 | カバレッジ要件なし | `fastlane test` + 80%+ 目標 |

#### Maestro E2E（8件）

| # | TODO | 現状 | 修正後 |
|---|------|------|--------|
| 20 | ディレクトリ名 | `flows/` | `maestro/` |
| 21 | clearState + clearKeychain | なし | 全フロー先頭に追加 |
| 22 | extendedWaitUntil | なし（即タップ） | 30000ms（起動）, 10000ms（画面遷移） |
| 23 | takeScreenshot | なし | 各フロー末尾に追加 |
| 24 | id: selectors only | text/id 混在 | `id:` 主、`text:` はシステムダイアログのみ |
| 25 | tags 追加 | なし | `smokeTest`, `onboarding`, `timer`, `paywall` |
| 26 | Maestro 実行方法 | `maestro test flows/` | `maestro test maestro/`（CLI） |
| 27 | CI timeout ガイダンス | なし | 30000ms タイムアウト推奨 |

#### Rule 21 修正（3件）

| # | TODO | 現状 | 修正後 |
|---|------|------|--------|
| 28 | Edge Case #7 | Foundation Models fallback | 削除。AI なし（Rule 21） |
| 29 | Performance: AI generation | `< 3s` | `< 500ms`（静的フィルタリング） |
| 30 | AIStretchService テスト名 | `testFallback*` | `testGenerate*` |

#### レビューゲート + その他（4件）

| # | TODO | 現状 | 修正後 |
|---|------|------|--------|
| 31 | code-quality-reviewer を独立フェーズに | codex-review（外部） | サブエージェント（内部）、004-R + 006-R |
| 32 | Edge Case → Test mapping | マッピングなし | Edge Case # → Test file + test name |
| 33 | Mock grep 精度 | `grep -r 'Mock'` | `grep -rw 'class Mock'` |
| 34 | セッション分割ドキュメント化 | 未定義フロー | 9 sessions with gates |

---

## 7. レビューゲート設計

ソース: [HubSpot Engineering](https://product.hubspot.com/blog/automated-code-review-the-6-month-evolution) / 核心の引用: 「Internal agent framework... reducing cycle time and ensuring high quality feedback as fast as possible.」

ソース: [Qodo - AI Code Review 2026](https://www.qodo.ai/blog/5-ai-code-review-pattern-predictions-in-2026/) / 核心の引用: 「Severity-Driven Review: Every finding gets assigned a severity level.」

### フェーズ内レビュー: code-quality-reviewer サブエージェント

| 観点 | Codex CLI（外部） | code-quality-reviewer（内部 — 採用） |
|------|-------------------|-------------------------------------|
| コンテキスト | 白紙スタート | CLAUDE.md + Serena メモリ参照 |
| レイテンシ | 高（外部プロセス） | **低（同一セッション）** |
| 反復回数 | 多い（コンテキスト不足） | **少ない（プロジェクト知識）** |
| Blocking 精度 | 低（汎用） | **高（カスタムルール）** |

### codex-review は存続

リリース前最終ゲート・大規模リファクタ時に使用。Phase B の各セッションでは使わない。

### レビュー発動ルール

| 変更規模 | レビュー | ブロッキング |
|---------|---------|-------------|
| 5行以下 | なし（テストのみ） | テスト PASS |
| 5〜50行 | 軽量チェック | テスト PASS |
| 50行〜 / 複数ファイル | **code-quality-reviewer** | CRITICAL=0 |
| 公開 API 変更 | **code-quality-reviewer（必須）** | CRITICAL=0 |
| セキュリティ / 決済コード | **人間レビュー（必須）** | 人間 OK |

---

## 8. Phase D: DeskStretch 完走（US-008a〜009）

| # | ステップ | 内容 |
|---|---------|------|
| 1 | US-008a〜008e | スクショ、メタデータ、ビルド、コンプライアンス、TestFlight |
| 2 | US-009 | App Privacy + App Store 提出 |
| 3 | 問題記録 | 新たな問題を best-practices-audit.md に追記 |

---

## 9. Phase E: 新アプリで検証

| # | ステップ | 内容 |
|---|---------|------|
| 1 | `ralph.sh` 実行 | 改善済みレシピで US-001〜009（20セッション）を1本通す |
| 2 | `validate.sh` 確認 | 全 US が passes: true |
| 3 | 問題記録 | 新たな問題を best-practices-audit.md に追記 |

---

## 10. Phase F: Cron テスト

| # | ステップ | 内容 |
|---|---------|------|
| 1 | cron 設定確認 | `mobileapp-factory-morning` 15:00 JST |
| 2 | 無人実行 | ralph.sh が全 US を自動走行 |
| 3 | Slack 報告確認 | #metrics に完了報告 |

---

## 11. OSS 計画 — `https://github.com/Daisuke134/mobileapp-builder`

### リポジトリ構成

```
mobileapp-builder/
├── SKILL.md                    ← エントリーポイント（npx skills add で配布）
├── CLAUDE.md                   ← CC セッション用テンプレート
├── ralph.sh                    ← Loop executor（1 US = 1 CC session）
├── validate.sh                 ← External quality gate
├── prd.json                    ← Backlog テンプレート
├── SETUP.md                    ← 初回セットアップ手順
├── README.md                   ← OSS ドキュメント
├── references/
│   ├── us-001-trend.md
│   ├── us-002-planning.md
│   ├── us-003-research.md
│   ├── us-004-specs.md
│   ├── us-005a-infra.md
│   ├── us-005b-monetization.md
│   ├── us-006-implement.md
│   ├── us-007-testing.md
│   ├── us-008-release.md
│   ├── us-009-submit.md
│   ├── best-practices-audit.md
│   └── submission-checklist.md
└── templates/
    ├── Fastfile
    ├── project.yml
    └── .env.example
```

### OSS 公開フロー

| # | ステップ | 内容 |
|---|---------|------|
| 1 | Phase A-E 完了 | DeskStretch + 新アプリで全レシピ検証済み |
| 2 | 秘密情報の除去 | Webhook URL, API Key, Slack Token → プレースホルダ |
| 3 | README.md 作成 | セットアップ手順、前提条件 |
| 4 | SETUP.md 更新 | `npx skills add Daisuke134/mobileapp-builder` |
| 5 | templates/ 作成 | Fastfile, project.yml, .env.example |
| 6 | GitHub Release | v1.0.0 タグ |
| 7 | skills.sh 登録 | `npx skills add` で配布可能に |

### 依存スキル（ユーザーが別途インストール）

| スキル | ソース |
|--------|--------|
| `ios-ux-design` | 自作 |
| `frontend-design` | Anthropic 公式 |
| `implementation-guide` | rshankras/claude-code-apple-skills |
| `maestro-e2e` | skills.sh |
| `asc-*` シリーズ | rshankras/claude-code-apple-skills |

---

## 12. オンボーディング設計ルール（mau.md — Prayer Lock $25k/月の実例）

| # | ルール | ソース引用 |
|---|--------|-----------|
| 1 | **3幕構成**: 問題提示 → アプリ体験 → Paywall | 「introduction → climax → conclusion」 |
| 2 | **質問 = ユーザーの自己説得** | 「the real purpose is to reflect on their own answers」 |
| 3 | **回答のミラーリング** | 「mirror the user's answers back to them」 |
| 4 | **長いほど変換率UP（価値がある限り）** | 「the longer, the better it converts」 |
| 5 | **コア機能を体験させる** | 「let the user actually use your core feature」 |
| 6 | **レビューモーダル = コア体験直後** | 「right after the user completes your core feature」 |
| 7 | **コミットメント原則** | 「actively state they are committed before paywall」 |
| 8 | **10%+ DL→Trial 変換率** | 「at least 10% download to trial conversion rate」 |

---

## 13. サマリー

| 項目 | 値 |
|------|-----|
| DeskStretch 問題数 | 21件（CRITICAL 1, HIGH 12, MEDIUM 8） |
| レシピ改善 TODO | 34件 + デザインスキル統合 + mau.md ルール |
| Phase A（SDD Spec） | 3セッション（004a, 004b, 004-R） |
| Phase B（TDD Fix） | 6セッション（006a, 006b, 006c, 006d, 006-R, 007） |
| Phase C（レシピ更新） | **20/20 DONE**。Fat→thin は Phase E に DEFERRED |
| Phase D（DeskStretch 完走） | US-008a〜009 |
| Phase E（新アプリ検証） | ralph.sh フル実行（20セッション） |
| Phase F（Cron） | 15:00 JST 自動実行 |
| **prd.json セッション数** | **20**（US-004: 3分割、US-006: 5分割） |
| **DeskStretch 固有セッション** | **9**（Phase A: 3 + Phase B: 6） |

| 変更 | 理由 | ソース |
|------|------|--------|
| TDD を 006 に統合 | TDD = 実装そのもの | Martin Fowler TDD |
| 007 を E2E のみに | Unit/Integration は 006 で完了 | Quash TDD Guide |
| レビューを独立フェーズに（004-R, 006-R） | 「explicit step in workflow」 | Martin Fowler RefinementCodeReview |
| 004a-R 削除 → 004-R に統合 | Spec は 004b 完了後にまとめてレビュー | Anthropic teams workflow |
| 1フェーズ = 1スキル | 複数スキル = 混乱 | Anthropic Skills Guide |
| codex-review は存続 | リリース前最終ゲート | — |
| prd.json 20分割 | ralph.sh が 1 US = 1 CC セッションで読む | ghuntley.com/ralph |
| Fix Loop 上限なし | 全フロー PASS まで繰り返す。3回で BLOCKED は間違い | — |
| レシピ = thin | 手順はスキルに。レシピは「スキル読め + 変数 + Gate」のみ | Anthropic Skills Guide |
