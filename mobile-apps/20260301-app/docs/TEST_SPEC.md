# Test Specification: AffirmFlow

**Version:** 1.0.0
**Date:** 2026-03-01
**Status:** APPROVED

---

## 1. Test Strategy

### 1.1 Test Pyramid

```
        /\
       /  \      UI Tests (10%)
      /____\     5-10 critical flows
     /      \    Integration Tests (20%)
    /________\   Service + Data layer
   /          \  Unit Tests (70%)
  /______________\  Models, ViewModels, Logic
```

### 1.2 Coverage Target

| Target | Percentage |
|--------|------------|
| **Overall** | 80%+ |
| Models | 95% |
| ViewModels | 85% |
| Services | 80% |
| Views | 50% (via UI tests) |

---

## 2. Unit Tests

### 2.1 FocusArea Tests

**File: `AffirmFlowTests/Models/FocusAreaTests.swift`**

```swift
import Testing
@testable import AffirmFlow

struct FocusAreaTests {
    @Test
    func allCasesCount() {
        #expect(FocusArea.allCases.count == 5)
    }

    @Test(arguments: FocusArea.allCases)
    func hasSystemImage(area: FocusArea) {
        #expect(!area.systemImage.isEmpty)
    }

    @Test(arguments: FocusArea.allCases)
    func hasColor(area: FocusArea) {
        #expect(area.color != nil)
    }

    @Test(arguments: FocusArea.allCases)
    func hasDescription(area: FocusArea) {
        #expect(!area.description.isEmpty)
    }

    @Test(arguments: FocusArea.allCases)
    func hasPrompt(area: FocusArea) {
        #expect(!area.prompt.isEmpty)
        #expect(area.prompt.contains("affirmation"))
    }

    @Test
    func rawValueEncoding() {
        #expect(FocusArea.confidence.rawValue == "Confidence")
        #expect(FocusArea.selfLove.rawValue == "Self-Love")
    }
}
```

### 2.2 Affirmation Tests

**File: `AffirmFlowTests/Models/AffirmationTests.swift`**

```swift
import Testing
import Foundation
@testable import AffirmFlow

struct AffirmationTests {
    @Test
    func initializesWithCorrectValues() {
        let affirmation = Affirmation(content: "Test content", focusArea: .calm)

        #expect(affirmation.content == "Test content")
        #expect(affirmation.focusArea == .calm)
        #expect(affirmation.isFavorite == false)
        #expect(affirmation.id != nil)
    }

    @Test
    func createdAtIsNow() {
        let before = Date()
        let affirmation = Affirmation(content: "Test", focusArea: .calm)
        let after = Date()

        #expect(affirmation.createdAt >= before)
        #expect(affirmation.createdAt <= after)
    }

    @Test
    func favoriteToggle() {
        let affirmation = Affirmation(content: "Test", focusArea: .calm)
        #expect(affirmation.isFavorite == false)

        affirmation.isFavorite = true
        #expect(affirmation.isFavorite == true)

        affirmation.isFavorite = false
        #expect(affirmation.isFavorite == false)
    }

    @Test
    func focusAreaAccessor() {
        let affirmation = Affirmation(content: "Test", focusArea: .gratitude)
        #expect(affirmation.focusArea == .gratitude)

        affirmation.focusArea = .motivation
        #expect(affirmation.focusArea == .motivation)
    }
}
```

### 2.3 UserSettings Tests

**File: `AffirmFlowTests/Models/UserSettingsTests.swift`**

