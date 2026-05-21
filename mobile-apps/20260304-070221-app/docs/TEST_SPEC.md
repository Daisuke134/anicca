# Test Specification: BreathStory

**Date:** 2026-03-04
**Version:** 1.0.0

Source: [XCTest Documentation](https://developer.apple.com/documentation/xctest)
Source: [Swift Testing](https://developer.apple.com/xcode/swift-testing/)

---

## Test Strategy

| Layer | Ratio | Tool | What |
|-------|-------|------|------|
| Unit Tests | 80% | Swift Testing / XCTest | Models, Services, ViewModels |
| Integration Tests | 15% | XCTest + Mocks | Service interactions |
| E2E Tests | 5% | Maestro | Key user flows |

---

## Unit Test Matrix

### Models

| # | File | Test Name | What |
|---|------|-----------|------|
| T-M1 | Story.swift | `testStoryIsPremiumFlag` | isPremium = false for first 3 stories |
| T-M2 | Story.swift | `testStoryHasRequiredFields` | id, title, script, soundFile non-empty |
| T-M3 | BreathingPattern.swift | `testBoxBreathingPattern` | inhale=4, hold=4, exhale=4 |
| T-M4 | BreathingPattern.swift | `testFourSevenEightPattern` | inhale=4, hold=7, exhale=8 |
| T-M5 | BreathingPattern.swift | `testCoherentBreathingPattern` | inhale=5, hold=0, exhale=5 |

### Services

| # | File | Test Name | What |
|---|------|-----------|------|
| T-S1 | StreakService.swift | `testFirstSessionSetsStreakToOne` | New install → streak = 1 after first session |
| T-S2 | StreakService.swift | `testConsecutiveDayIncrementsStreak` | Yesterday session → today session → streak = 2 |
| T-S3 | StreakService.swift | `testSameDayDoesNotDoubleCount` | Two sessions same day → streak stays same |
| T-S4 | StreakService.swift | `testMissedDayResetsStreak` | Session 3 days ago → today → streak = 1 |
| T-S5 | SubscriptionService.swift | `testIsPremiumFalseByDefault` | Fresh init → isPremium = false |
| T-S6 | SubscriptionService.swift | `testEntitlementKeyIsPremium` | Entitlement identifier = "premium" |

### ViewModels

| # | File | Test Name | What |
|---|------|-----------|------|
| T-V1 | LibraryViewModel.swift | `testFreeStoriesUnlocked` | First 3 stories: isLocked = false |
| T-V2 | LibraryViewModel.swift | `testPremiumStoriesLockedOnFreeTier` | Stories 4-5 locked when isPremium = false |
| T-V3 | LibraryViewModel.swift | `testAllStoriesUnlockedOnPremium` | All stories unlocked when isPremium = true |
| T-V4 | PlayerViewModel.swift | `testInitialStateIsStopped` | Initial state: isPlaying = false |
| T-V5 | PlayerViewModel.swift | `testBreathPhaseTransitions` | Inhale → Hold → Exhale phase sequence |
| T-V6 | SubscriptionViewModel.swift | `testDefaultSelectedPackageIsAnnual` | Annual package selected by default |

---

## Integration Tests

| # | Test Name | What |
|---|-----------|------|
| T-I1 | `testStoryLibraryHasFiveStories` | StoryLibrary.allStories.count == 5 |
| T-I2 | `testAllSoundFilesExistInBundle` | 5 .mp3 files present in bundle |
| T-I3 | `testBreathingPatternTimingsAreValid` | All patterns: inhale+exhale > 0 |
| T-I4 | `testStreakPersistsAcrossServiceInit` | Write streak → create new StreakService → read same streak |

---

## E2E Tests (Maestro)

### T-E1: Onboarding Flow
```yaml
# maestro/01-onboarding.yaml
- launchApp
- assertVisible: "Breathing helps. But it's boring."
- tapOn: "→"
- assertVisible: "What if breathing felt like a story?"
- tapOn: "→"
- assertVisible: "Start Breathing"
- tapOn: "Start Breathing"
- assertVisible: "BreathStory"  # HomeView
```

### T-E2: Play Free Story
```yaml
# maestro/02-play-free-story.yaml
- launchApp
- tapOn: "Start Breathing"
- tapOn: "The Forest Path"
- assertVisible: "INHALE"
- tapOn: "Stop"
```

### T-E3: Paywall Appears for Premium Story
```yaml
# maestro/03-paywall.yaml
- launchApp
- tapOn: "Start Breathing"
- tapOn: "Starfield"      # 4th story (premium)
- assertVisible: "BreathStory Premium"
- assertVisible: "Maybe Later"   # CRITICAL: always visible
- tapOn: "Maybe Later"
- assertNotVisible: "BreathStory Premium"  # dismissed
```

---

## Test File Locations

```
BreathStoryios/
└── BreathStoryTests/
    ├── Models/
    │   ├── StoryTests.swift
    │   └── BreathingPatternTests.swift
    ├── Services/
    │   ├── StreakServiceTests.swift
    │   └── SubscriptionServiceTests.swift
    ├── ViewModels/
    │   ├── LibraryViewModelTests.swift
    │   ├── PlayerViewModelTests.swift
    │   └── SubscriptionViewModelTests.swift
    └── Integration/
        └── IntegrationTests.swift
```

---

## Build & Run Tests

```bash
# Unit + Integration
cd BreathStoryios
xcodebuild test -scheme BreathStory -destination 'platform=iOS Simulator,name=iPhone 15' 2>&1 | tail -20

# E2E (Maestro)
maestro test maestro/01-onboarding.yaml
maestro test maestro/02-play-free-story.yaml
maestro test maestro/03-paywall.yaml
```

---

## Acceptance: All Tests Must Pass

| Check | Command | Expected |
|-------|---------|---------|
| Unit tests pass | `xcodebuild test` | `** TEST SUCCEEDED **` |
| No Mock in production code | `grep -r 'Mock' --include='*.swift' . \| grep -v Tests/` | 0 results |
| RevenueCat imported | `grep -r 'import RevenueCat' --include='*.swift' .` | > 0 results |
| RevenueCatUI NOT imported | `grep -r 'import RevenueCatUI' --include='*.swift' .` | 0 results |
