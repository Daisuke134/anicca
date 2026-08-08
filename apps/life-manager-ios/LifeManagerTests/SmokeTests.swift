import XCTest

final class LifeManagerSmokeTests: XCTestCase {
    func testLaunchesLifeManagerInTestEnvironment() {
        let app = XCUIApplication()
        app.launchArguments = ["-uiTesting"]
        app.launchEnvironment["LIFEMANAGER_TESTING"] = "1"

        app.launch()

        XCTAssertTrue(
            app.staticTexts["Life Manager"].waitForExistence(timeout: 10),
            "Life Manager should launch with its test environment"
        )
    }
}
