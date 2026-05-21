import XCTest
@testable import EyeBreakIsland

final class ModelTests: XCTestCase {

    // MARK: - TimerState

    func testTimerStateIdle() {
        let state = TimerState.idle
        XCTAssertEqual(state.rawValue, "idle")
    }

    func testTimerStateRunning() {
        let state = TimerState.running
        XCTAssertEqual(state.rawValue, "running")
    }

    func testTimerStateBreaking() {
        let state = TimerState.breaking
        XCTAssertEqual(state.rawValue, "breaking")
    }

    func testTimerStatePaused() {
        let state = TimerState.paused
        XCTAssertEqual(state.rawValue, "paused")
    }

    func testTimerStateCodable() throws {
        let original = TimerState.running
        let data = try JSONEncoder().encode(original)
        let decoded = try JSONDecoder().decode(TimerState.self, from: data)
        XCTAssertEqual(decoded, original)
    }

    // MARK: - BreakSession

    func testBreakSessionDefaultInit() {
        let session = BreakSession()
        XCTAssertEqual(session.breakCount, 0)
        XCTAssertEqual(session.totalMinutes, 0)
    }

    func testBreakSessionCustomInit() {
        let session = BreakSession(breakCount: 5, totalMinutes: 100)
        XCTAssertEqual(session.breakCount, 5)
        XCTAssertEqual(session.totalMinutes, 100)
    }

    func testBreakSessionCodable() throws {
        let original = BreakSession(breakCount: 3, totalMinutes: 60)
        let data = try JSONEncoder().encode(original)
        let decoded = try JSONDecoder().decode(BreakSession.self, from: data)
        XCTAssertEqual(decoded.breakCount, original.breakCount)
        XCTAssertEqual(decoded.totalMinutes, original.totalMinutes)
    }

    func testBreakSessionIdentifiable() {
        let session = BreakSession()
        XCTAssertNotNil(session.id)
    }

    // MARK: - SubscriptionStatus

    func testSubscriptionStatusFree() {
        let status = SubscriptionStatus.free
        XCTAssertEqual(status.rawValue, "free")
    }

    func testSubscriptionStatusPro() {
        let status = SubscriptionStatus.pro
        XCTAssertEqual(status.rawValue, "pro")
    }

    func testSubscriptionStatusCodable() throws {
        let original = SubscriptionStatus.pro
        let data = try JSONEncoder().encode(original)
        let decoded = try JSONDecoder().decode(SubscriptionStatus.self, from: data)
        XCTAssertEqual(decoded, original)
    }
}
