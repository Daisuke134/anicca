import XCTest
@testable import EyeBreakIsland

final class ConstantsTests: XCTestCase {

    func testDefaultWorkIntervalMinutesIs20() {
        XCTAssertEqual(Constants.defaultWorkIntervalMinutes, 20)
    }

    func testDefaultBreakDurationSecondsIs20() {
        XCTAssertEqual(Constants.defaultBreakDurationSeconds, 20)
    }

    func testDefaultWorkIntervalSecondsIs1200() {
        XCTAssertEqual(Constants.defaultWorkIntervalSeconds, 1200)
    }

    func testHasCompletedOnboardingKey() {
        XCTAssertEqual(Constants.hasCompletedOnboardingKey, "hasCompletedOnboarding")
    }

    func testAccessibilityIDTimerStart() {
        XCTAssertEqual(AccessibilityID.timerStartButton, "timer_start_button")
    }

    func testAccessibilityIDPaywallMaybeLater() {
        XCTAssertEqual(AccessibilityID.paywallMaybeLater, "paywall_maybe_later")
    }
}
