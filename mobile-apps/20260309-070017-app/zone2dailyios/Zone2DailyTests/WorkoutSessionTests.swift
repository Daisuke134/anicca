// File: Zone2DailyTests/WorkoutSessionTests.swift
// TDD: WorkoutSession derived properties

import XCTest
@testable import Zone2Daily

final class WorkoutSessionTests: XCTestCase {
    // MARK: — zone2Minutes

    func test_zone2Minutes_120seconds_returns2() {
        let session = WorkoutSession(durationSeconds: 600, zone2Seconds: 120, targetHR: 150)
        XCTAssertEqual(session.zone2Minutes, 2.0, accuracy: 0.001)
    }

    func test_zone2Minutes_90seconds_returns1point5() {
        let session = WorkoutSession(durationSeconds: 600, zone2Seconds: 90, targetHR: 150)
        XCTAssertEqual(session.zone2Minutes, 1.5, accuracy: 0.001)
    }

    func test_zone2Minutes_0seconds_returns0() {
        let session = WorkoutSession(durationSeconds: 600, zone2Seconds: 0, targetHR: 150)
        XCTAssertEqual(session.zone2Minutes, 0.0, accuracy: 0.001)
    }

    // MARK: — zone2Percentage

    func test_zone2Percentage_halfDuration_returns50() {
        let session = WorkoutSession(durationSeconds: 600, zone2Seconds: 300, targetHR: 150)
        XCTAssertEqual(session.zone2Percentage, 50.0, accuracy: 0.001)
    }

    func test_zone2Percentage_zeroDuration_returns0() {
        // Guard against division by zero
        let session = WorkoutSession(durationSeconds: 0, zone2Seconds: 0, targetHR: 150)
        XCTAssertEqual(session.zone2Percentage, 0.0, accuracy: 0.001)
    }

    func test_zone2Percentage_fullDuration_returns100() {
        let session = WorkoutSession(durationSeconds: 600, zone2Seconds: 600, targetHR: 150)
        XCTAssertEqual(session.zone2Percentage, 100.0, accuracy: 0.001)
    }

    // MARK: — init

    func test_init_setsUniqueIDs() {
        let s1 = WorkoutSession(durationSeconds: 600, zone2Seconds: 300, targetHR: 150)
        let s2 = WorkoutSession(durationSeconds: 600, zone2Seconds: 300, targetHR: 150)
        XCTAssertNotEqual(s1.id, s2.id)
    }

    func test_init_defaultDateIsNow() {
        let before = Date.now
        let session = WorkoutSession(durationSeconds: 600, zone2Seconds: 300, targetHR: 150)
        let after = Date.now
        XCTAssertGreaterThanOrEqual(session.date, before)
        XCTAssertLessThanOrEqual(session.date, after)
    }
}
