# Test Specification: DeskStretch

> **Version:** 1.0 | **Date:** 2026-03-05

---

## 1. Strategy

### Test Pyramid

```
        /\
       /  \      E2E (10%) — Maestro
      /____\       3 scenarios
     /      \    Integration (20%) — XCTest
    /________\     5 test files
   /          \  Unit (70%) — Swift Testing
  /______________\  7 test files
```

| Layer | Framework | Coverage Target | Speed |
|-------|-----------|----------------|-------|
| **Unit** | Swift Testing (`#expect`) | 70% | < 1s per test |
| **Integration** | XCTest | 20% | < 5s per test |
| **E2E** | Maestro | 10% | < 60s per scenario |
| **Overall** | Combined | **80%+** | < 3 min total |

### Testing Rules

| Rule | Detail |
|------|--------|
| TDD mandatory | RED → GREEN → REFACTOR |
| AAA pattern | Arrange → Act → Assert |
| Test length | < 10 lines per test |
| Isolation | No test depends on another test |
| Real SDK | RevenueCat real SDK (no mocks for subscription logic) |
| Fastlane only | `cd DeskStretchios && fastlane test` (no xcodebuild) |

---

## 2. Unit Tests

### 2.1 ProgressServiceTests.swift

| # | Test Name | What It Tests |
|---|-----------|--------------|
| 1 | `testRecordFirstSession` | First session sets todayCount=1, streak=1 |
| 2 | `testRecordSecondSessionSameDay` | todayCount increments, streak unchanged |
| 3 | `testStreakContinuesConsecutiveDay` | Next-day session increments streak |
| 4 | `testStreakResetsAfterMissedDay` | Missed day resets streak to 1 |
| 5 | `testTotalSessionsIncrement` | totalSessions always increments |
| 6 | `testTotalMinutesAccumulate` | totalMinutes adds session duration |
| 7 | `testWeekHistoryTracked` | weekHistory records daily counts |
| 8 | `testLoadEmptyReturnsDefault` | No saved data returns UserProgress.empty |

### 2.2 StretchRecommendationServiceTests.swift

| # | Test Name | What It Tests |
|---|-----------|--------------|
| 1 | `testGenerateReturnsCorrectCount` | Returns requested exercise count |
| 2 | `testGenerateFiltersByPainArea` | Only returns exercises for selected pain areas |
| 3 | `testGenerateAvoidsRecentExercises` | Excludes exercises from last 3 sessions |
| 4 | `testGenerateWithInsufficientExercises` | Returns available exercises when fewer than requested |
| 5 | `testEmptyPainAreasReturnsEmpty` | No pain areas → empty routine |

### 2.3 NotificationServiceTests.swift

| # | Test Name | What It Tests |
|---|-----------|--------------|
| 1 | `testScheduleCreatesRequest` | Scheduling adds notification to center |
| 2 | `testCancelRemovesAll` | cancelAll removes all pending requests |
| 3 | `testIntervalConversion` | Minutes correctly convert to TimeInterval |

### 2.4 BreakScheduleTests.swift

| # | Test Name | What It Tests |
|---|-----------|--------------|
| 1 | `testDefaultValues` | Default schedule is 60min, 9:00-18:00 |
| 2 | `testValidIntervals` | Only 30/45/60/90 are valid |
| 3 | `testCodable` | Encode/decode roundtrip preserves values |

### 2.5 StretchExerciseTests.swift

| # | Test Name | What It Tests |
|---|-----------|--------------|
| 1 | `testJSONDecoding` | StretchLibrary.json decodes correctly |
| 2 | `testCategoryFiltering` | Filter by PainArea returns correct subset |
| 3 | `testMinimumExerciseCount` | At least 20 exercises in library |
| 4 | `testEachCategoryHasMinimum5` | Each pain area has 5+ exercises |
| 5 | `testUniqueIds` | All exercise IDs are unique |

### 2.6 PainAreaTests.swift

| # | Test Name | What It Tests |
|---|-----------|--------------|
| 1 | `testAllCases` | 4 cases: neck, back, shoulders, wrists |
| 2 | `testDisplayName` | Each case has non-empty display name |
| 3 | `testSFSymbol` | Each case has non-empty SF Symbol name |

### 2.7 UserProgressTests.swift

| # | Test Name | What It Tests |
|---|-----------|--------------|
| 1 | `testEmptyProgress` | .empty has all zeros |
| 2 | `testCodableRoundtrip` | Encode/decode preserves all fields |

---

## 3. Integration Tests

### 3.1 SubscriptionIntegrationTests.swift

| # | Test Name | What It Tests |
|---|-----------|--------------|
| 1 | `testOfferingsLoad` | RevenueCat offerings load (sandbox) |
| 2 | `testEntitlementCheck` | Premium entitlement check works |
| 3 | `testRestorePurchases` | Restore completes without crash |

### 3.2 StretchLibraryIntegrationTests.swift

| # | Test Name | What It Tests |
|---|-----------|--------------|
| 1 | `testLoadFromBundle` | JSON loads from app bundle |
| 2 | `testAllCategoriesRepresented` | All 4 pain areas have exercises |

### 3.3 ProgressPersistenceTests.swift