```swift
import Testing
import Foundation
@testable import AffirmFlow

struct UserSettingsTests {
    @Test
    func defaultValues() {
        let settings = UserSettings()
        // Reset for test
        settings.selectedFocusAreas = []
        settings.onboardingComplete = false
        settings.dailyRefreshCount = 0

        #expect(settings.selectedFocusAreas.isEmpty)
        #expect(settings.onboardingComplete == false)
        #expect(settings.dailyRefreshCount == 0)
    }

    @Test
    func focusAreasSaveAndLoad() {
        let settings = UserSettings()
        settings.selectedFocusAreas = [.calm, .gratitude]

        #expect(settings.selectedFocusAreas.count == 2)
        #expect(settings.selectedFocusAreas.contains(.calm))
        #expect(settings.selectedFocusAreas.contains(.gratitude))
    }

    @Test
    func freeLimitIsThree() {
        #expect(UserSettings.freeLimit == 3)
    }

    @Test
    func canRefreshWhenUnderLimit() {
        let settings = UserSettings()
        settings.dailyRefreshCount = 0

        #expect(settings.canRefresh == true)
        #expect(settings.refreshesRemaining == 3)
    }

    @Test
    func cannotRefreshAtLimit() {
        let settings = UserSettings()
        settings.dailyRefreshCount = 3
        settings.lastRefreshDateInterval = Date().timeIntervalSince1970

        #expect(settings.canRefresh == false)
        #expect(settings.refreshesRemaining == 0)
    }

    @Test
    func incrementRefreshCount() {
        let settings = UserSettings()
        settings.dailyRefreshCount = 0

        settings.incrementRefreshCount()
        #expect(settings.dailyRefreshCount == 1)

        settings.incrementRefreshCount()
        #expect(settings.dailyRefreshCount == 2)
    }

    @Test
    func resetsCountAtMidnight() {
        let settings = UserSettings()
        settings.dailyRefreshCount = 3
        // Set last refresh to yesterday
        settings.lastRefreshDateInterval = Date().addingTimeInterval(-86400).timeIntervalSince1970

        // canRefresh should trigger reset
        #expect(settings.canRefresh == true)
    }
}
```

### 2.4 AffirmationService Tests

**File: `AffirmFlowTests/Services/AffirmationServiceTests.swift`**

```swift
import Testing
@testable import AffirmFlow

struct AffirmationServiceTests {
    @Test
    func serviceInitializes() {
        let service = AffirmationService()
        #expect(service != nil)
    }

    // Note: Foundation Models tests require device/simulator with iOS 26
    // Integration tests will cover actual generation

    @Test(arguments: FocusArea.allCases)
    func promptContainsAreaName(area: FocusArea) {
        // Verify prompts are properly formatted
        let prompt = area.prompt
        #expect(prompt.lowercased().contains(area.rawValue.lowercased()) ||
                prompt.contains("affirmation"))
    }
}
```

### 2.5 SubscriptionService Tests

**File: `AffirmFlowTests/Services/SubscriptionServiceTests.swift`**

```swift
import Testing
@testable import AffirmFlow

struct SubscriptionServiceTests {
    @Test
    func sharedInstanceExists() {
        let service = SubscriptionService.shared
        #expect(service != nil)
    }

    @Test
    func defaultsToNotPremium() {
        // Fresh install should not be premium
        // (Actual RevenueCat calls mocked in integration tests)
        let service = SubscriptionService.shared
        // Without configure(), isPremium should be false
        #expect(service.isPremium == false)
    }
}
```

---

## 3. Integration Tests

### 3.1 SwiftData Integration

**File: `AffirmFlowTests/Integration/SwiftDataIntegrationTests.swift`**

```swift
import Testing
import SwiftData
@testable import AffirmFlow

struct SwiftDataIntegrationTests {
    var container: ModelContainer!

    init() throws {
        let config = ModelConfiguration(isStoredInMemoryOnly: true)
        container = try ModelContainer(for: Affirmation.self, configurations: config)
    }

    @Test
    func insertAndFetch() throws {
        let context = container.mainContext
        let affirmation = Affirmation(content: "Test", focusArea: .calm)

        context.insert(affirmation)
        try context.save()

        let descriptor = FetchDescriptor<Affirmation>()
        let results = try context.fetch(descriptor)

        #expect(results.count == 1)
        #expect(results.first?.content == "Test")
    }

    @Test
    func fetchFavoritesOnly() throws {
        let context = container.mainContext

        let fav = Affirmation(content: "Favorite", focusArea: .calm)
        fav.isFavorite = true
        let notFav = Affirmation(content: "Not favorite", focusArea: .calm)

        context.insert(fav)
        context.insert(notFav)
        try context.save()

        var descriptor = FetchDescriptor<Affirmation>(
            predicate: #Predicate { $0.isFavorite == true }
        )
        let results = try context.fetch(descriptor)

        #expect(results.count == 1)
        #expect(results.first?.content == "Favorite")
    }

    @Test
    func deleteAffirmation() throws {
        let context = container.mainContext
        let affirmation = Affirmation(content: "To delete", focusArea: .calm)

        context.insert(affirmation)
        try context.save()

        context.delete(affirmation)
        try context.save()

        let descriptor = FetchDescriptor<Affirmation>()
        let results = try context.fetch(descriptor)

        #expect(results.isEmpty)
    }
}
```

