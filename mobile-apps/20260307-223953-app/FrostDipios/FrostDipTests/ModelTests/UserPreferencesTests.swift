import XCTest
@testable import FrostDip

final class UserPreferencesTests: XCTestCase {
    private var defaults: UserDefaults!
    private var prefs: UserPreferences!

    override func setUp() {
        super.setUp()
        defaults = UserDefaults(suiteName: "test_\(UUID().uuidString)")!
        prefs = UserPreferences(defaults: defaults)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: defaults.description)
        super.tearDown()
    }

    func testTemperatureUnit_defaultsCelsius() {
        XCTAssertEqual(prefs.temperatureUnit, .celsius)
    }

    func testTemperatureUnit_setFahrenheit() {
        prefs.temperatureUnit = .fahrenheit
        XCTAssertEqual(prefs.temperatureUnit, .fahrenheit)
    }

    func testNotificationsEnabled_defaultsFalse() {
        XCTAssertFalse(prefs.notificationsEnabled)
    }

    func testHasCompletedOnboarding_defaultsFalse() {
        XCTAssertFalse(prefs.hasCompletedOnboarding)
    }

    func testHasCompletedOnboarding_setTrue() {
        prefs.hasCompletedOnboarding = true
        XCTAssertTrue(prefs.hasCompletedOnboarding)
    }

    func testExperienceLevel_defaultsBeginner() {
        XCTAssertEqual(prefs.experienceLevel, .beginner)
    }

    func testExperienceLevel_setAdvanced() {
        prefs.experienceLevel = .advanced
        XCTAssertEqual(prefs.experienceLevel, .advanced)
    }

    func testStreak_defaultsZero() {
        XCTAssertEqual(prefs.currentStreak, 0)
        XCTAssertEqual(prefs.longestStreak, 0)
    }

    func testStreak_increment() {
        prefs.currentStreak = 5
        prefs.longestStreak = 10
        XCTAssertEqual(prefs.currentStreak, 5)
        XCTAssertEqual(prefs.longestStreak, 10)
    }

    func testLastPlungeDate_defaultsNil() {
        XCTAssertNil(prefs.lastPlungeDate)
    }

    func testReminderTime_setAndGet() {
        let date = Date()
        prefs.reminderTime = date
        XCTAssertNotNil(prefs.reminderTime)
        XCTAssertEqual(prefs.reminderTime!.timeIntervalSince1970, date.timeIntervalSince1970, accuracy: 1.0)
    }

    func testAppLaunchCount_defaultsZero() {
        XCTAssertEqual(prefs.appLaunchCount, 0)
    }
}
