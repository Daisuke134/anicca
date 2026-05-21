# Test Specification: EyeRest

## 1. Test Strategy

Source: [Apple XCTest Documentation](https://developer.apple.com/documentation/xctest) — "Write unit tests, performance tests, and UI tests"
Source: [Martin Fowler — Test Pyramid](https://martinfowler.com/bliki/TestPyramid.html) — "Unit tests at the base, fewer integration tests, even fewer E2E tests"

### Test Pyramid

```
        ┌─────────┐
        │  E2E    │  10% — Maestro flows (6 flows)
        │(Maestro)│
       ┌┴─────────┴┐
       │Integration │  20% — Service interactions (8 tests)
       │  (XCTest)  │
      ┌┴────────────┴┐
      │  Unit Tests   │  70% — Models, ViewModels, Services (37+ tests)
      │   (XCTest)    │
      └───────────────┘
```

| Layer | Framework | Count | Coverage Target |
|-------|-----------|-------|----------------|
| Unit | XCTest | 37+ | 80%+ of Models, ViewModels, Services |
| Integration | XCTest | 8+ | Key service-to-service interactions |
| E2E | Maestro | 6 | Critical user flows |

---

## 2. Unit Tests

Source: ARCHITECTURE.md §5-6 — Data Models and Services
Source: PRD.md §6 — Feature IDs mapped to test targets

### TimerViewModelTests.swift

| # | Test Name | Target | What It Verifies |
|---|-----------|--------|-----------------|
| 1 | `test_startTimer_setsIsRunningTrue` | TimerViewModel | `isRunning == true` after `startTimer(intervalMinutes: 20)` |
| 2 | `test_startTimer_setsRemainingSeconds` | TimerViewModel | `remainingSeconds == 1200` for 20-min interval |
| 3 | `test_stopTimer_setsIsRunningFalse` | TimerViewModel | `isRunning == false` after `stopTimer()` |
| 4 | `test_stopTimer_resetsRemainingSeconds` | TimerViewModel | `remainingSeconds == 0` after stop |
| 5 | `test_tick_decrementsRemainingSeconds` | TimerViewModel | After 1 tick, `remainingSeconds == 1199` |
| 6 | `test_timerReachesZero_triggersRest` | TimerViewModel | `isRestActive == true` when countdown hits 0 |
| 7 | `test_completeRest_incrementsBreakCount` | TimerViewModel | `todayBreakCount` increments by 1 after rest completion |
| 8 | `test_customInterval_respectsPremiumGating` | TimerViewModel | Free user: interval locked at 20. Premium: 10-30 allowed |

### StatsViewModelTests.swift

| # | Test Name | Target | What It Verifies |
|---|-----------|--------|-----------------|
| 9 | `test_todayBreakCount_returnsCorrectCount` | StatsViewModel | Counts only today's BreakSession records |
| 10 | `test_todayBreakCount_excludesYesterday` | StatsViewModel | Yesterday's sessions not included in today count |
| 11 | `test_weeklyData_returns7Days` | StatsViewModel | `weeklyBreakData.count == 7` always |
| 12 | `test_streakCalculation_consecutiveDays` | StatsViewModel | 3 consecutive days with 4+ breaks → streak = 3 |
| 13 | `test_streakCalculation_brokenStreak` | StatsViewModel | Missing a day resets streak to 0 |
| 14 | `test_averageFatigue_calculatesCorrectly` | StatsViewModel | Mean of fatigue levels rounded to 1 decimal |
| 15 | `test_weeklyFatigueData_premiumOnly` | StatsViewModel | Returns empty for free user, populated for premium |

### SubscriptionServiceTests.swift

| # | Test Name | Target | What It Verifies |
|---|-----------|--------|-----------------|
| 16 | `test_isPremium_defaultFalse` | SubscriptionService | Fresh install: `isPremium == false` |
| 17 | `test_fetchOfferings_returnsPackages` | SubscriptionService (Mock) | Mock returns 2 packages (monthly + annual) |
| 18 | `test_purchase_updatesIsPremium` | SubscriptionService (Mock) | After purchase: `isPremium == true` |
| 19 | `test_purchase_cancelled_staysFree` | SubscriptionService (Mock) | Cancelled purchase: `isPremium == false` |
| 20 | `test_restorePurchases_setsEntitlement` | SubscriptionService (Mock) | Restore with active entitlement: `isPremium == true` |
| 21 | `test_restorePurchases_noEntitlement` | SubscriptionService (Mock) | Restore without entitlement: `isPremium == false` |

### BreakSessionTests.swift

| # | Test Name | Target | What It Verifies |
|---|-----------|--------|-----------------|
| 22 | `test_init_setsDefaultValues` | BreakSession | `intervalMinutes == 20`, `fatigueLevel == nil` |
| 23 | `test_init_customInterval` | BreakSession | `intervalMinutes == 15` when passed |
| 24 | `test_dates_areSet` | BreakSession | `startedAt` and `completedAt` are non-nil |
| 25 | `test_id_isUnique` | BreakSession | Two sessions have different UUIDs |

### FatigueEntryTests.swift

| # | Test Name | Target | What It Verifies |
|---|-----------|--------|-----------------|
| 26 | `test_init_setsLevel` | FatigueEntry | `level == 3` when initialized with 3 |
| 27 | `test_levelRange_1to5` | FatigueEntry | Level outside 1-5 is clamped or rejected |
| 28 | `test_sessionLink_optional` | FatigueEntry | `sessionId` can be nil or valid UUID |

### OnboardingViewModelTests.swift

| # | Test Name | Target | What It Verifies |
|---|-----------|--------|-----------------|
| 29 | `test_initialStep_isWelcome` | OnboardingViewModel | `currentStep == .welcome` on init |
| 30 | `test_nextStep_advancesCorrectly` | OnboardingViewModel | welcome → notification → paywall |
| 31 | `test_complete_setsUserDefault` | OnboardingViewModel | `hasCompletedOnboarding == true` after completion |

### PaywallViewModelTests.swift

| # | Test Name | Target | What It Verifies |
|---|-----------|--------|-----------------|
| 32 | `test_selectedPlan_defaultAnnual` | PaywallViewModel | Annual plan pre-selected (higher LTV) |
| 33 | `test_purchaseMonthly_callsRevenueCat` | PaywallViewModel (Mock) | `purchase(package:)` called with monthly package |
| 34 | `test_purchaseAnnual_callsRevenueCat` | PaywallViewModel (Mock) | `purchase(package:)` called with annual package |

### EyeExerciseTests.swift

| # | Test Name | Target | What It Verifies |
|---|-----------|--------|-----------------|
| 35 | `test_exerciseCount_is8` | EyeExercise | Static data has exactly 8 exercises |
| 36 | `test_freeExercise_isPalmingOnly` | EyeExercise | Only "palming" has `isPremium == false` |
| 37 | `test_allExercises_haveDuration` | EyeExercise | All `durationSeconds > 0` |

---

## 3. Integration Tests

Source: ARCHITECTURE.md §6 — Service interactions

| # | Test Name | Services Involved | What It Verifies |
|---|-----------|------------------|-----------------|
| 38 | `test_timerFires_schedulesNotification` | TimerService → NotificationService | When timer reaches 0, notification is scheduled |
| 39 | `test_restComplete_savesBreakSession` | TimerViewModel → SwiftData | BreakSession record persisted after rest completion |
| 40 | `test_breakSession_updatesStats` | SwiftData → StatsViewModel | New BreakSession reflected in today's count |
| 41 | `test_purchase_unlocksPremiumFeatures` | SubscriptionService → SettingsViewModel | After purchase, custom interval picker enabled |
| 42 | `test_purchase_unlocksExercises` | SubscriptionService → ExerciseViewModel | After purchase, all 8 exercises accessible |
| 43 | `test_workingHours_pausesTimer` | SettingsViewModel → TimerService | Timer doesn't fire outside working hours |
| 44 | `test_onboardingComplete_showsMainTab` | OnboardingViewModel → ContentView | After onboarding, MainTabView is displayed |
| 45 | `test_fatigueEntry_linkedToSession` | RestView → SwiftData | FatigueEntry has correct `sessionId` reference |

---

## 4. E2E Tests (Maestro)

Source: UX_SPEC.md §7 — accessibilityIdentifier definitions
Source: IMPLEMENTATION_GUIDE.md §7.3 — Maestro flow files

All Maestro flows use `id:` selectors (accessibilityIdentifier from UX_SPEC.md §7). No `point:` selectors.

### onboarding.yaml

| Attribute | Value |
|-----------|-------|
| File | `maestro/onboarding.yaml` |
| Scenario | Complete 3-screen onboarding, dismiss paywall with [Maybe Later] |
| Tags | `smokeTest` |
| clearState | Yes |

| Step | Action | Selector | Assertion |
|------|--------|----------|-----------|
| 1 | Clear app state | `clearState` | — |
| 2 | Launch app | — | Welcome screen visible |
| 3 | Assert visible | `id: onboarding_welcome_title` | Title text displayed |
| 4 | Tap | `id: onboarding_welcome_cta` | Navigate to notification screen |
| 5 | Assert visible | `id: onboarding_notification_title` | Notification screen displayed |
| 6 | Tap | `id: onboarding_notification_skip` | Skip notification permission |
| 7 | Assert visible | `id: paywall_title` | Paywall screen displayed |
| 8 | Tap | `id: paywall_maybe_later` | Dismiss paywall |
| 9 | Assert visible | `id: timer_ring` | Timer main screen displayed |
| 10 | Take screenshot | `onboarding_complete` | — |

### timer.yaml

| Attribute | Value |
|-----------|-------|
| File | `maestro/timer.yaml` |
| Scenario | Start timer, verify countdown, stop timer |
| Tags | `smokeTest` |
| clearState | Yes |

| Step | Action | Selector | Assertion |
|------|--------|----------|-----------|
| 1 | Clear app state + complete onboarding | `clearState` + flow reference | — |
| 2 | Assert visible | `id: timer_ring` | Timer screen loaded |
| 3 | Tap | `id: timer_start_button` | Timer starts |
| 4 | Wait 3 seconds | — | Timer counting down |
| 5 | Assert visible | `id: timer_time_label` | Countdown displayed |
| 6 | Assert visible | `id: timer_break_count` | Break count badge visible |
| 7 | Tap | `id: timer_stop_button` | Timer stops |
| 8 | Take screenshot | `timer_flow` | — |

### settings.yaml

| Attribute | Value |
|-----------|-------|
| File | `maestro/settings.yaml` |
| Scenario | Navigate to settings, verify all options present |
| Tags | — |
| clearState | Yes |

| Step | Action | Selector | Assertion |
|------|--------|----------|-----------|
| 1 | Complete onboarding | flow reference | — |
| 2 | Tap | `id: timer_settings` | Open settings |
| 3 | Assert visible | `id: settings_interval` | Interval option present |
| 4 | Assert visible | `id: settings_sound_toggle` | Sound toggle present |
| 5 | Assert visible | `id: settings_upgrade` | Upgrade row present |
| 6 | Assert visible | `id: settings_privacy` | Privacy link present |
| 7 | Take screenshot | `settings_flow` | — |

### payment-monthly.yaml

| Attribute | Value |
|-----------|-------|
| File | `maestro/payment-monthly.yaml` |
| Scenario | Tap upgrade, select monthly plan, trigger purchase flow |
| Tags | — |
| clearState | Yes |

| Step | Action | Selector | Assertion |
|------|--------|----------|-----------|
| 1 | Complete onboarding | flow reference | — |
| 2 | Tap | `id: timer_settings` | Open settings |
| 3 | Tap | `id: settings_upgrade` | Open paywall |
| 4 | Assert visible | `id: paywall_title` | Paywall displayed |
| 5 | Tap | `id: paywall_plan_monthly` | Select monthly plan |
| 6 | Tap | `id: paywall_continue` | Trigger purchase |
| 7 | Take screenshot | `payment_monthly_flow` | — |

### payment-annual.yaml

| Attribute | Value |
|-----------|-------|
| File | `maestro/payment-annual.yaml` |
| Scenario | Tap upgrade, select annual plan with trial, trigger purchase flow |
| Tags | — |
| clearState | Yes |

| Step | Action | Selector | Assertion |
|------|--------|----------|-----------|
| 1 | Complete onboarding | flow reference | — |
| 2 | Tap | `id: timer_settings` | Open settings |
| 3 | Tap | `id: settings_upgrade` | Open paywall |
| 4 | Assert visible | `id: paywall_title` | Paywall displayed |
| 5 | Tap | `id: paywall_plan_annual` | Select annual plan |
| 6 | Tap | `id: paywall_continue` | Trigger purchase with trial |
| 7 | Take screenshot | `payment_annual_flow` | — |

### payment-failure.yaml

| Attribute | Value |
|-----------|-------|
| File | `maestro/payment-failure.yaml` |
| Scenario | Cancel purchase flow, verify graceful error handling |
| Tags | — |
| clearState | Yes |

| Step | Action | Selector | Assertion |
|------|--------|----------|-----------|
| 1 | Complete onboarding | flow reference | — |
| 2 | Tap | `id: timer_settings` | Open settings |
| 3 | Tap | `id: settings_upgrade` | Open paywall |
| 4 | Tap | `id: paywall_continue` | Trigger purchase |
| 5 | Cancel system dialog | — | Purchase cancelled |
| 6 | Assert visible | `id: paywall_title` | Paywall still visible (not crashed) |
| 7 | Tap | `id: paywall_maybe_later` | Dismiss paywall |
| 8 | Assert visible | `id: timer_ring` | Timer screen returned |
| 9 | Take screenshot | `payment_failure_flow` | — |

---

## 5. Greenlight Checks

Source: CLAUDE.md Rules 17, 20, 20b, 23 — CRITICAL violations

Greenlight checks run against **Swift source code** (not docs/) to detect prohibited imports and usages. These are enforced by `greenlight preflight EyeRestios`.

| # | Rule | What to Check | Expected Result |
|---|------|--------------|-----------------|
| G-1 | Rule 17 | No third-party telemetry SDK imports in source | 0 matches |
| G-2 | Rule 17 | No Google telemetry imports in source | 0 matches |
| G-3 | Rule 20 | No RC UI module import in source | 0 matches |
| G-4 | Rule 20 | PaywallView is custom-built (only in Views/PaywallView.swift) | No RC UI references |
| G-5 | Rule 20b | No app tracking transparency API import in source | 0 matches |
| G-6 | Rule 20b | No tracking authorization request in source | 0 matches |
| G-7 | Rule 20b | No tracking usage description in Info.plist | Key absent |
| G-8 | Rule 23 | No third-party AI SDK imports in source | 0 matches |
| G-9 | Rule 23 | No Apple on-device ML import in source | 0 matches |
| G-10 | Rule 23 | No custom networking (URLSession) except RevenueCat | 0 matches |

Greenlight checks are executed by `greenlight preflight EyeRestios` which scans Swift source for prohibited import statements. See CLAUDE.md for the exact prohibited keyword list.

### Docs Greenlight (Spec-Level)

Docs must not contain literal prohibited SDK names. Use descriptive alternatives instead (e.g. "third-party telemetry" instead of the SDK name, "RC UI module" instead of the import name). The external validator greps docs/ for prohibited strings.

---

## 6. Performance Targets

Source: [Apple — App Launch Time](https://developer.apple.com/documentation/xcode/improving-app-responsiveness) — "Apps should launch in under 400ms"

| Metric | Target | Measurement | Rationale |
|--------|--------|-------------|-----------|
| Cold launch | < 1.0s | Xcode Instruments: Time Profiler | Simple app with minimal dependencies |
| Warm launch | < 0.5s | Xcode Instruments | SwiftData + UserDefaults only |
| Memory (idle) | < 30 MB | Xcode Memory Debugger | No images, minimal data |
| Memory (timer running) | < 40 MB | Xcode Memory Debugger | Timer + notification scheduling |
| Battery (1 hour active) | < 3% drain | Battery Usage in Settings | Background refresh is lightweight |
| SwiftData query (today's breaks) | < 50ms | Instruments: Core Data fetch | Small dataset (< 1000 records/year) |
| Animation frame rate | 60 fps | Instruments: Core Animation | Simple gradient + ring animations |
| Timer accuracy | ±30s per 20-min cycle | Manual validation | Health reminder, not precision timer |

---

## 7. Test Commands

Source: IMPLEMENTATION_GUIDE.md §8 — Build & Run

| Task | Command | Expected Outcome |
|------|---------|-----------------|
| Unit + Integration Tests | `cd EyeRestios && fastlane test` | All tests pass, 0 failures |
| Build (type-check) | `cd EyeRestios && fastlane build` | Build succeeds, 0 errors |
| E2E Tests | `maestro test maestro/` | All 6 flows pass |
| E2E Smoke Only | `maestro test --tags smokeTest maestro/` | 2 smoke flows pass |
| Greenlight Preflight | `greenlight preflight EyeRestios` | CRITICAL = 0 |
| Individual Test | `cd EyeRestios && fastlane test testplan:TimerViewModelTests` | Specific test file |

### CI/CD Integration

```bash
# Full test pipeline (run before commit)
cd EyeRestios && fastlane test       # Unit + Integration
maestro test maestro/                 # E2E
greenlight preflight EyeRestios       # Rule violations
```
