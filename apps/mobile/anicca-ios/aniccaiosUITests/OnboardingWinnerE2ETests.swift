import XCTest
import StoreKitTest

/// StoreKit's local session is active before launch: no sandbox account login.
@MainActor
final class OnboardingWinnerE2ETests: XCTestCase {
    private var storeKit: SKTestSession!

    override func setUpWithError() throws {
        continueAfterFailure = false
        storeKit = try SKTestSession(configurationFileNamed: "Anicca")
        storeKit.resetToDefaultState()
        storeKit.disableDialogs = true
        storeKit.clearTransactions()
    }

    func testStandardJourneyClosesPaywallIntoSameIntervention() throws {
        let app = XCUIApplication()
        // No -aniccaRecordingMode here: with auto-advance on, the deck moves
        // past the first card before the closing assertion can read it on a
        // slow CI runner (the same race build-830's Maestro run hit). The
        // recording-mode home capture lives in the second test below.
        app.launchArguments = ["-resetOnLaunch", "-uiTesting", "-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
        app.launch()
        let start = Date()
        func tap(_ id: String) {
            let element = app.buttons[id]
            XCTAssertTrue(element.waitForExistence(timeout: 30), id)
            for _ in 0..<6 where !element.isHittable { app.swipeUp() }
            XCTAssertTrue(element.isHittable, id)
            let enabled = XCTNSPredicateExpectation(predicate: NSPredicate(format: "enabled == true"), object: element)
            XCTAssertEqual(XCTWaiter.wait(for: [enabled], timeout: 15), .completed)
            XCTAssertFalse(XCUIApplication(bundleIdentifier: "com.apple.springboard").alerts.staticTexts.matching(NSPredicate(format: "label CONTAINS[c] 'Apple Account' OR label CONTAINS[c] 'Apple ID'")).firstMatch.exists)
            element.tap()
        }
        func answer(_ question: String, _ value: String) {
            tap("onboarding-\(question)-\(value)")
            tap("onboarding-\(question)-continue")
        }
        tap("onboarding-welcome-cta")
        tap("onboarding-goal-calm")
        tap("onboarding-goal-continue")
        answer("focus_categories", "anxiety")
        tap("onboarding-name-continue")
        tap("onboarding-birth_context-skip")
        answer("mood_baseline", "heavy")
        tap("onboarding-struggle-stress")
        tap("onboarding-struggles-next")
        answer("stress_trigger", "work")
        tap("onboarding-depth-daily")
        tap("onboarding-depth-continue")
        answer("belief_themes", "inner_peace")
        tap("onboarding-micro-save")
        answer("tone", "gentle")
        answer("life_context", "work")
        answer("routine_anchors", "lunch")
        answer("prior_attempts", "first_time")
        answer("start_reason", "overwhelmed")
        answer("quiet_hours", "overnight")
        tap("theme-sandWave")
        tap("onboarding-theme-continue")
        tap("onboarding-icon-AppIcon")
        tap("onboarding-icon-continue")
        tap("onboarding-widget-later")
        let reveal = app.staticTexts["onboarding-first-affirmation"]
        XCTAssertTrue(reveal.waitForExistence(timeout: 30))
        let words = reveal.label
        tap("onboarding-first-save")
        tap("onboarding-first-continue")
        tap("onboarding-reminder-continue")
        tap("onboarding-notifications-skip")
        XCTAssertTrue(app.buttons["paywall-plan-annual"].waitForExistence(timeout: 30))
        XCTAssertTrue(app.buttons["paywall-plan-weekly"].exists)
        XCTAssertTrue(app.buttons["paywall-plan-lifetime"].exists)
        XCTAssertFalse(app.buttons["paywall-plan-monthly"].exists)
        XCTAssertTrue(app.staticTexts["paywall-monthly-equivalent"].label.contains("5.00"))
        XCTAssertTrue(app.otherElements["paywall-trial-timeline"].exists || app.staticTexts["paywall-trial-timeline"].exists)
        let time = XCTAttachment(string: "paywall_arrival_seconds=\(Date().timeIntervalSince(start))")
        time.lifetime = .keepAlways
        add(time)
        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = "winner-three-plan-paywall"
        screenshot.lifetime = .keepAlways
        add(screenshot)
        tap("paywall-close-button")
        XCTAssertTrue(app.staticTexts["quote-text"].waitForExistence(timeout: 30))
        XCTAssertEqual(app.staticTexts["quote-text"].label, words)
    }

    /// Second launch in the same recording: onboarding is already complete,
    /// so the app lands directly on the living home. With
    /// -aniccaRecordingMode the deck auto-advances every 3s; dwelling here
    /// is what captures the words actually changing in the recorded video.
    /// Labels are attached as evidence only — the frame-level check happens
    /// on the video itself. Named to sort after the journey test.
    func testZRecordingHomeAutoAdvance() throws {
        let app = XCUIApplication()
        app.launchArguments = ["-uiTesting", "-aniccaRecordingMode", "-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
        app.launch()
        let quote = app.staticTexts["quote-text"]
        XCTAssertTrue(quote.waitForExistence(timeout: 30))
        let arrival = XCTAttachment(string: "home_quote_at_arrival=\(quote.label)")
        arrival.lifetime = .keepAlways
        add(arrival)
        Thread.sleep(forTimeInterval: 15)
        let afterDwell = XCTAttachment(string: "home_quote_after_15s=\(app.staticTexts["quote-text"].label)")
        afterDwell.lifetime = .keepAlways
        add(afterDwell)
        let homeScreenshot = XCTAttachment(screenshot: app.screenshot())
        homeScreenshot.name = "living-home-after-dwell"
        homeScreenshot.lifetime = .keepAlways
        add(homeScreenshot)
    }
}