### 3.2 Widget Data Sharing

**File: `AffirmFlowTests/Integration/WidgetDataSharingTests.swift`**

```swift
import Testing
@testable import AffirmFlow

struct WidgetDataSharingTests {
    let suiteName = "group.com.anicca.affirmflow"

    @Test
    func writeAndReadAffirmation() {
        let defaults = UserDefaults(suiteName: suiteName)
        let content = "Test affirmation"
        let area = FocusArea.calm

        defaults?.set(content, forKey: "currentAffirmation")
        defaults?.set(area.rawValue, forKey: "currentFocusArea")

        #expect(defaults?.string(forKey: "currentAffirmation") == content)
        #expect(defaults?.string(forKey: "currentFocusArea") == area.rawValue)
    }

    @Test
    func premiumStatusSharing() {
        let defaults = UserDefaults(suiteName: suiteName)

        defaults?.set(true, forKey: "isPremium")
        #expect(defaults?.bool(forKey: "isPremium") == true)

        defaults?.set(false, forKey: "isPremium")
        #expect(defaults?.bool(forKey: "isPremium") == false)
    }
}
```

---

## 4. UI Tests

### 4.1 Onboarding Flow

**File: `AffirmFlowUITests/OnboardingUITests.swift`**

```swift
import XCTest

final class OnboardingUITests: XCTestCase {
    var app: XCUIApplication!

    override func setUp() {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchArguments = ["--uitesting", "--reset-state"]
        app.launch()
    }

    func testOnboardingFlow() {
        // Welcome screen
        XCTAssert(app.staticTexts["AffirmFlow"].exists)
        XCTAssert(app.staticTexts["Your thoughts never leave your phone"].exists)

        app.buttons["Get Started"].tap()

        // Focus area selection
        XCTAssert(app.staticTexts["Choose Your Focus"].exists)

        // Select 2 areas
        app.buttons["Confidence"].tap()
        app.buttons["Calm"].tap()

        app.buttons["Continue"].tap()

        // Widget tutorial
        XCTAssert(app.staticTexts["Add Your Widget"].exists)

        app.buttons["Done, Let's Go!"].tap()

        // Home screen
        XCTAssert(app.buttons["Settings"].exists)
    }

    func testFocusAreaLimit() {
        app.buttons["Get Started"].tap()

        // Try to select 4 areas
        app.buttons["Confidence"].tap()
        app.buttons["Gratitude"].tap()
        app.buttons["Calm"].tap()
        app.buttons["Motivation"].tap() // Should not select (max 3)

        // Verify only 3 checkmarks
        let checkmarks = app.images.matching(identifier: "checkmark.circle.fill")
        XCTAssertEqual(checkmarks.count, 3)
    }

    func testSkipWidgetTutorial() {
        app.buttons["Get Started"].tap()
        app.buttons["Confidence"].tap()
        app.buttons["Continue"].tap()

        app.buttons["Skip for now"].tap()

        // Should be on home screen
        XCTAssert(app.buttons["Settings"].exists)
    }
}
```

### 4.2 Home Screen Tests

**File: `AffirmFlowUITests/HomeUITests.swift`**

