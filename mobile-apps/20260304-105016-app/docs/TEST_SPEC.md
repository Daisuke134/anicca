# Test Specification: Chi Daily

**Version:** 1.0
**Date:** 2026-03-04
**Coverage Target:** 80%+ (P0 features: 100%)

---

## 1. Test Strategy (Test Pyramid)

```
         /\
        /  \       UI Tests (10%) — XCUITest: onboarding, check-in flow
       /    \
      /      \     Integration Tests (20%) — ViewModel + SwiftData
     /________\
    /          \   Unit Tests (70%) — Models, Services, ViewModels
   /____________\
```

| Layer | Ratio | Tool | Scope |
|-------|-------|------|-------|
| Unit | 70% | XCTest + Swift Testing | Models, ConstitutionType, FoundationModelsService parsing, SubscriptionService logic |
| Integration | 20% | XCTest + SwiftData in-memory | CheckInViewModel + ModelContext, HistoryViewModel queries |
| UI | 10% | XCUITest | Onboarding flow, check-in flow, history navigation |

---

## 2. Unit Test Cases

### 2.1 ConstitutionType Tests

**File:** `ChiDailyiosTests/Models/ConstitutionTypeTests.swift`

| Test | Input | Expected |
|------|-------|---------|
| `testAllCasesHaveIcon` | All 5 cases | `.icon` returns non-empty string |
| `testAllCasesHaveColor` | All 5 cases | `.color` returns non-nil Color |
| `testAllCasesHaveJapaneseName` | All 5 cases | `.japaneseName` returns non-empty string |
| `testFromStringValid` | "Wood" | `.wood` |
| `testFromStringValid_fire` | "Fire" | `.fire` |
| `testFromStringInvalid_defaultsToEarth` | "Invalid" | `.earth` |
| `testFromStringCaseSensitive` | "wood" | `.earth` (default, case-sensitive) |
| `testAllCasesHaveRawValue` | All 5 cases | rawValue matches enum name |

```swift
// Example
@Test func testFromStringValid() {
    let result = ConstitutionType.from(string: "Wood")
    #expect(result == .wood)
}

@Test func testFromStringInvalid_defaultsToEarth() {
    let result = ConstitutionType.from(string: "Unknown")
    #expect(result == .earth)
}

@Test(arguments: ConstitutionType.allCases)
func testAllCasesHaveIcon(type: ConstitutionType) {
    #expect(!type.icon.isEmpty)
}
```

### 2.2 CheckIn Model Tests

**File:** `ChiDailyiosTests/Models/CheckInTests.swift`

| Test | Scenario | Expected |
|------|---------|---------|
| `testInitDefaults` | Default init | `id` is UUID, `date` ≈ now, createdAt ≈ now |
| `testInitWithValues` | Custom values 1–5 | All properties set correctly |
| `testBoundaryValues_min` | All answers = 1 | Model accepts without crash |
| `testBoundaryValues_max` | All answers = 5 | Model accepts without crash |

### 2.3 FoundationModelsService Parsing Tests

**File:** `ChiDailyiosTests/Services/FoundationModelsServiceParsingTests.swift`

Test the JSON parsing logic in isolation (without calling Foundation Models).

| Test | Input JSON | Expected |
|------|-----------|---------|
| `testParseValidJSON_wood` | `{"constitution":"Wood","food":"..","movement":"..","rest":".."}` | ConstitutionType.wood + 3 recs |
| `testParseValidJSON_water` | `{"constitution":"Water","food":"..","movement":"..","rest":".."}` | ConstitutionType.water + 3 recs |
| `testParseMissingField_throwsError` | `{"constitution":"Wood","food":".."}` | FoundationModelsError.parseFailure |
| `testParseEmptyJSON_throwsError` | `{}` | FoundationModelsError.parseFailure |
| `testParseRecommendationCategories` | Valid JSON | food/movement/rest categories correct |

### 2.4 SubscriptionService Logic Tests

**File:** `ChiDailyiosTests/Services/SubscriptionServiceTests.swift`

| Test | State | Expected |
|------|-------|---------|
| `testCanStartCheckIn_proUser` | isProUser=true, freeUsed=99 | `canStartCheckIn()` = true |
| `testCanStartCheckIn_freeUnder3` | isProUser=false, freeUsed=2 | `canStartCheckIn()` = true |
| `testCanStartCheckIn_freeExactly3` | isProUser=false, freeUsed=3 | `canStartCheckIn()` = false |
| `testCanStartCheckIn_freeOver3` | isProUser=false, freeUsed=5 | `canStartCheckIn()` = false |
| `testRecordFreeCheckIn_incrementsCount` | freeUsed=1 | After `recordFreeCheckIn()`: freeUsed=2 |

### 2.5 CheckInViewModel Tests

**File:** `ChiDailyiosTests/ViewModels/CheckInViewModelTests.swift`

