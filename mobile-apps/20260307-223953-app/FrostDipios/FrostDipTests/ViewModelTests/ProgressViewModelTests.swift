import XCTest
@testable import FrostDip

final class ProgressViewModelTests: XCTestCase {
    private var sut: ProgressViewModel!
    private var defaults: UserDefaults!

    override func setUp() {
        super.setUp()
        defaults = UserDefaults(suiteName: "ProgressViewModelTests")!
        defaults.removePersistentDomain(forName: "ProgressViewModelTests")
        sut = ProgressViewModel(defaults: defaults)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: "ProgressViewModelTests")
        sut = nil
        defaults = nil
        super.tearDown()
    }

    // MARK: - Streak

    func testCurrentStreakReadsFromPrefs() {
        let prefs = UserPreferences(defaults: defaults)
        prefs.currentStreak = 5
        sut = ProgressViewModel(defaults: defaults)
        XCTAssertEqual(sut.currentStreak, 5)
    }

    func testLongestStreakReadsFromPrefs() {
        let prefs = UserPreferences(defaults: defaults)
        prefs.longestStreak = 12
        sut = ProgressViewModel(defaults: defaults)
        XCTAssertEqual(sut.longestStreak, 12)
    }

    // MARK: - Stats Aggregation

    func testTotalSessionsWithEmptyData() {
        sut.updateSessions([])
        XCTAssertEqual(sut.totalSessions, 0)
    }

    func testTotalSessionsWithData() {
        let sessions = [
            PlungeSession(duration: 120),
            PlungeSession(duration: 180)
        ]
        sut.updateSessions(sessions)
        XCTAssertEqual(sut.totalSessions, 2)
    }

    func testAverageDuration() {
        let sessions = [
            PlungeSession(duration: 120),
            PlungeSession(duration: 180)
        ]
        sut.updateSessions(sessions)
        XCTAssertEqual(sut.averageDuration, 150, accuracy: 0.1)
    }

    func testAverageDurationWithEmptyReturnsZero() {
        sut.updateSessions([])
        XCTAssertEqual(sut.averageDuration, 0)
    }

    func testAverageTemperature() {
        let s1 = PlungeSession(duration: 120, waterTemperature: 4.0)
        let s2 = PlungeSession(duration: 180, waterTemperature: 6.0)
        sut.updateSessions([s1, s2])
        XCTAssertEqual(sut.averageTemperature ?? 0, 5.0, accuracy: 0.1)
    }

    func testAverageTemperatureIgnoresNils() {
        let s1 = PlungeSession(duration: 120, waterTemperature: 4.0)
        let s2 = PlungeSession(duration: 180)
        sut.updateSessions([s1, s2])
        XCTAssertEqual(sut.averageTemperature ?? 0, 4.0, accuracy: 0.1)
    }

    // MARK: - Formatted Duration

    func testFormattedDurationMinutesAndSeconds() {
        XCTAssertEqual(sut.formattedDuration(125), "2:05")
    }

    func testFormattedDurationZero() {
        XCTAssertEqual(sut.formattedDuration(0), "0:00")
    }

    // MARK: - Weekday Labels

    func testWeekdayLabelsHasSevenEntries() {
        XCTAssertEqual(sut.weekdayLabels.count, 7)
    }
}
