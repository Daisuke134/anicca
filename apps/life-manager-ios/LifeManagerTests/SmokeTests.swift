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

    func testJapaneseCatalogRendersInTheTestEnvironment() {
        let app = XCUIApplication()
        app.launchArguments = ["-uiTesting", "-AppleLanguages", "(ja)", "-AppleLocale", "ja_JP"]
        app.launchEnvironment["LIFEMANAGER_TESTING"] = "1"

        app.launch()

        XCTAssertTrue(
            app.staticTexts["カレンダーに接続して、次に進む一歩を明確にしましょう。"].waitForExistence(timeout: 10),
            "Japanese catalog should render in the test environment"
        )
    }
}