| Test | Action | Expected |
|------|--------|---------|
| `testInitialState` | Create viewModel | currentQuestion=0, answers=[3,3,3,3,3] |
| `testSelectAnswer` | `selectAnswer(5)` on Q1 | answers[0] = 5 |
| `testNextQuestion` | `nextQuestion()` | currentQuestion = 1 |
| `testNextQuestion_clampsAt4` | `nextQuestion()` from Q4 | currentQuestion stays 4 |
| `testPreviousQuestion` | `previousQuestion()` from Q2 | currentQuestion = 1 |
| `testPreviousQuestion_clampsAt0` | `previousQuestion()` from Q0 | currentQuestion stays 0 |
| `testAnswersIndependentPerQuestion` | Set Q1=5, Q2=2 | answers[0]=5, answers[1]=2 |

---

## 3. Integration Test Cases

### 3.1 CheckIn Persistence

**File:** `ChiDailyiosTests/Integration/CheckInPersistenceTests.swift`

Uses `ModelConfiguration(isStoredInMemoryOnly: true)` for speed.

| Test | Action | Expected |
|------|--------|---------|
| `testSaveAndFetch` | Save CheckIn, fetch | Fetched item matches saved |
| `testFetchTodayOnly` | Save yesterday + today | Fetch today = 1 result |
| `testFetchSortedByDate` | Save 3 entries | Fetched in descending date order |
| `testDeleteCheckIn` | Save + delete | Fetch returns 0 |

```swift
@Test func testSaveAndFetch() async throws {
    let config = ModelConfiguration(isStoredInMemoryOnly: true)
    let container = try ModelContainer(for: CheckIn.self, configurations: config)
    let context = ModelContext(container)

    let checkIn = CheckIn(energyLevel: 4, sleepQuality: 3, digestionComfort: 4,
                          emotionalState: 5, physicalSensation: 3,
                          constitutionType: "Wood", foodRecommendation: "Eat greens",
                          movementRecommendation: "Stretch", restRecommendation: "Sleep by 10")
    context.insert(checkIn)
    try context.save()

    let descriptor = FetchDescriptor<CheckIn>()
    let results = try context.fetch(descriptor)
    #expect(results.count == 1)
    #expect(results[0].constitutionType == "Wood")
}
```

---

## 4. UI Test Cases

**File:** `ChiDailyiosUITests/OnboardingUITests.swift`

### 4.1 Onboarding Flow

| Step | Action | Assertion |
|------|--------|-----------|
| 1 | Launch app (first run) | Onboarding Screen 1 visible |
| 2 | Tap "Get Started" | Screen 2 visible |
| 3 | Tap "Continue" | Screen 3 (paywall) visible |
| 4 | Tap "Maybe Later" | HomeView visible |

### 4.2 Check-in Flow (Subscription mocked via RC sandbox)

| Step | Action | Assertion |
|------|--------|-----------|
| 1 | Tap "Start Today's Check-in" | CheckInView with Q1 visible |
| 2 | Select answer option 3 | Option 3 highlighted |
| 3 | Tap "Next" 4 times | Q5 visible |
| 4 | Tap "Get My Plan" | ProgressView appears, then ResultView |
| 5 | View ResultView | 3 recommendation cards visible |
| 6 | Tap "Done ✓" | HomeView, today's result shown |

### 4.3 History Navigation

| Step | Action | Assertion |
|------|--------|-----------|
| 1 | Tap "History" tab | HistoryView visible |
| 2 | Tap first entry | HistoryDetailView shows constitution + cards |
| 3 | Tap back | HistoryView visible |

---

## 5. Accessibility Testing Checklist

| Element | Check |
|---------|-------|
| All buttons | `.accessibilityLabel()` set |
| Recommendation cards | Full text accessible as one unit |
| Constitution badge | Icon + name announced together |
| Question options | "Option X of 5: Label" announced |
| Progress bar | `.accessibilityValue("Question X of 5")` |
| Tab bar items | Default SwiftUI accessibility labels |

---

## 6. Performance Targets

| Metric | Target | How to measure |
|--------|--------|---------------|
| App cold launch | < 2 sec | Instruments → App Launch |
| Foundation Models response | < 3 sec | Time from "Get My Plan" tap to ResultView |
| SwiftData fetch (7 entries) | < 0.1 sec | XCTest `measure` block |

---

## 7. Edge Cases

| Scenario | Expected Behavior |
|---------|------------------|
| Foundation Models times out | Show error message; allow retry |
| Foundation Models returns malformed JSON | `parseFailure` error; show user-friendly message |
| HealthKit authorization denied | Silent fail; check-in still saved |
| RevenueCat unreachable | Paywall shows without offering; retry available |
| 0 check-ins in history | Empty state shown; no crash |
| No internet (all features) | App works fully offline (Foundation Models is on-device) |

---

## 8. Test Execution

```bash
# Run all tests (via Fastlane — MANDATORY)
cd ChiDailyios && fastlane test

# Individual test target
xcodebuild test -scheme ChiDailyios -destination 'platform=iOS Simulator,name=iPhone 16'
```

---

## 9. Beta Testing Plan

| Phase | Duration | Participants | Focus |
|-------|----------|-------------|-------|
| Internal | 3 days | Dev + 2 friends | Crash-free baseline |
| TestFlight EN | 7 days | 20 US testers | Onboarding, check-in UX |
| TestFlight JA | 7 days | 10 Japan testers | Japanese localization accuracy |

**Success criteria before App Store submission:**
- Crash-free rate > 99.5%
- All 7 acceptance criteria in US-004 confirmed working
- No untranslated strings in Japanese
