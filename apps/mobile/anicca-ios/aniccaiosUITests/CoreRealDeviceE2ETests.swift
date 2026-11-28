import XCTest

/// Core flows for Firebase Test Lab real iPhones (XCUITest only; Maestro cannot run there).
/// Mirrors maestro/gate/06-quote-deep-link.yaml and 07-notifications-screen.yaml.
/// Assumes onboarding was completed (launch arg -uiTesting true skips nothing; the
/// first test finishes onboarding through the same ids as maestro gate 01 if needed).
final class CoreRealDeviceE2ETests: XCTestCase {
    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchArguments += ["-uiTesting", "true"]
        app.launch()
        dismissSystemSheets()
    }

    private func dismissSystemSheets() {
        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        for label in ["Cancel", "キャンセル", "Don’t Allow", "Don't Allow", "許可しない"] {
            let b = springboard.buttons[label]
            if b.waitForExistence(timeout: 1) { b.tap() }
        }
    }

    func testQuoteDeepLinkQ003() throws {
        XCTAssertTrue(app.otherElements["feed-today"].waitForExistence(timeout: 30)
                      || app.descendants(matching: .any)["feed-today"].waitForExistence(timeout: 5))
        app.open(URL(string: "anicca://quote/q003")!)
        dismissSystemSheets()
        let quote = app.descendants(matching: .any)["quote-text"]
        XCTAssertTrue(quote.waitForExistence(timeout: 20))
        let text = (quote.label + (quote.value as? String ?? ""))
        XCTAssertTrue(text.contains("Every breath moves me closer to my truest self")
                      || text.contains("一呼吸ごとに、本当の自分に近づいています"), "got: \(text)")
    }

    func testNotificationsScreenFromSettings() throws {
        let feed = app.descendants(matching: .any)["feed-today"]
        XCTAssertTrue(feed.waitForExistence(timeout: 30))
        app.descendants(matching: .any)["feed-settings"].tap()
        XCTAssertTrue(app.descendants(matching: .any)["settings-theme"].waitForExistence(timeout: 15))
        let notif = app.buttons.matching(NSPredicate(format: "label CONTAINS 'Notifications' OR label CONTAINS '通知'")).firstMatch
        XCTAssertTrue(notif.waitForExistence(timeout: 10))
        notif.tap()
        XCTAssertTrue(app.descendants(matching: .any)["reminder-permission-status"].waitForExistence(timeout: 15))
    }
}