| # | Test Name | What It Tests |
|---|-----------|--------------|
| 1 | `testSaveAndLoad` | UserDefaults roundtrip works |
| 2 | `testOverwritePreservesData` | Sequential saves don't corrupt |

### 3.4 AppStateIntegrationTests.swift

| # | Test Name | What It Tests |
|---|-----------|--------------|
| 1 | `testOnboardingFlagPersists` | hasCompletedOnboarding survives app restart |
| 2 | `testPainAreasPersist` | Selected pain areas survive app restart |

### 3.5 NotificationIntegrationTests.swift

| # | Test Name | What It Tests |
|---|-----------|--------------|
| 1 | `testScheduleAndRetrieve` | Scheduled notification appears in pending list |

---

## 4. E2E Tests (Maestro)

### 4.1 01-onboarding.yaml

```yaml
appId: com.aniccafactory.deskstretch
tags:
  - smokeTest
  - onboarding
---
- launchApp:
    clearState: true
- assertVisible: "Back pain from sitting all day?"
- tapOn:
    id: "onboarding_get_started"
- assertVisible: "Where does it hurt?"
- tapOn:
    id: "pain_area_neck"
- tapOn:
    id: "pain_area_back"
- tapOn: "Continue"
- assertVisible: "Unlock Your Full Stretch Routine"
- tapOn:
    id: "paywall_maybe_later"
- assertVisible:
    id: "timer_countdown"
```

### 4.2 02-timer-stretch-flow.yaml

```yaml
appId: com.aniccafactory.deskstretch
tags:
  - smokeTest
  - timer
---
- launchApp
- tapOn:
    id: "timer_stretch_now"
- assertVisible:
    id: "session_exercise_name"
- assertVisible:
    id: "session_skip"
- tapOn:
    id: "session_skip"
- tapOn:
    id: "session_skip"
- tapOn:
    id: "session_skip"
- assertVisible: "Great stretch!"
```

### 4.3 03-paywall.yaml

```yaml
appId: com.aniccafactory.deskstretch
tags:
  - paywall
---
- launchApp:
    clearState: true
- tapOn:
    id: "onboarding_get_started"
- tapOn:
    id: "pain_area_neck"
- tapOn: "Continue"
- assertVisible: "$3.99"
- assertVisible: "$29.99"
- assertVisible: "7-day free trial"
- assertVisible:
    id: "paywall_maybe_later"
- tapOn:
    id: "paywall_maybe_later"
```

---

## 5. Edge Cases

| # | Scenario | Expected Behavior |
|---|----------|------------------|
| 1 | No pain areas selected → Continue | Button disabled (cannot proceed) |
| 2 | All exercises completed today (free tier) | Show paywall upsell |
| 3 | No notification permission | Timer shows in-app countdown, prompt re-enable |
| 4 | App killed during session | Session not recorded (no partial credit) |
| 5 | Date changes mid-session | Session recorded for start date |
| 6 | UserDefaults data corrupted | Return .empty defaults, no crash |
| 7 | StretchLibrary.json empty for pain area | Show "No exercises found" message |
| 8 | RevenueCat network error | Show error alert, don't change subscription state |
| 9 | Timezone change | Streak calculation uses Calendar.current |
| 10 | Device clock manipulation | Streak based on last active date comparison |

---

## 6. Accessibility Testing

| Test | Method | Criteria |
|------|--------|---------|
| VoiceOver navigation | Manual | All screens navigable with VoiceOver |
| Dynamic Type | Simulator settings | Text scales without truncation at all sizes |
| Color contrast | Xcode Accessibility Inspector | 4.5:1 minimum for all text |
| Reduce Motion | Simulator settings | No animations when enabled |
| Bold Text | Simulator settings | All text respects bold preference |

---

## 7. Performance Testing

| Metric | Target | Test Method |
|--------|--------|------------|
| Cold start | < 2s | Xcode Instruments (Time Profiler) |
| Stretch selection | < 500ms | Unit test with timeout |
| Memory usage | < 50 MB | Instruments (Allocations) |
| Scroll performance | 60 FPS | Instruments (Core Animation) |
| Battery impact | < 1%/hr | Instruments (Energy Log) |

---

## 8. Manual Testing Checklist

| # | Test | How to Verify |
|---|------|--------------|
| 1 | Onboarding completes | Fresh install → 3 screens → main app |
| 2 | Timer fires notification | Set 1-min interval → wait → notification appears |
| 3 | Stretch session works | Tap notification → exercises play → completion screen |
| 4 | Progress updates | Complete session → progress tab shows increment |
| 5 | Streak logic | Use on consecutive days → streak increments |
| 6 | Paywall appears | Tap premium feature as free user → paywall shows |
| 7 | Maybe Later works | Tap Maybe Later → paywall dismisses |
| 8 | Settings persist | Change interval → kill app → reopen → setting saved |
| 9 | Dark mode | Toggle system dark mode → all screens render correctly |
| 10 | Japanese locale | Switch to ja → all strings localized |

---

## 9. Test Execution

```bash
# Unit + Integration tests (via Fastlane)
cd DeskStretchios && FASTLANE_SKIP_UPDATE_CHECK=1 fastlane test

# E2E tests (Maestro)
maestro test maestro/

# Specific E2E
maestro test maestro/01-onboarding.yaml

# Smoke tests only
maestro test maestro/ --include-tags=smokeTest
```