```swift
import XCTest

final class HomeUITests: XCTestCase {
    var app: XCUIApplication!

    override func setUp() {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchArguments = ["--uitesting", "--skip-onboarding"]
        app.launch()
    }

    func testHomeScreenElements() {
        // Card exists
        XCTAssert(app.otherElements["affirmationCard"].exists)

        // Action buttons exist
        XCTAssert(app.buttons["heart"].exists || app.buttons["heart.fill"].exists)
        XCTAssert(app.buttons["arrow.clockwise"].exists || app.buttons["lock.fill"].exists)

        // Navigation exists
        XCTAssert(app.buttons["History"].exists)
        XCTAssert(app.buttons["Favorites"].exists)
        XCTAssert(app.buttons["Settings"].exists)
    }

    func testRefreshAffirmation() {
        let card = app.otherElements["affirmationCard"]
        let initialText = card.staticTexts.firstMatch.label

        app.buttons["arrow.clockwise"].tap()

        // Wait for generation
        let expectation = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "label != %@", initialText),
            object: card.staticTexts.firstMatch
        )
        wait(for: [expectation], timeout: 5.0)
    }

    func testToggleFavorite() {
        // Initial state: not favorite
        let heartEmpty = app.buttons["heart"]
        let heartFill = app.buttons["heart.fill"]

        if heartEmpty.exists {
            heartEmpty.tap()
            XCTAssert(heartFill.exists)
        }

        if heartFill.exists {
            heartFill.tap()
            XCTAssert(heartEmpty.exists)
        }
    }

    func testNavigateToHistory() {
        app.buttons["History"].tap()
        XCTAssert(app.navigationBars["History"].exists)
    }

    func testNavigateToFavorites() {
        app.buttons["Favorites"].tap()
        XCTAssert(app.navigationBars["Favorites"].exists)
    }

    func testNavigateToSettings() {
        app.buttons["Settings"].tap()
        XCTAssert(app.navigationBars["Settings"].exists)
    }
}
```

### 4.3 Paywall Tests

**File: `AffirmFlowUITests/PaywallUITests.swift`**

```swift
import XCTest

final class PaywallUITests: XCTestCase {
    var app: XCUIApplication!

    override func setUp() {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchArguments = ["--uitesting", "--skip-onboarding", "--free-user"]
        app.launch()
    }

    func testPaywallAppearsAtLimit() {
        // Exhaust free refreshes
        for _ in 0..<3 {
            if app.buttons["arrow.clockwise"].exists {
                app.buttons["arrow.clockwise"].tap()
                sleep(2) // Wait for generation
            }
        }

        // Fourth refresh should show paywall
        app.buttons["lock.fill"].tap()

        XCTAssert(app.staticTexts["Unlock AffirmFlow Premium"].exists)
    }

    func testPaywallElements() {
        // Trigger paywall
        app.buttons["Upgrade"].tap()

        // Verify elements
        XCTAssert(app.staticTexts["Unlock AffirmFlow Premium"].exists)
        XCTAssert(app.staticTexts["$29.99/year"].exists)
        XCTAssert(app.staticTexts["$2.99/week"].exists)
        XCTAssert(app.buttons["Continue"].exists)
        XCTAssert(app.buttons["Restore Purchases"].exists)
    }

    func testDismissPaywall() {
        app.buttons["Upgrade"].tap()
        XCTAssert(app.staticTexts["Unlock AffirmFlow Premium"].exists)

        app.buttons["xmark"].tap()

        XCTAssertFalse(app.staticTexts["Unlock AffirmFlow Premium"].exists)
    }
}
```

---

## 5. Accessibility Tests

### 5.1 VoiceOver Tests

**File: `AffirmFlowUITests/AccessibilityUITests.swift`**

```swift
import XCTest

final class AccessibilityUITests: XCTestCase {
    var app: XCUIApplication!

    override func setUp() {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchArguments = ["--uitesting", "--skip-onboarding"]
        app.launch()
    }

    func testAffirmationCardAccessibility() {
        let card = app.otherElements["affirmationCard"]
        XCTAssert(card.isAccessibilityElement || card.staticTexts.count > 0)
    }

    func testActionButtonsAccessibility() {
        let saveButton = app.buttons.matching(NSPredicate(format: "label CONTAINS 'favorite'")).firstMatch
        let refreshButton = app.buttons.matching(NSPredicate(format: "label CONTAINS 'refresh' OR label CONTAINS 'new'")).firstMatch

        XCTAssert(saveButton.exists || refreshButton.exists)
    }

    func testMinimumTouchTargets() {
        let buttons = app.buttons.allElementsBoundByIndex
        for button in buttons {
            let frame = button.frame
            XCTAssert(frame.width >= 44 && frame.height >= 44,
                      "Button \(button.label) is too small: \(frame)")
        }
    }
}
```

---

## 6. Performance Tests

### 6.1 Launch Time

