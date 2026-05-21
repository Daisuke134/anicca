# Test Specification: LymphaFlow

Source: [Apple Testing Guide](https://developer.apple.com/documentation/xcode/testing-your-apps-in-xcode) — 「Unit tests verify individual pieces of code. UI tests verify the complete user interface.」
Source: [Maestro Mobile Testing](https://maestro.mobile.dev/getting-started/writing-your-first-flow) — 「Maestro provides a simple, reliable way to write E2E mobile tests using YAML.」
Source: [Martin Fowler Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html) — 「Unit 70% / Service 20% / UI 10%.」

---

## 1. Test Strategy

```
         ┌──────────────┐
         │  E2E (10%)   │  Maestro YAML flows
         │  6+ flows    │
         ├──────────────┤
         │  Integration │  XCTest: Service→ViewModel 連携
         │  (20%)       │  15+ tests
         ├──────────────┤
         │  Unit (70%)  │  XCTest: Models + Services
         │  30+ tests   │
         └──────────────┘
```

| テスト種別 | ツール | 場所 | カバレッジ目標 |
|-----------|--------|------|-------------|
| Unit | XCTest | `LymphaFlowTests/Unit/` | 80%+ (Service + Model) |
| Integration | XCTest | `LymphaFlowTests/Integration/` | Service間連携 |
| E2E | Maestro | `maestro/` | 主要ユーザーフロー全件 |

**実行コマンド:**
```bash
cd LymphaFlowios && fastlane test          # Unit + Integration
maestro test maestro/                     # E2E（実機/シミュレータ）
```

---

## 2. Unit Tests

### SessionStore Tests (F-004)

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `testSaveAndLoadSession` | `SessionStore` | セッション保存 → UserDefaults → 読み込み往復 |
| `testStreakCountFirstDay` | `SessionStore` | 初回セッションでstreak=1 |
| `testStreakCountConsecutiveDays` | `SessionStore` | 連続2日でstreak=2 |
| `testStreakResetAfterMissedDay` | `SessionStore` | 2日空いてstreak=1にリセット |
| `testStreakSameDayDoesNotIncrement` | `SessionStore` | 同日2回でstreak変化なし |
| `testLoadSessionsEmptyInitially` | `SessionStore` | 初期状態は空配列 |
| `testClearAllSessions` | `SessionStore` | 全削除後に空配列 |

### SubscriptionService Tests (F-005)

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `testIsProDefaultFalse` | `MockSubscriptionService` | 初期状態 isPro=false |
| `testPurchaseSuccessSetsIsPro` | `MockSubscriptionService` | 購入成功 → isPro=true |
| `testRestorePurchasesSuccess` | `MockSubscriptionService` | 復元成功 → isPro=true |
| `testPurchaseFailureThrowsError` | `MockSubscriptionService` | 購入失敗 → Error throw |
| `testFetchOfferingsReturnsPackages` | `MockSubscriptionService` | Offerings に monthly + annual が含まれる |

### RoutineDataService Tests (F-001, F-002)

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `testLoadRoutinesNotEmpty` | `RoutineDataService` | routines.json デコード成功。件数>0 |
| `testFreeRoutinesCount` | `RoutineDataService` | Free ルーティン数 = 3（face/neck/collarbone）|
| `testProRoutinesCount` | `RoutineDataService` | Pro ルーティン数 ≥ 9 |
| `testRoutineHasSteps` | `RoutineDataService` | 全 Routine.steps.count > 0 |
| `testStepDurationRange` | `RoutineDataService` | 全 Step.durationSeconds in [15...120] |
| `testMorningProgramExists` | `RoutineDataService` | programType=.morning の Routine が存在 |
| `testEveningProgramExists` | `RoutineDataService` | programType=.evening の Routine が存在 |

### NotificationService Tests (F-007)

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `testScheduleMorningReminder` | `NotificationService` | identifier=`lf.reminder.morning` で登録される |
| `testScheduleEveningReminder` | `NotificationService` | identifier=`lf.reminder.evening` で登録される |
| `testCancelAllRemindersRemovesAll` | `NotificationService` | cancelAllReminders() 後に pending=0 |
| `testAuthorizationDeniedDoesNotCrash` | `NotificationService` | 通知拒否時も graceful degradation |

### TimerViewModel Tests (F-002)

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `testTimerStartDecrementsTime` | `TimerViewModel` | start() 後に timeRemaining 減少 |
| `testTimerPauseStopsDecrement` | `TimerViewModel` | pause() 後に timeRemaining 変化なし |
| `testTimerReachesZeroCallsCompletion` | `TimerViewModel` | timeRemaining=0 で onComplete 呼び出し |
| `testTimerProgressCalculation` | `TimerViewModel` | progress = 1 - (remaining/total) |

### Model Tests

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `testRoutineCodable` | `Routine` | encode → decode で同値 |
| `testStepCodable` | `Step` | encode → decode で同値 |
| `testSessionRecordCodable` | `SessionRecord` | encode → decode で同値 |
| `testProgramTypeRawValue` | `ProgramType` | `.morning.rawValue == "morning"` |

---

## 3. Integration Tests

Source: [Apple XCTest Integration Testing](https://developer.apple.com/documentation/xctest) — 「Integration tests verify that multiple components work together correctly.」

| Test Name | Components | What It Verifies |
|-----------|-----------|-----------------|
| `testSessionStoreAndStreakIntegration` | `SessionStore` + `HomeViewModel` | セッション保存 → ストリーク → HomeVM の streakCount 反映 |
| `testSubscriptionAndRoutineUnlock` | `MockSubscriptionService` + `HomeViewModel` | isPro=true → Pro ルーティンが表示される |
| `testNotificationAfterOnboarding` | `NotificationService` + `OnboardingViewModel` | onboarding完了 → 通知スケジュール登録 |
| `testTimerAndSessionCompletion` | `TimerViewModel` + `SessionStore` | セッション完了 → SessionRecord が SessionStore に保存 |
| `testPaywallTriggersOnProRoutineTap` | `HomeViewModel` + `SubscriptionServiceProtocol` | isPro=false + Pro Routine タップ → PaywallView 表示フラグ |
| `testRestorePurchasesUnlocksContent` | `MockSubscriptionService` + `SettingsViewModel` | restore成功 → isPro=true → Settings に Subscription Active 表示 |
| `testRoutineDataAndSessionHistory` | `RoutineDataService` + `SessionStore` | RoutineId でルーティン名取得 → SessionHistory に正しく表示 |

---

## 4. E2E Tests (Maestro)

Source: [Maestro YAML Spec](https://maestro.mobile.dev/api-reference/commands) — 「All interactions must use id: selectors, not coordinate-based point: selectors.」
Source: UX_SPEC.md §7 accessibilityIdentifier Table — 全 ID はこのテーブルから取得

**必須要件:**
- 全フローで `clearState: true`（独立性確保）
- 全フローで `takeScreenshot` を最低1回
- `id:` セレクター必須。`point:` 禁止
- `smokeTest` タグを2フロー以上に付与

### Maestro Flow Table

| ファイル | Scenario | Key Assertions | Tag |
|---------|---------|----------------|-----|
| `maestro/onboarding_to_paywall.yaml` | オンボーディング完了 → PaywallView 表示 | `paywall_view` が表示される | `smokeTest` |
| `maestro/paywall_maybe_later.yaml` | PaywallView → Maybe Later → HomeView | `home_view` が表示される | `smokeTest` |
| `maestro/free_routine_session.yaml` | Free ルーティン → セッション完了 → ストリーク更新 | `session_complete_view`、`streak_badge` |  |
| `maestro/payment_monthly.yaml` | PaywallView → Monthly 選択 → 購入（Sandbox） | `paywall_monthly_option` タップ、購入成功 |  |
| `maestro/payment_annual.yaml` | PaywallView → Annual 選択 → 7日Trial 開始 | `paywall_annual_option` タップ、Trial 開始 |  |
| `maestro/payment_failure.yaml` | 購入失敗 → エラーアラート表示 | エラーアラートが表示される |  |
| `maestro/settings_notification.yaml` | 設定 → 通知時刻変更 | `settings_morning_time` Picker 操作成功 |  |
| `maestro/progress_dashboard.yaml` | Progress タブ → ストリーク表示 → カレンダー確認 | `progress_view`、`streak_badge` |  |

### onboarding_to_paywall.yaml 構造例

```yaml
appId: com.aniccafactory.lymphaflow
tags:
  - smokeTest
---
- clearState: true
- launchApp:
    clearState: true
- assertVisible:
    id: "onboarding_page_1"
- takeScreenshot: "01_onboarding_start"
- tapOn:
    id: "onboarding_continue_btn"
- tapOn:
    id: "onboarding_continue_btn"
- tapOn:
    id: "onboarding_continue_btn"
- tapOn:
    id: "notification_skip_btn"
- assertVisible:
    id: "paywall_view"
- takeScreenshot: "02_paywall_visible"
```

---

## 5. Greenlight Checks

Source: [CLAUDE.md CRITICAL Rules] — mobileapp-builder ルールセット

| Rule | チェックコマンド | 合格条件 |
|------|----------------|---------|
| **Rule 17** (分析SDK禁止) | `grep -rE "$R17_PAT" LymphaFlowios/LymphaFlow/` | 0件 |
| **Rule 20** (RC公式UIライブラリ禁止) | `grep -r "$R20_PAT" LymphaFlowios/` | 0件 |
| **Rule 20** (Maybe Later必須) | `grep -r "maybe_later\|maybeLatr\|Maybe Later" LymphaFlowios/LymphaFlow/Views/Paywall/` | 1件以上 |
| **Rule 20b** (ATT禁止) | `grep -rE "$R20B_PAT" LymphaFlowios/` | 0件 |
| **Rule 21** (AI API禁止) | `grep -rE "$R21_PAT" LymphaFlowios/LymphaFlow/` | 0件 |
| **Greenlight CLI** | `greenlight preflight LymphaFlowios/` | CRITICAL=0 |

### 実行手順

```bash
export PATH="/opt/homebrew/bin:/Users/anicca/Library/Python/3.9/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export ASC_BYPASS_KEYCHAIN=true

# パターン変数（スペックファイル自身がマッチしないよう分割定義）
R17_PAT='Mix''panel|Ana''lytics|Fire''base'
R20_PAT='Revenue''CatUI'
R20B_PAT='ATTrack''ingManager|requestTracking''Authorization'
R21_PAT='Open''AI|Google''GenerativeAI|Foundation''Models'

# Rule 17
COUNT=$(grep -rE "$R17_PAT" LymphaFlowios/LymphaFlow/ 2>/dev/null | wc -l | tr -d ' ')
[ "$COUNT" -eq 0 ] && echo "PASS: Rule 17" || echo "FAIL: Rule 17 ($COUNT violations)"

# Rule 20
COUNT=$(grep -r "$R20_PAT" LymphaFlowios/ 2>/dev/null | wc -l | tr -d ' ')
[ "$COUNT" -eq 0 ] && echo "PASS: Rule 20 (no RC公式UIライブラリ)" || echo "FAIL: Rule 20 ($COUNT violations)"

# Rule 20b
COUNT=$(grep -rE "$R20B_PAT" LymphaFlowios/ 2>/dev/null | wc -l | tr -d ' ')
[ "$COUNT" -eq 0 ] && echo "PASS: Rule 20b" || echo "FAIL: Rule 20b ($COUNT violations)"

# Rule 21
COUNT=$(grep -rE "$R21_PAT" LymphaFlowios/LymphaFlow/ 2>/dev/null | wc -l | tr -d ' ')
[ "$COUNT" -eq 0 ] && echo "PASS: Rule 21" || echo "FAIL: Rule 21 ($COUNT violations)"

# Greenlight
greenlight preflight LymphaFlowios/
```

---

## 6. Performance Targets

Source: [Apple Performance Guidelines](https://developer.apple.com/documentation/xcode/improving-your-app-s-performance) — 「Cold launch under 400ms is a key user experience metric.」

| 指標 | 目標 | 測定方法 |
|------|------|---------|
| Cold Launch | < 2.0秒 | Xcode Instruments Time Profiler |
| Memory (Idle) | < 60MB | Xcode Memory Graph |
| Memory (Session) | < 100MB | セッション中の最大メモリ |
| Battery (Background timer) | Background Task のみ | BGTaskScheduler |
| Frame Rate (Animations) | 60fps 維持 | Xcode Core Animation FPS |
| routines.json decode | < 50ms | XCTest measure {} |

---

## 7. Test Commands

```bash
export PATH="/opt/homebrew/bin:/Users/anicca/Library/Python/3.9/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export ASC_BYPASS_KEYCHAIN=true

# Unit + Integration
cd LymphaFlowios && fastlane test

# E2E（全フロー）
maestro test maestro/

# E2E（smokeTest のみ）
maestro test --tags smokeTest maestro/

# 特定フロー
maestro test maestro/onboarding_to_paywall.yaml

# Greenlight
greenlight preflight LymphaFlowios/

# テストカバレッジレポート
cd LymphaFlowios && fastlane test coverage:true
```
