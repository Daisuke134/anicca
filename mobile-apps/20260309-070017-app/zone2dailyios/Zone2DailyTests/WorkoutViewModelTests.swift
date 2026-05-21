// File: Zone2DailyTests/WorkoutViewModelTests.swift
// TDD: WorkoutViewModel — background timer support
// Source: Apple Background Execution — https://developer.apple.com/documentation/uikit/app_and_environment/scenes/preparing_your_ui_to_run_in_the_background

import XCTest
@testable import Zone2Daily

@MainActor
final class WorkoutViewModelTests: XCTestCase {
    var sut: WorkoutViewModel!

    override func setUp() {
        super.setUp()
        sut = WorkoutViewModel()
    }

    override func tearDown() {
        sut.stopTimer()
        sut = nil
        super.tearDown()
    }

    // MARK: — formattedTime

    func test_formattedTime_initial_showsDoubleZero() {
        XCTAssertEqual(sut.formattedTime, "00:00")
    }

    func test_formattedTime_90seconds_shows1min30() {
        sut.elapsedSeconds = 90
        XCTAssertEqual(sut.formattedTime, "01:30")
    }

    func test_formattedTime_3661seconds_shows61min01() {
        sut.elapsedSeconds = 3661
        XCTAssertEqual(sut.formattedTime, "61:01")
    }

    func test_formattedTime_0seconds_shows00colon00() {
        sut.elapsedSeconds = 0
        XCTAssertEqual(sut.formattedTime, "00:00")
    }

    // MARK: — startTimer / stopTimer

    func test_startTimer_setsIsRunningTrue() {
        sut.startTimer()
        XCTAssertTrue(sut.isRunning)
    }

    func test_stopTimer_setsIsRunningFalse() {
        sut.startTimer()
        sut.stopTimer()
        XCTAssertFalse(sut.isRunning)
    }

    // MARK: — startDate (background timer support)

    func test_startTimer_setsStartDate() {
        let before = Date.now
        sut.startTimer()
        let after = Date.now
        XCTAssertNotNil(sut.startDate)
        if let startDate = sut.startDate {
            XCTAssertGreaterThanOrEqual(startDate, before)
            XCTAssertLessThanOrEqual(startDate, after)
        }
    }

    func test_stopTimer_clearsStartDate() {
        sut.startTimer()
        sut.stopTimer()
        XCTAssertNil(sut.startDate)
    }

    func test_startTimer_twice_updatesStartDate() {
        sut.startTimer()
        let first = sut.startDate
        sut.stopTimer()
        let pause = Date.now
        sut.startTimer()
        let second = sut.startDate
        XCTAssertNotEqual(first, second)
        if let s = second {
            XCTAssertGreaterThanOrEqual(s, pause)
        }
    }

    // MARK: — reset state

    func test_stopTimer_doesNotResetElapsedSeconds() {
        // Elapsed seconds reset only happens in stopAndSave after successful save
        sut.elapsedSeconds = 120
        sut.stopTimer()
        XCTAssertEqual(sut.elapsedSeconds, 120)
    }

    func test_stopTimer_doesNotResetZone2Seconds() {
        sut.zone2Seconds = 60
        sut.stopTimer()
        XCTAssertEqual(sut.zone2Seconds, 60)
    }

    // MARK: — elapsed from startDate (background accuracy)

    func test_elapsedSeconds_afterTimerStart_startDateAnchorsTime() {
        sut.startTimer()
        guard let startDate = sut.startDate else {
            XCTFail("startDate must be set after startTimer()")
            return
        }
        let elapsed = Int(Date.now.timeIntervalSince(startDate))
        XCTAssertGreaterThanOrEqual(elapsed, 0)
        XCTAssertLessThanOrEqual(elapsed, 2)  // Within 2 seconds of start
    }
}