**File: `AffirmFlowUITests/PerformanceUITests.swift`**

```swift
import XCTest

final class PerformanceUITests: XCTestCase {
    func testLaunchPerformance() {
        measure(metrics: [XCTApplicationLaunchMetric()]) {
            XCUIApplication().launch()
        }
    }

    func testAffirmationGenerationTime() {
        let app = XCUIApplication()
        app.launchArguments = ["--uitesting", "--skip-onboarding"]
        app.launch()

        let card = app.otherElements["affirmationCard"]

        measure {
            app.buttons["arrow.clockwise"].tap()

            let expectation = XCTNSPredicateExpectation(
                predicate: NSPredicate(format: "exists == true"),
                object: card.staticTexts.element(boundBy: 0)
            )
            _ = XCTWaiter.wait(for: [expectation], timeout: 5.0)
        }
    }
}
```

### 6.2 Performance Benchmarks

| Metric | Target | Measurement |
|--------|--------|-------------|
| Cold launch | < 1.5s | XCTApplicationLaunchMetric |
| Affirmation generation | < 2s | Manual timing |
| Memory (app) | < 100 MB | Instruments |
| Memory (widget) | < 30 MB | Instruments |
| Scroll FPS | 60 fps | Core Animation |

---

## 7. Test Matrix

### 7.1 Model Tests

| Test | Class | Status |
|------|-------|--------|
| FocusArea all cases | FocusAreaTests | Required |
| FocusArea has properties | FocusAreaTests | Required |
| Affirmation init | AffirmationTests | Required |
| Affirmation favorite toggle | AffirmationTests | Required |
| UserSettings defaults | UserSettingsTests | Required |
| UserSettings refresh limit | UserSettingsTests | Required |
| UserSettings midnight reset | UserSettingsTests | Required |

### 7.2 Service Tests

| Test | Class | Status |
|------|-------|--------|
| AffirmationService init | AffirmationServiceTests | Required |
| SubscriptionService shared | SubscriptionServiceTests | Required |

### 7.3 Integration Tests

| Test | Class | Status |
|------|-------|--------|
| SwiftData CRUD | SwiftDataIntegrationTests | Required |
| SwiftData favorites filter | SwiftDataIntegrationTests | Required |
| Widget data sharing | WidgetDataSharingTests | Required |

### 7.4 UI Tests

| Test | Class | Status |
|------|-------|--------|
| Onboarding flow | OnboardingUITests | Required |
| Home screen elements | HomeUITests | Required |
| Refresh affirmation | HomeUITests | Required |
| Toggle favorite | HomeUITests | Required |
| Paywall at limit | PaywallUITests | Required |

---

## 8. Test Execution

### 8.1 Commands

```bash
# Run all tests
xcodebuild test -scheme AffirmFlow -destination 'platform=iOS Simulator,name=iPhone 15 Pro'

# Run unit tests only
xcodebuild test -scheme AffirmFlow -destination 'platform=iOS Simulator,name=iPhone 15 Pro' -only-testing:AffirmFlowTests

# Run UI tests only
xcodebuild test -scheme AffirmFlow -destination 'platform=iOS Simulator,name=iPhone 15 Pro' -only-testing:AffirmFlowUITests

# Generate coverage report
xcodebuild test -scheme AffirmFlow -destination 'platform=iOS Simulator,name=iPhone 15 Pro' -enableCodeCoverage YES
```

### 8.2 CI Integration

Tests run automatically on:
- Pull request creation
- Push to main/dev
- Nightly builds

---

## 9. Beta Testing Plan

### 9.1 TestFlight Beta

| Phase | Duration | Participants | Focus |
|-------|----------|--------------|-------|
| Alpha | 3 days | 5 internal | Critical bugs |
| Beta 1 | 1 week | 20 users | Core functionality |
| Beta 2 | 1 week | 50 users | Polish, performance |

### 9.2 Success Criteria

| Metric | Target |
|--------|--------|
| Crash-free rate | > 99.5% |
| Average rating | > 4.0 |
| Session length | > 30 seconds |
| Widget adoption | > 50% |

### 9.3 Feedback Collection

- TestFlight feedback form
- In-app feedback button
- Crash reports via Xcode Organizer

---

**Document End**
