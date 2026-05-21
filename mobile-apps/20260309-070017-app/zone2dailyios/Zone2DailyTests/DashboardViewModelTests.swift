// File: Zone2DailyTests/DashboardViewModelTests.swift
// TDD: DashboardViewModel unit tests

import XCTest
@testable import Zone2Daily

final class DashboardViewModelTests: XCTestCase {
    var sut: DashboardViewModel!

    override func setUp() {
        super.setUp()
        sut = DashboardViewModel()
    }

    // MARK: — loadWeeklyData

    func test_loadWeeklyData_noSessions_weeklyMinutesIsZero() {
        sut.loadWeeklyData(sessions: [])
        XCTAssertEqual(sut.weeklyZone2Minutes, 0.0, accuracy: 0.001)
    }

    func test_loadWeeklyData_thisWeekSession_countsMinutes() {
        let session = WorkoutSession(
            date: Date.now,
            durationSeconds: 3600,
            zone2Seconds: 1800,
            targetHR: 150
        )
        sut.loadWeeklyData(sessions: [session])
        XCTAssertEqual(sut.weeklyZone2Minutes, 30.0, accuracy: 0.001)
    }

    func test_loadWeeklyData_oldSession_notCounted() {
        // Session from 30 days ago should not count in weekly total
        let oldDate = Calendar.current.date(byAdding: .day, value: -30, to: .now)!
        let session = WorkoutSession(
            date: oldDate,
            durationSeconds: 3600,
            zone2Seconds: 1800,
            targetHR: 150
        )
        sut.loadWeeklyData(sessions: [session])
        XCTAssertEqual(sut.weeklyZone2Minutes, 0.0, accuracy: 0.001)
    }

    func test_loadWeeklyData_multipleSessions_summed() {
        let s1 = WorkoutSession(date: .now, durationSeconds: 3600, zone2Seconds: 1800, targetHR: 150)
        let s2 = WorkoutSession(date: .now, durationSeconds: 1800, zone2Seconds: 900, targetHR: 150)
        sut.loadWeeklyData(sessions: [s1, s2])
        XCTAssertEqual(sut.weeklyZone2Minutes, 45.0, accuracy: 0.001)
    }

    // MARK: — progressFraction

    func test_progressFraction_zeroMinutes_isZero() {
        sut.weeklyZone2Minutes = 0
        sut.weeklyGoalMinutes = 150
        XCTAssertEqual(sut.progressFraction, 0.0, accuracy: 0.001)
    }

    func test_progressFraction_halfGoal_isPointFive() {
        sut.weeklyZone2Minutes = 75
        sut.weeklyGoalMinutes = 150
        XCTAssertEqual(sut.progressFraction, 0.5, accuracy: 0.001)
    }

    func test_progressFraction_overGoal_cappedAtOne() {
        sut.weeklyZone2Minutes = 300
        sut.weeklyGoalMinutes = 150
        XCTAssertEqual(sut.progressFraction, 1.0, accuracy: 0.001)
    }

    // MARK: — canLogWorkout (free tier)

    func test_canLogWorkout_premium_alwaysTrue() {
        let sessions = (0..<10).map { _ in
            WorkoutSession(date: .now, durationSeconds: 600, zone2Seconds: 300, targetHR: 150)
        }
        XCTAssertTrue(sut.canLogWorkout(sessions: sessions, isPremium: true))
    }

    func test_canLogWorkout_freeTierUnder3_true() {
        let sessions = (0..<2).map { _ in
            WorkoutSession(date: .now, durationSeconds: 600, zone2Seconds: 300, targetHR: 150)
        }
        XCTAssertTrue(sut.canLogWorkout(sessions: sessions, isPremium: false))
    }

    func test_canLogWorkout_freeTierAt3_false() {
        let sessions = (0..<3).map { _ in
            WorkoutSession(date: .now, durationSeconds: 600, zone2Seconds: 300, targetHR: 150)
        }
        XCTAssertFalse(sut.canLogWorkout(sessions: sessions, isPremium: false))
    }

    // MARK: — weekdayActivity

    func test_weekdayActivity_returnsSevenEntries() {
        sut.loadWeeklyData(sessions: [])
        XCTAssertEqual(sut.weekdayActivity.count, 7)
    }

    func test_weekdayActivity_noSessions_allHaveNoActivity() {
        sut.loadWeeklyData(sessions: [])
        XCTAssertTrue(sut.weekdayActivity.allSatisfy { !$0.hasActivity })
    }

    func test_weekdayActivity_todaySession_atLeastOneActive() {
        let session = WorkoutSession(date: .now, durationSeconds: 600, zone2Seconds: 300, targetHR: 150)
        sut.loadWeeklyData(sessions: [session])
        XCTAssertTrue(sut.weekdayActivity.contains { $0.hasActivity })
    }

    func test_weekdayActivity_oldSession_noneActive() {
        let old = Calendar.current.date(byAdding: .day, value: -10, to: .now)!
        let session = WorkoutSession(date: old, durationSeconds: 600, zone2Seconds: 300, targetHR: 150)
        sut.loadWeeklyData(sessions: [session])
        XCTAssertTrue(sut.weekdayActivity.allSatisfy { !$0.hasActivity })
    }

    func test_weekdayActivity_allLabelsNonEmpty() {
        sut.loadWeeklyData(sessions: [])
        XCTAssertTrue(sut.weekdayActivity.allSatisfy { !$0.label.isEmpty })
    }

    func test_weekdayActivity_minutesAccumulate() {
        let s1 = WorkoutSession(date: .now, durationSeconds: 1200, zone2Seconds: 600, targetHR: 150)
        let s2 = WorkoutSession(date: .now, durationSeconds: 600, zone2Seconds: 300, targetHR: 150)
        sut.loadWeeklyData(sessions: [s1, s2])
        let todayEntry = sut.weekdayActivity.last!  // last = today
        XCTAssertEqual(todayEntry.minutes, 15.0, accuracy: 0.1)
    }
}
