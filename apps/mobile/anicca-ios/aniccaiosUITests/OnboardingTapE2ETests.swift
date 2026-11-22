import XCTest

/// Release gate: one normal coordinate tap per action, including blank label padding.
/// Each case requires a fresh simulator and live RevenueCat configuration plus local StoreKit test products; no route or entitlement bypass.
final class OnboardingTapE2ETests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    @MainActor
    func testFullOnboardingCenterTaps() {
        completeOnboarding(tapX: 0.5, pains: ["stress", "anxiety"], triedBefore: false)
    }

    @MainActor
    func testFullOnboardingLeadingPaddingTaps() {
        completeOnboarding(tapX: 0.12, pains: ["self_doubt", "procrastination"], triedBefore: true)
    }

    @MainActor
    func testFullOnboardingTrailingPaddingTaps() {
        completeOnboarding(tapX: 0.88, pains: ["sleep", "stress"], triedBefore: true)
    }

    @MainActor
    private func completeOnboarding(tapX: CGFloat, pains: [String], triedBefore: Bool) {
        let app = XCUIApplication()
        // Lowercase -uiTesting suppresses the nondeterministic StoreKit rating prompt.
        // Uppercase UITESTING would disable RevenueCat and is deliberately not used.
        app.launchArguments = ["-uiTesting", "-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
        app.launch()

        tap(app.buttons["onboarding-welcome-cta"], x: tapX)
        XCTAssertTrue(app.buttons["onboarding-goal-calm"].waitForExistence(timeout: 30),
                      "A single normal welcome tap must advance to goal selection")
        select(app.buttons["onboarding-goal-calm"], in: app, x: tapX)
        tap(app.buttons["onboarding-goal-continue"], x: tapX)
        answer("focus_categories", "anxiety", in: app, x: tapX)
        tap(app.buttons["onboarding-name-continue"], x: tapX) // Name is optional.
        answer("birth_context", "aries", in: app, x: tapX)
        answer("mood_baseline", "neutral", in: app, x: tapX)
        let next = app.buttons["onboarding-struggles-next"]
        XCTAssertTrue(next.waitForExistence(timeout: 10))
        XCTAssertFalse(next.isEnabled, "Pain points must require a selection")
        for pain in pains {
            select(app.buttons["onboarding-struggle-\(pain)"], in: app, x: tapX)
        }
        tap(next, x: tapX)
        // The three cases cover all five deep-dive modules, including sleep's three screens.
        for pain in pains {
            switch pain {
            case "stress": answer("stress_trigger", "work", in: app, x: tapX)
            case "anxiety": answer("anxiety_target", "future", in: app, x: tapX)
            case "self_doubt": answer("self_criticism", "work", in: app, x: tapX)
            case "procrastination": answer("avoidance_task", "work", in: app, x: tapX)
            case "sleep":
                answer("sleep_reason", "racing_mind", in: app, x: tapX)
                answer("bedtime", "before_22", in: app, x: tapX)
                answer("wake_time", "before_6", in: app, x: tapX)
            default: XCTFail("Uncovered pain branch: \(pain)")
            }
        }
        select(app.buttons["onboarding-depth-daily"], in: app, x: tapX)
        tap(app.buttons["onboarding-depth-continue"], x: tapX)
        answer("belief_themes", "self_trust", in: app, x: tapX)
        XCTAssertTrue(app.staticTexts["onboarding-micro-preview"].waitForExistence(timeout: 10))
        tap(app.buttons["onboarding-micro-save"], x: tapX)
        answer("tone", "gentle", in: app, x: tapX)
        answer("life_context", "work", in: app, x: tapX)
        answer("routine_anchors", "waking", in: app, x: tapX)
        answer("prior_attempts", triedBefore ? "meditation" : "first_time", in: app, x: tapX)
        if triedBefore { answer("prior_helpfulness", "meditation", in: app, x: tapX) }
        answer("start_reason", "overwhelmed", in: app, x: tapX)
        answer("quiet_hours", "none", in: app, x: tapX)
        select(app.buttons["theme-sandWave"], in: app, x: tapX)
        tap(app.buttons["onboarding-theme-continue"], x: tapX)
        // Keep the primary icon: changing it presents a separate OS confirmation.
        tap(app.buttons["onboarding-icon-AppIcon"], x: tapX)
        tap(app.buttons["onboarding-icon-continue"], x: tapX)
        XCTAssertTrue(app.descendants(matching: .any).matching(identifier: "onboarding-widget-preview").firstMatch.waitForExistence(timeout: 10))
        tap(app.buttons["onboarding-widget-interested"], x: tapX)
        tap(app.buttons["onboarding-first-continue"], x: tapX)
        // Timing is the model's decision (founder rule 2026-11-22): the
        // reminder step no longer asks for slots or frequency.
        tap(app.buttons["onboarding-reminder-continue"], x: tapX)
        tap(app.buttons["onboarding-notifications-allow"], x: tapX)

        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        let deny = springboard.buttons.matching(NSPredicate(format: "label IN %@", ["Don't Allow", "Don’t Allow"])).firstMatch
        XCTAssertTrue(deny.waitForExistence(timeout: 10), "Fresh install must request notification permission")
        tap(deny, x: 0.5)

        let purchase = app.buttons["paywall-plan-cta"]
        XCTAssertTrue(purchase.waitForExistence(timeout: 60), "Configured paywall products must load")
        XCTAssertTrue(purchase.isEnabled, "An unloaded product is not a passing gate")
        tap(app.buttons["paywall-close-button"], x: 0.5)
        // The home deck is a UIPageViewController; do not assume its AX element type.
        XCTAssertTrue(app.descendants(matching: .any).matching(identifier: "feed-today").firstMatch.waitForExistence(timeout: 20),
                      "Paywall close must finish onboarding without a purchase")
        XCTAssertFalse(app.buttons["paywall-close-button"].exists)
        XCTAssertFalse(app.buttons["onboarding-welcome-cta"].exists)
        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = "completed-onboarding-tap-x-\(tapX)"
        screenshot.lifetime = .keepAlways
        add(screenshot)

        app.terminate()
        app.launchArguments = ["-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
        app.launch()
        XCTAssertTrue(app.descendants(matching: .any).matching(identifier: "feed-today").firstMatch.waitForExistence(timeout: 20),
                      "Completion must persist across a normal relaunch")
        XCTAssertFalse(app.buttons["paywall-close-button"].exists)
        XCTAssertFalse(app.buttons["onboarding-welcome-cta"].exists)
    }

    @MainActor
    private func answer(_ question: String, _ option: String, in app: XCUIApplication, x: CGFloat) {
        select(app.buttons["onboarding-\(question)-\(option)"], in: app, x: x)
        tap(app.buttons["onboarding-\(question)-continue"], x: x)
    }

    @MainActor
    private func select(_ element: XCUIElement, in app: XCUIApplication, x: CGFloat) {
        XCTAssertTrue(element.waitForExistence(timeout: 30))
        // Require the entire row inside the actual viewport, not an extra margin:
        // ThemePickerView has 16pt padding and its single free-theme row cannot
        // scroll far enough to satisfy the old artificial 20pt inset.
        let scroll = app.scrollViews.firstMatch
        XCTAssertTrue(scroll.waitForExistence(timeout: 10))
        for scrollAttempt in 0...8 {
            let visible = scroll.frame.intersection(app.frame)
            let row = element.frame
            if !visible.isEmpty && !row.isEmpty && visible.contains(row) && element.isHittable { break }
            // Check again after the eighth swipe before reporting failure.
            guard scrollAttempt < 8 else {
                let screenshot = XCTAttachment(screenshot: app.screenshot())
                screenshot.name = "unexposed-\(element.identifier)"
                screenshot.lifetime = .keepAlways
                add(screenshot)
                XCTFail("Could not expose the complete row: \(element.identifier); row=\(row), viewport=\(visible), hittable=\(element.isHittable)")
                return
            }
            // Scroll only to expose a row; never repeat its tap to mask a missed touch.
            if row.midY < visible.midY { scroll.swipeDown() }
            else { scroll.swipeUp() }
        }
        tap(element, x: x)
        let selected = XCTNSPredicateExpectation(predicate: NSPredicate(format: "selected == true"), object: element)
        XCTAssertEqual(XCTWaiter.wait(for: [selected], timeout: 5), .completed,
                       "A single normal tap must select the row")
    }

    @MainActor
    private func tap(_ element: XCUIElement, x: CGFloat,
                     file: StaticString = #filePath, line: UInt = #line) {
        XCTAssertTrue(element.waitForExistence(timeout: 30), "Missing \(element)", file: file, line: line)
        // The cold simulator in run 44509771791 computed a valid hit point,
        // then the 10s outer waiter interrupted the next AX query. Avoid the
        // element-backed predicate's diagnostic description work during polling
        // and allow the same 30s readiness budget as waitForExistence above.
        let ready = NSPredicate { _, _ in
            element.exists && element.isEnabled && element.isHittable
        }
        let expectation = XCTNSPredicateExpectation(predicate: ready, object: nil)
        guard XCTWaiter.wait(for: [expectation], timeout: 30) == .completed else {
            let screenshot = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
            screenshot.name = "untappable-cta"
            screenshot.lifetime = .keepAlways
            add(screenshot)
            XCTFail("CTA never became tappable: \(element.debugDescription)", file: file, line: line)
            return
        }
        element.coordinate(withNormalizedOffset: CGVector(dx: x, dy: 0.5)).tap()
    }
}
