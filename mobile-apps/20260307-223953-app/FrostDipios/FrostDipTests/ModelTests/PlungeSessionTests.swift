import XCTest
@testable import FrostDip

final class PlungeSessionTests: XCTestCase {
    func testInit_setsDefaults() {
        let session = PlungeSession(duration: 120)
        XCTAssertEqual(session.duration, 120)
        XCTAssertNil(session.waterTemperature)
        XCTAssertEqual(session.notes, "")
        XCTAssertEqual(session.heartRates, [])
        XCTAssertFalse(session.isContrastSession)
        XCTAssertNil(session.hotTemperature)
        XCTAssertNil(session.coldDuration)
        XCTAssertNil(session.hotDuration)
        XCTAssertNil(session.roundsCompleted)
    }

    func testInit_withTemperature() {
        let session = PlungeSession(duration: 60, waterTemperature: 4.5)
        XCTAssertEqual(session.waterTemperature, 4.5)
    }

    func testInit_withNotes() {
        let session = PlungeSession(duration: 90, notes: "Cold morning")
        XCTAssertEqual(session.notes, "Cold morning")
    }

    func testInit_generatesUniqueIDs() {
        let s1 = PlungeSession(duration: 60)
        let s2 = PlungeSession(duration: 60)
        XCTAssertNotEqual(s1.id, s2.id)
    }

    func testContrastSessionProperties() {
        let session = PlungeSession(duration: 300)
        session.isContrastSession = true
        session.hotTemperature = 40.0
        session.coldDuration = 120
        session.hotDuration = 180
        session.roundsCompleted = 3

        XCTAssertTrue(session.isContrastSession)
        XCTAssertEqual(session.hotTemperature, 40.0)
        XCTAssertEqual(session.coldDuration, 120)
        XCTAssertEqual(session.hotDuration, 180)
        XCTAssertEqual(session.roundsCompleted, 3)
    }

    func testHeartRateData() {
        let session = PlungeSession(duration: 60)
        session.heartRates = [72.0, 68.0, 65.0]
        session.heartRateAvg = 68.3
        session.heartRateMax = 72.0

        XCTAssertEqual(session.heartRates.count, 3)
        XCTAssertEqual(session.heartRateAvg, 68.3)
        XCTAssertEqual(session.heartRateMax, 72.0)
    }
}
