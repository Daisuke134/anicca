import XCTest
@testable import EyeBreakIsland

@MainActor
final class TimerServiceTests: XCTestCase {

    // MARK: - Initial State

    func testInitialStateIsIdle() {
        let sut = TimerService()
        XCTAssertEqual(sut.timerState, .idle)
    }

    func testInitialRemainingSecondsEqualsWorkInterval() {
        let sut = TimerService(workInterval: 300)
        XCTAssertEqual(sut.remainingSeconds, 300)
    }

    func testInitialBreakCountIsZero() {
        let sut = TimerService()
        XCTAssertEqual(sut.breakCount, 0)
    }

    // MARK: - Start Session

    func testStartSessionSetsRunning() {
        let sut = TimerService(workInterval: 60)
        sut.startSession()
        XCTAssertEqual(sut.timerState, .running)
    }

    func testStartSessionResetsRemainingSeconds() {
        let sut = TimerService(workInterval: 120)
        sut.startSession()
        XCTAssertEqual(sut.remainingSeconds, 120)
    }

    // MARK: - Stop Session

    func testStopSessionSetsIdle() {
        let sut = TimerService()
        sut.startSession()
        sut.stopSession()
        XCTAssertEqual(sut.timerState, .idle)
    }

    func testStopSessionResetsToWorkInterval() {
        let sut = TimerService(workInterval: 600)
        sut.startSession()
        sut.stopSession()
        XCTAssertEqual(sut.remainingSeconds, 600)
    }

    // MARK: - Pause / Resume

    func testPauseSessionSetsPaused() {
        let sut = TimerService()
        sut.startSession()
        sut.pauseSession()
        XCTAssertEqual(sut.timerState, .paused)
    }

    func testPauseOnlyWorksWhenRunning() {
        let sut = TimerService()
        sut.pauseSession()
        XCTAssertEqual(sut.timerState, .idle)
    }

    func testResumeSessionSetsRunning() {
        let sut = TimerService()
        sut.startSession()
        sut.pauseSession()
        sut.resumeSession()
        XCTAssertEqual(sut.timerState, .running)
    }

    func testResumeOnlyWorksWhenPaused() {
        let sut = TimerService()
        sut.startSession()
        sut.resumeSession()
        XCTAssertEqual(sut.timerState, .running)
    }

    // MARK: - Break

    func testStartBreakSetsBreaking() {
        let sut = TimerService(breakInterval: 5)
        sut.startBreak()
        XCTAssertEqual(sut.timerState, .breaking)
    }

    func testStartBreakSetsRemainingToBreakInterval() {
        let sut = TimerService(breakInterval: 10)
        sut.startBreak()
        XCTAssertEqual(sut.remainingSeconds, 10)
    }

    func testCompleteBreakIncrementsCount() {
        let sut = TimerService()
        let initialCount = sut.breakCount
        sut.completeBreak()
        XCTAssertEqual(sut.breakCount, initialCount + 1)
    }

    func testCompleteBreakSetsRunning() {
        let sut = TimerService()
        sut.startBreak()
        sut.completeBreak()
        XCTAssertEqual(sut.timerState, .running)
    }

    func testCompleteBreakResetsToWorkInterval() {
        let sut = TimerService(workInterval: 300)
        sut.startBreak()
        sut.completeBreak()
        XCTAssertEqual(sut.remainingSeconds, 300)
    }

    // MARK: - Custom Intervals

    func testCustomWorkInterval() {
        let sut = TimerService(workInterval: 15 * 60)
        XCTAssertEqual(sut.workInterval, 900)
    }

    func testCustomBreakInterval() {
        let sut = TimerService(breakInterval: 30)
        XCTAssertEqual(sut.breakInterval, 30)
    }

    func testDefaultWorkIntervalIs20Minutes() {
        let sut = TimerService()
        XCTAssertEqual(sut.workInterval, 1200)
    }

    func testDefaultBreakIntervalIs20Seconds() {
        let sut = TimerService()
        XCTAssertEqual(sut.breakInterval, 20)
    }
}
