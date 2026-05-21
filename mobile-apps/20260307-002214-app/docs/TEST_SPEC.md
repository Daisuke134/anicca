# Test Specification: EyeBreakIsland

**Version:** 1.0
**Date:** 2026-03-07
**SSOT:** docs/PRD.md
**Architecture:** docs/ARCHITECTURE.md
**UX Spec:** docs/UX_SPEC.md

Source: [Martin Fowler: Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html) — "Write many small unit tests, some integration tests, few E2E tests"
Source: [Apple: Testing Your Apps in Xcode](https://developer.apple.com/documentation/xctest) — "XCTest framework for unit and UI testing"
Source: [Maestro: Mobile UI Testing](https://maestro.mobile.dev/) — "Write E2E tests in YAML"

---

## 1. Test Strategy

### Test Pyramid

```
         ╱╲
        ╱ E2E ╲          6 flows (Maestro)     10%
       ╱────────╲
      ╱Integration╲      8 tests               20%
     ╱──────────────╲
    ╱   Unit Tests    ╲   32 tests              70%
   ╱────────────────────╲
```

| Level | Framework | Count | Coverage Target | Location |
|-------|-----------|-------|----------------|----------|
| Unit | XCTest | 32+ | 70% | `EyeBreakIslandTests/` |
| Integration | XCTest | 8+ | 20% | `EyeBreakIslandTests/Integration/` |
| E2E | Maestro | 6+ | 10% | `maestro/` |

### Test Naming Convention

```
test_{methodName}_{scenario}_{expectedBehavior}
```

Example: `test_startSession_whenIdle_setsRunningState`

---

## 2. Unit Tests

### TimerServiceTests.swift (8 tests)

| # | Test Name | Target | What It Verifies |
|---|-----------|--------|-----------------|
| 1 | `test_startSession_whenIdle_setsRunningState` | F-001 | `timerState` becomes `.running` |
| 2 | `test_startSession_whenIdle_setsCorrectDuration` | F-001 | `remainingSeconds` = 1200 (20 min) |
| 3 | `test_stopSession_whenRunning_setsIdleState` | F-001 | `timerState` becomes `.idle` |
| 4 | `test_pauseSession_whenRunning_setsPausedState` | F-001 | `timerState` becomes `.paused` |
| 5 | `test_resumeSession_whenPaused_setsRunningState` | F-001 | `timerState` returns to `.running` |
| 6 | `test_startBreak_setsBreakingState` | F-001 | `timerState` becomes `.breaking`, `remainingSeconds` = 20 |
| 7 | `test_completeBreak_incrementsBreakCount` | F-001 | `breakCount` increments by 1 |
| 8 | `test_completeBreak_restartsWorkTimer` | F-001 | `timerState` = `.running`, `remainingSeconds` = 1200 |

### NotificationServiceTests.swift (4 tests)

| # | Test Name | Target | What It Verifies |
|---|-----------|--------|-----------------|
| 9 | `test_requestPermission_returnsBool` | F-003 | Returns `true` or `false` (no crash) |
| 10 | `test_scheduleBreakNotification_createsRequest` | F-003 | UNNotificationCenter has 1 pending request |
| 11 | `test_cancelAll_removesPendingRequests` | F-003 | Pending notification count = 0 |
| 12 | `test_scheduleBreakNotification_correctInterval` | F-003 | Trigger interval matches input |

### SubscriptionServiceTests.swift (6 tests)

| # | Test Name | Target | What It Verifies |
|---|-----------|--------|-----------------|
| 13 | `test_initialStatus_isFree` | F-005 | Default `status` = `.free` |
| 14 | `test_configure_doesNotCrash` | F-005 | `configure(apiKey:)` runs without error |
| 15 | `test_loadOfferings_returnsPackages` | F-005 | `loadOfferings()` returns non-empty array (mock) |
| 16 | `test_purchase_updatesStatusToPro` | F-005 | `status` becomes `.pro` after successful purchase (mock) |
| 17 | `test_restorePurchases_updatesStatus` | F-005 | `restorePurchases()` sets correct status (mock) |
| 18 | `test_checkStatus_returnsCurrentStatus` | F-005 | `checkStatus()` returns cached status on error |

### TimerViewModelTests.swift (6 tests)

| # | Test Name | Target | What It Verifies |
|---|-----------|--------|-----------------|
| 19 | `test_formattedTime_idle_shows2000` | ViewModel | "20:00" when idle with 1200 seconds |
| 20 | `test_formattedTime_running_formatsCorrectly` | ViewModel | "18:34" for 1114 seconds |
| 21 | `test_formattedTime_breaking_showsSeconds` | ViewModel | "00:15" for 15 seconds |
| 22 | `test_toggleTimer_whenIdle_startsSession` | ViewModel | `timerState` becomes `.running` |
| 23 | `test_toggleTimer_whenRunning_stopsSession` | ViewModel | `timerState` becomes `.idle` |
| 24 | `test_toggleTimer_whenBreaking_doesNothing` | ViewModel | `timerState` stays `.breaking` |

### OnboardingViewModelTests.swift (4 tests)

| # | Test Name | Target | What It Verifies |
|---|-----------|--------|-----------------|
| 25 | `test_initialPage_isZero` | F-004 | `currentPage` = 0 |
| 26 | `test_nextPage_incrementsPage` | F-004 | `currentPage` goes from 0 to 1 |
| 27 | `test_completeOnboarding_setsFlag` | F-004 | `UserDefaults.hasCompletedOnboarding` = true |
| 28 | `test_totalPages_isFour` | F-004 | `totalPages` = 4 (problem, feature, notification, paywall) |

### PaywallViewModelTests.swift (4 tests)

| # | Test Name | Target | What It Verifies |
|---|-----------|--------|-----------------|
| 29 | `test_initialPackages_isEmpty` | F-005 | `packages` is empty before load |
| 30 | `test_selectedPackage_initiallyNil` | F-005 | `selectedPackage` = nil |
| 31 | `test_purchase_setsIsPurchasing` | F-005 | `isPurchasing` = true during purchase |
| 32 | `test_purchase_cancelledByUser_statusRemainsFree` | F-005 | `status` stays `.free` when user cancels |

---

## 3. Integration Tests

### Integration/ directory (8 tests)

| # | Test Name | Services Tested | What It Verifies |
|---|-----------|----------------|-----------------|
| 1 | `test_timerToNotification_schedulesOnBackground` | TimerService + NotificationService | When timer starts, background notification is scheduled for 20 min |
| 2 | `test_timerToNotification_cancelsOnStop` | TimerService + NotificationService | When timer stops, pending notifications are cancelled |
| 3 | `test_subscriptionGating_freeUserCannotSetInterval` | SubscriptionService + SettingsViewModel | Free user cannot change timer interval from default |
| 4 | `test_subscriptionGating_proUserCanSetInterval` | SubscriptionService + SettingsViewModel | Pro user can change timer interval to 15/25 min |
| 5 | `test_onboardingToTimer_setsCompletionFlag` | OnboardingViewModel + UserDefaults | After onboarding, `hasCompletedOnboarding` = true and timer screen is shown |
| 6 | `test_breakSession_persistsToUserDefaults` | TimerService + UserDefaults | Break count is persisted and survives service re-init |
| 7 | `test_streakCalculation_consecutiveDays` | TimerService + UserDefaults | Streak increments for consecutive active days |
| 8 | `test_streakCalculation_missedDay_resetsStreak` | TimerService + UserDefaults | Streak resets to 0 when a day is missed |

---

## 4. E2E Tests (Maestro)

### Test Files

| # | File | Scenario | Key Assertions | Tags |
|---|------|----------|---------------|------|
| 1 | `maestro/onboarding_flow.yaml` | Complete onboarding (4 pages) | All 4 pages visible, notification prompt appears, paywall displays | `smokeTest` |
| 2 | `maestro/timer_start_stop.yaml` | Start and stop timer | Timer shows countdown, stop returns to idle | `smokeTest` |
| 3 | `maestro/settings_navigation.yaml` | Open settings, verify sections | Settings sheet opens, all sections visible | — |
| 4 | `maestro/payment_monthly.yaml` | Select monthly, tap subscribe | Monthly package selected, subscribe button enabled | — |
| 5 | `maestro/payment_annual.yaml` | Select annual, tap subscribe | Annual package selected, trial info visible | — |
| 6 | `maestro/payment_failure.yaml` | Cancel purchase flow | Paywall remains visible, error handled | — |

### Maestro Standards

| Rule | Implementation |
|------|---------------|
| Selectors | `id:` only (e.g., `id: "timer_start_button"`) — NO `point:` selectors |
| State cleanup | `clearState` at start of every flow |
| Screenshots | `takeScreenshot` after each key assertion |
| Accessibility IDs | Must match UX_SPEC.md §7 table exactly |
| Timeout | Default 10s per assertion |

### Example: onboarding_flow.yaml

```yaml
appId: com.aniccafactory.eyebreakisland
tags:
  - smokeTest
---
- clearState
- launchApp

# Page 1: Problem
- assertVisible:
    id: "onboarding_page_1"
- takeScreenshot: onboarding_page_1

# Next
- tapOn:
    id: "onboarding_next_button"

# Page 2: Feature
- assertVisible:
    id: "onboarding_page_2"
- takeScreenshot: onboarding_page_2

# Next
- tapOn:
    id: "onboarding_next_button"

# Page 3: Notification
- assertVisible:
    id: "onboarding_page_3"
- takeScreenshot: onboarding_page_3

# Allow notifications (system dialog)
- tapOn:
    id: "onboarding_allow_notifications"
- tapOn:
    text: "Allow"
    optional: true

# Page 4: Paywall
- assertVisible:
    id: "paywall_container"
- assertVisible:
    id: "paywall_maybe_later"
- takeScreenshot: paywall_view

# Dismiss
- tapOn:
    id: "paywall_maybe_later"

# Timer screen
- assertVisible:
    id: "timer_view"
- takeScreenshot: timer_view_after_onboarding
```

### Example: timer_start_stop.yaml

```yaml
appId: com.aniccafactory.eyebreakisland
tags:
  - smokeTest
---
- clearState
- launchApp

# Skip onboarding (if needed)
- tapOn:
    id: "onboarding_next_button"
    optional: true
- tapOn:
    id: "onboarding_next_button"
    optional: true
- tapOn:
    id: "onboarding_allow_notifications"
    optional: true
- tapOn:
    text: "Allow"
    optional: true
- tapOn:
    id: "paywall_maybe_later"
    optional: true

# Timer screen
- assertVisible:
    id: "timer_view"
- assertVisible:
    id: "timer_start_button"
- takeScreenshot: timer_idle

# Start timer
- tapOn:
    id: "timer_start_button"
- assertVisible:
    id: "timer_time_label"
- takeScreenshot: timer_running

# Stop timer
- tapOn:
    id: "timer_stop_button"
- assertVisible:
    id: "timer_start_button"
- takeScreenshot: timer_stopped
```

---

## 5. Greenlight Checks

### Rule Compliance (MUST all PASS before any release)

| Check | Command | Expected |
|-------|---------|----------|
| Rule 17: No analytics SDK | `grep -rE "Mixpanel\|Analytics\|Firebase" EyeBreakIsland/ --include="*.swift" \| grep -v "Tests/"` | 0 matches |
| Rule 20: No RevenueCatUI | `grep -r "RevenueCatUI" EyeBreakIsland/ --include="*.swift"` | 0 matches |
| Rule 20: Custom PaywallView exists | `grep -r "Purchases.shared.purchase" EyeBreakIsland/ --include="*.swift" \| grep -v "Tests/"` | 1+ matches |
| Rule 20: Maybe Later exists | `grep -r "paywall_maybe_later\|maybe_later\|Maybe Later" EyeBreakIsland/ --include="*.swift"` | 1+ matches |
| Rule 20b: No ATT | `grep -r "ATTrackingManager\|requestTrackingAuthorization" EyeBreakIsland/ --include="*.swift"` | 0 matches |
| Rule 20b: No tracking description | `grep -r "NSUserTrackingUsageDescription" EyeBreakIsland/ --include="*.plist"` | 0 matches |
| Rule 21: No AI API | `grep -rE "OpenAI\|Anthropic\|GoogleGenerativeAI\|FoundationModels" EyeBreakIsland/ --include="*.swift"` | 0 matches |
| PrivacyInfo exists | `test -f EyeBreakIsland/Resources/PrivacyInfo.xcprivacy` | File exists |
| No hardcoded API key | `grep -rE "appl_[a-zA-Z0-9]+" EyeBreakIsland/ --include="*.swift" \| grep -v "Tests/"` | 0 matches |

### Greenlight CLI

```bash
# Run full greenlight preflight
greenlight preflight EyeBreakIslandios/
# Expected: CRITICAL=0
```

---

## 6. Performance Targets

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Cold launch to timer screen | < 2.0s | Instruments Time Profiler |
| Timer tick interval accuracy | +/- 50ms | XCTest `measure {}` block |
| Memory usage (idle) | < 30 MB | Instruments Allocations |
| Memory usage (timer running) | < 50 MB | Instruments Allocations |
| Live Activity update latency | < 500ms | ActivityKit logs |
| Battery drain (1 hour active) | < 3% | Real device + Settings > Battery |
| App size (IPA) | < 15 MB | Xcode archive |
| Onboarding completion time | < 60 seconds | Maestro flow timing |

Source: [Apple: Improving App Responsiveness](https://developer.apple.com/documentation/xcode/improving-app-responsiveness) — "Aim for a hang-free experience with response times under 100ms"

---

## 7. Test Commands

### Unit + Integration Tests

```bash
# Via Fastlane (preferred)
cd EyeBreakIslandios && fastlane test

# Direct (development only)
xcodebuild test \
    -project EyeBreakIsland.xcodeproj \
    -scheme EyeBreakIsland \
    -destination 'platform=iOS Simulator,name=iPhone 15 Pro' \
    -resultBundlePath TestResults.xcresult
```

### E2E Tests (Maestro)

```bash
# All flows
maestro test maestro/

# Smoke tests only
maestro test --tags smokeTest maestro/

# Single flow
maestro test maestro/onboarding_flow.yaml
```

### Coverage Report

```bash
# Generate coverage
xcodebuild test \
    -project EyeBreakIsland.xcodeproj \
    -scheme EyeBreakIsland \
    -destination 'platform=iOS Simulator,name=iPhone 15 Pro' \
    -enableCodeCoverage YES

# View coverage
xcrun xccov view --report TestResults.xcresult
```

### Test Execution Order

```
1. Unit Tests (32+)          → fastlane test
2. Integration Tests (8+)     → fastlane test (same target)
3. Greenlight Checks          → greenlight preflight
4. E2E Tests (6+)            → maestro test maestro/
5. Performance Tests          → Instruments (manual)
```

---

**End of Test Specification**
