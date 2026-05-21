# Test Specification: Zone2Daily

Source: [Apple WWDC 2023 — Testing in Xcode](https://developer.apple.com/videos/play/wwdc2023/10177/) — 「Organize tests into a pyramid: unit tests at the base, integration tests in the middle, UI tests at the top.」
Source: [Maestro Mobile Testing](https://maestro.mobile.dev/) — 「Use accessibilityIdentifier selectors for reliable E2E tests.」
Source: [Swift Testing Documentation](https://developer.apple.com/documentation/testing) — 「Swift Testing replaces XCTest with a modern, expressive API.」

---

## 1. Test Strategy

```
          ┌─────────────────┐
          │  E2E (Maestro)  │  ← 10%: 6 flows (onboarding, workout, paywall)
          │    6 YAML flows │
          └────────┬────────┘
         ┌─────────┴─────────┐
         │  Integration Tests │  ← 20%: Service layer integration
         │  (XCTest / Swift) │
         └────────┬──────────┘
    ┌─────────────┴──────────────┐
    │         Unit Tests         │  ← 70%: Models + Services + ViewModels
    │   (XCTest / Swift Testing) │
    └────────────────────────────┘
```

| 種別 | 目標数 | ファイル場所 | フレームワーク |
|------|--------|------------|-------------|
| Unit | 35+ | `Zone2DailyTests/Unit/` | Swift Testing (`@Test`) |
| Integration | 10+ | `Zone2DailyTests/Integration/` | XCTest |
| E2E | 6+ | `maestro/` | Maestro YAML |

---

## 2. Unit Tests

### Zone2Calculator Tests

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `test_zone2MaxHR_age35_returns145` | `Zone2Calculator` | 180 - 35 = 145 |
| `test_zone2MaxHR_age0_returns180` | `Zone2Calculator` | 境界値: age=0 → 180 |
| `test_zone2MaxHR_age80_returns100` | `Zone2Calculator` | 境界値: age=80 → 100 |
| `test_zone2MinHR_is10BelowMax` | `Zone2Calculator` | zone2MinHR = zone2MaxHR - 10 |
| `test_zone2Range_containsMaxHR` | `Zone2Calculator` | range.contains(zone2MaxHR) == true |
| `test_zone2Range_age40_is130to140` | `Zone2Calculator` | 40歳: 130...140 |

### WorkoutSession Model Tests

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `test_zone2Minutes_calculation` | `WorkoutSession` | zone2Seconds / 60.0 の正確な変換 |
| `test_zone2Percentage_normalCase` | `WorkoutSession` | zone2Seconds / durationSeconds × 100 |
| `test_zone2Percentage_zeroDuration_returns0` | `WorkoutSession` | ゼロ除算ガード |
| `test_zone2Percentage_fullZone2_returns100` | `WorkoutSession` | zone2 = duration → 100% |
| `test_workoutSession_defaultsCorrect` | `WorkoutSession` | id が UUID、date が今日 |

### UserProfile Model Tests

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `test_zone2MaxHR_matchesCalculator` | `UserProfile` | profile.zone2MaxHR == Zone2Calculator.zone2MaxHR(age:) |
| `test_weeklyGoalDefault_is150` | `UserProfile` | weeklyGoalMinutes のデフォルト = 150 |
| `test_zone2MinHR_is10BelowMax` | `UserProfile` | zone2MinHR = zone2MaxHR - 10 |
| `test_userProfile_ageValidation_10to80` | `UserProfile` | 有効範囲チェック |

### SubscriptionService (Protocol + Mock) Tests

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `test_isPremium_defaultsFalse` | `MockSubscriptionService` | 初期値は false |
| `test_purchase_setsIsPremium` | `MockSubscriptionService` | purchase() 成功 → isPremium = true |
| `test_restorePurchases_setsIsPremium` | `MockSubscriptionService` | restore() → isPremium = true |
| `test_fetchOfferings_returnsPackages` | `MockSubscriptionService` | offerings が空でないこと |
| `test_purchase_failure_doesNotSetPremium` | `MockSubscriptionService` | エラー時に isPremium = false のまま |

### OnboardingViewModel Tests

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `test_initialAge_is35` | `OnboardingViewModel` | デフォルト年齢 = 35 |
| `test_zone2HR_updatesWithAge` | `OnboardingViewModel` | age 変更 → zone2MaxHR 更新 |
| `test_completeOnboarding_setsUserDefaults` | `OnboardingViewModel` | hasCompletedOnboarding = true |
| `test_saveUserProfile_persistsToSwiftData` | `OnboardingViewModel` | SwiftData に UserProfile 保存 |
| `test_notificationGranted_setsFlag` | `OnboardingViewModel` | permission granted → notificationsEnabled = true |

### WorkoutViewModel Tests

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `test_timer_incrementsEverySecond` | `WorkoutViewModel` | 1秒後に durationSeconds += 1 |
| `test_stopWorkout_savesSession` | `WorkoutViewModel` | stopWorkout() → SwiftData に WorkoutSession 保存 |
| `test_zone2Minutes_calculatedCorrectly` | `WorkoutViewModel` | zone2Minutes = input × 60 |
| `test_freeTier_limitAt3Workouts` | `WorkoutViewModel` | 4件目で canLogWorkout = false |
| `test_premiumUser_unlimitedWorkouts` | `WorkoutViewModel` | isPremium = true → 制限なし |

### DashboardViewModel Tests

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `test_weeklyZone2Minutes_sumsCurrent7Days` | `DashboardViewModel` | 過去7日間の合計分数 |
| `test_progressPercentage_isZoneMinutesOverGoal` | `DashboardViewModel` | weeklyMinutes / weeklyGoal |
| `test_streak_incrementsOnDailyWorkout` | `DashboardViewModel` | 連続日数カウント |
| `test_streak_resetsOnMissedDay` | `DashboardViewModel` | 1日スキップ → streak = 0 |
| `test_todayCompleted_whenWorkoutExistsToday` | `DashboardViewModel` | 今日のワークアウット存在 → todayCompleted = true |

### NotificationService Tests

| Test Name | Target | What It Verifies |
|-----------|--------|-----------------|
| `test_scheduleDailyReminder_addsRequest` | `NotificationService` | UNNotificationRequest が追加される |
| `test_dailyReminder_identifier_isCorrect` | `NotificationService` | identifier = "zone2daily.morning" |
| `test_scheduleDailyReminder_repeats` | `NotificationService` | trigger.repeats == true |

---

## 3. Integration Tests

### SwiftData Integration

| Test Name | What It Verifies |
|-----------|-----------------|
| `test_workoutSession_savesAndFetches` | SwiftData: 保存 → 取得の往復テスト |
| `test_userProfile_updatesPersists` | SwiftData: age 更新が永続化される |
| `test_freeTierQuery_returns3Max` | SwiftData: `#Predicate` で直近7日間3件制限クエリ |
| `test_weeklyAggregation_query` | SwiftData: 週間合計の集計クエリ |
| `test_swiftData_deletesWorkout` | SwiftData: ワークアウット削除が反映される |

### SubscriptionService + OnboardingViewModel Integration

| Test Name | What It Verifies |
|-----------|-----------------|
| `test_paywallView_showsAfterOnboarding` | オンボーディング完了直後に Paywall 表示 |
| `test_premiumPurchase_unlocksDashboard` | 購入完了 → Premium 機能アクセス可 |
| `test_restorePurchases_setsCorrectState` | restore → isPremium = true + UI 更新 |
| `test_freeTierLimit_triggerPaywall` | 無料ユーザーが4件目でPaywall .sheet 表示 |
| `test_dashboardUpdate_afterWorkoutSave` | ワークアウット保存後 DashboardViewModel が更新 |

---

## 4. E2E Tests (Maestro)

全フローは `maestro/` ディレクトリに YAML 形式で配置。

| File | Scenario | Key Assertions | Tag |
|------|----------|---------------|-----|
| `01_onboarding.yaml` | 新規ユーザーオンボーディング完全フロー | `label_zone2_hr` 表示 → `btn_continue_age` → `btn_maybe_later` → Dashboard 遷移 | `smokeTest` |
| `02_workout_complete.yaml` | ワークアウット記録（開始→停止→保存） | `btn_start_workout` → `btn_stop_workout` → `input_zone2_minutes` 入力 → `btn_save_workout` → Dashboard 更新 | `smokeTest` |
| `03_paywall_monthly.yaml` | 月額購入フロー | `btn_upgrade` → `selector_plan_monthly` → `btn_subscribe` → Premium UI 表示 | — |
| `04_paywall_annual.yaml` | 年額購入フロー | `btn_upgrade` → `selector_plan_annual` → `btn_subscribe` → Premium UI 表示 | — |
| `05_paywall_failure.yaml` | 購入キャンセル / エラー | `btn_subscribe` → キャンセル → Free tier 継続 → `btn_maybe_later` | — |
| `06_settings.yaml` | 設定変更フロー | `tab_settings` → `input_age_settings` 変更 → `toggle_notifications` → Dashboard HR 更新確認 | — |

### Maestro YAML 共通テンプレート

```yaml
# maestro/01_onboarding.yaml
appId: com.aniccafactory.zone2daily
tags:
  - smokeTest
---
- clearState: true
- launchApp:
    clearState: true
- assertVisible:
    id: "slider_age"
- tapOn:
    id: "btn_continue_age"
- assertVisible:
    id: "btn_continue_explainer"
- tapOn:
    id: "btn_continue_explainer"
- assertVisible:
    id: "btn_skip_notifications"
- tapOn:
    id: "btn_skip_notifications"
- assertVisible:
    id: "btn_maybe_later"
- tapOn:
    id: "btn_maybe_later"
- assertVisible:
    id: "tab_dashboard"
- takeScreenshot: "onboarding_complete"
```

**🔴 禁止: `point:` セレクター使用禁止。必ず `id:` セレクターを使用すること。**

---

## 5. Greenlight Checks

**🔴 Rule 17 — tracking SDK 禁止**

```bash
# tracking SDK (Rule 17) が混入していないか
# 検索パターン: サードパーティ analytics / crash reporting SDK の import
ANALYTICS=$(grep -rE "import (Amplitude|AppsFlyer)" Zone2Daily/ --include="*.swift" | grep -v "//")
[ -z "$ANALYTICS" ] && echo "PASS: Rule 17 (no tracking SDK)" || echo "FAIL: tracking SDK found: $ANALYTICS"
```

**🔴 Rule 20 — RC UI extension 禁止（自前 PaywallView 必須）**

```bash
# RevenueCatUI import が混入していないか（Rule 20: RevenueCat SDK のみ許可）
RCUI=$(grep -r "import RevenueCatUI" Zone2Daily/ --include="*.swift")
[ -z "$RCUI" ] && echo "PASS: Rule 20 (no RevenueCatUI)" || echo "FAIL: RevenueCatUI found: $RCUI"

# Mock が本番コードに混入していないか（Tests/ 除外）
MOCK=$(grep -rw "class Mock" Zone2Daily/ --include="*.swift" | grep -v Tests)
[ -z "$MOCK" ] && echo "PASS: no Mock in production" || echo "FAIL: Mock in production: $MOCK"
```

**🔴 Rule 20b — tracking permission dialog 禁止**

```bash
# tracking 許可ダイアログ (Rule 20b) が使用されていないか
ATT=$(grep -r "NSUserTrackingUsageDescription" Zone2Daily/ --include="*.swift" Zone2Daily/Info.plist)
[ -z "$ATT" ] && echo "PASS: Rule 20b (no tracking dialog)" || echo "FAIL: tracking dialog found: $ATT"
```

**🔴 Rule 21 — AI API / AI モデル 完全禁止**

```bash
# AI completion API / on-device LLM (Rule 21) が含まれていないか
# 検索パターン: AI SDK import / ChatCompletion / on-device ML
AI=$(grep -rE "import (CoreML|CreateML|NaturalLanguage)" Zone2Daily/ --include="*.swift")
[ -z "$AI" ] && echo "PASS: Rule 21 (no AI API)" || echo "FAIL: AI API found: $AI"
```

**HealthKit / CloudKit 禁止（追加チェック）**

```bash
HK=$(grep -r "import HealthKit\|import CloudKit" Zone2Daily/ --include="*.swift")
[ -z "$HK" ] && echo "PASS: no HealthKit/CloudKit" || echo "FAIL: found: $HK"
```

---

## 6. Performance Targets

| 指標 | 目標値 | 測定方法 |
|------|--------|---------|
| Cold Start Time | < 1.5秒 | Xcode Instruments: Time Profiler |
| Dashboard Render | < 0.3秒 | Xcode Instruments: Core Animation |
| SwiftData Query (7日間) | < 50ms | `clock()` ベンチマーク |
| Memory (Dashboard) | < 60MB | Xcode Memory Graph |
| Battery (1時間使用) | < 5% | Xcode Energy Organizer |
| Unit Test Suite | < 30秒 | `fastlane test` 計測 |

---

## 7. Test Commands

| タスク | コマンド | 合格基準 |
|--------|---------|---------|
| Unit + Integration テスト | `cd zone2dailyios && fastlane test` | 全テスト PASS、Coverage ≥ 70% |
| E2E（全フロー） | `maestro test maestro/` | 6/6 flows PASS |
| E2E（スモークテストのみ） | `maestro test maestro/ --include-tags smokeTest` | 2/2 flows PASS |
| Greenlight（Rule チェック） | `greenlight preflight Zone2DailyApp/` | CRITICAL = 0 |
| 型チェック | `cd zone2dailyios && fastlane build` | Build SUCCESS / Warnings 0 |

### Test Configuration

| 設定 | 値 |
|------|-----|
| Simulator | iPhone 16 Pro (iOS 18.x) |
| Locale (en-US) | `en_US` |
| Locale (ja) | `ja_JP` |
| Test Target | `Zone2DailyTests` |
| Coverage 報告 | Xcode → Report Navigator → Coverage |

Source: [Fastlane scan](https://docs.fastlane.tools/actions/scan/) — 「Use fastlane scan to run Xcode tests in CI.」
