import XCTest
@testable import FrostDip

final class StreakServiceTests: XCTestCase {
    private var defaults: UserDefaults!
    private var prefs: UserPreferences!

    override func setUp() {
        super.setUp()
        defaults = UserDefaults(suiteName: "streak_test_\(UUID().uuidString)")!
        prefs = UserPreferences(defaults: defaults)
    }

    func testRecordSession_firstSession_setsStreakToOne() {
        let service = StreakService(preferences: prefs)
        service.recordSession()
        XCTAssertEqual(prefs.currentStreak, 1)
        XCTAssertEqual(prefs.longestStreak, 1)
    }

    func testRecordSession_sameDayDuplicate_doesNotIncrement() {
        let service = StreakService(preferences: prefs)
        prefs.currentStreak = 3
        prefs.longestStreak = 3
        prefs.lastPlungeDate = Date()

        service.recordSession()
        XCTAssertEqual(prefs.currentStreak, 3)
    }

    func testRecordSession_consecutiveDay_increments() {
        let calendar = Calendar.current
        let yesterday = calendar.date(byAdding: .day, value: -1, to: Date())!
        prefs.currentStreak = 3
        prefs.longestStreak = 5
        prefs.lastPlungeDate = yesterday

        let service = StreakService(preferences: prefs, calendar: calendar)
        service.recordSession()
        XCTAssertEqual(prefs.currentStreak, 4)
    }

    func testRecordSession_gapMoreThanOneDay_resetsToOne() {
        let calendar = Calendar.current
        let threeDaysAgo = calendar.date(byAdding: .day, value: -3, to: Date())!
        prefs.currentStreak = 5
        prefs.longestStreak = 10
        prefs.lastPlungeDate = threeDaysAgo

        let service = StreakService(preferences: prefs, calendar: calendar)
        service.recordSession()
        XCTAssertEqual(prefs.currentStreak, 1)
    }

    func testRecordSession_updatesLongestStreak() {
        let calendar = Calendar.current
        let yesterday = calendar.date(byAdding: .day, value: -1, to: Date())!
        prefs.currentStreak = 10
        prefs.longestStreak = 10
        prefs.lastPlungeDate = yesterday

        let service = StreakService(preferences: prefs, calendar: calendar)
        service.recordSession()
        XCTAssertEqual(prefs.longestStreak, 11)
    }

    func testRecordSession_streakFreeze_twoDayGap() {
        let calendar = Calendar.current
        let twoDaysAgo = calendar.date(byAdding: .day, value: -2, to: Date())!
        prefs.currentStreak = 5
        prefs.longestStreak = 5
        prefs.lastPlungeDate = twoDaysAgo
        prefs.streakFreezeUsedThisWeek = false

        let service = StreakService(preferences: prefs, calendar: calendar)
        service.recordSession()
        XCTAssertEqual(prefs.currentStreak, 6)
        XCTAssertTrue(prefs.streakFreezeUsedThisWeek)
    }

    func testRecordSession_streakFreezeAlreadyUsed_resets() {
        let calendar = Calendar.current
        let twoDaysAgo = calendar.date(byAdding: .day, value: -2, to: Date())!
        prefs.currentStreak = 5
        prefs.longestStreak = 5
        prefs.lastPlungeDate = twoDaysAgo
        prefs.streakFreezeUsedThisWeek = true

        let service = StreakService(preferences: prefs, calendar: calendar)
        service.recordSession()
        XCTAssertEqual(prefs.currentStreak, 1)
    }
}
