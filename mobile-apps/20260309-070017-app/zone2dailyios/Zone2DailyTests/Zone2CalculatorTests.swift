// File: Zone2DailyTests/Zone2CalculatorTests.swift
// TDD: Zone2Calculator unit tests
// RED → GREEN → REFACTOR

import XCTest
@testable import Zone2Daily

final class Zone2CalculatorTests: XCTestCase {
    // MARK: — zone2MaxHR (F-001: Maffetone Formula)

    func test_zone2MaxHR_age30_returns150() {
        // Source: Maffetone 180 Formula — 180 - 30 = 150
        XCTAssertEqual(Zone2Calculator.zone2MaxHR(age: 30), 150)
    }

    func test_zone2MaxHR_age40_returns140() {
        XCTAssertEqual(Zone2Calculator.zone2MaxHR(age: 40), 140)
    }

    func test_zone2MaxHR_age20_returns160() {
        XCTAssertEqual(Zone2Calculator.zone2MaxHR(age: 20), 160)
    }

    func test_zone2MaxHR_age65_returns115() {
        XCTAssertEqual(Zone2Calculator.zone2MaxHR(age: 65), 115)
    }

    // MARK: — zone2MinHR

    func test_zone2MinHR_age30_returns140() {
        // minHR = maxHR - 10 = 150 - 10 = 140
        XCTAssertEqual(Zone2Calculator.zone2MinHR(age: 30), 140)
    }

    func test_zone2MinHR_age40_returns130() {
        XCTAssertEqual(Zone2Calculator.zone2MinHR(age: 40), 130)
    }

    // MARK: — zone2Range

    func test_zone2Range_age30_contains145() {
        let range = Zone2Calculator.zone2Range(age: 30)
        XCTAssertTrue(range.contains(145))
    }

    func test_zone2Range_age30_doesNotContain151() {
        let range = Zone2Calculator.zone2Range(age: 30)
        XCTAssertFalse(range.contains(151))
    }

    func test_zone2Range_age30_doesNotContain139() {
        let range = Zone2Calculator.zone2Range(age: 30)
        XCTAssertFalse(range.contains(139))
    }

    func test_zone2Range_age30_containsBoundaries() {
        let range = Zone2Calculator.zone2Range(age: 30)
        XCTAssertTrue(range.contains(140))  // min
        XCTAssertTrue(range.contains(150))  // max
    }
}
