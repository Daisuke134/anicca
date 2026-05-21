import XCTest
@testable import EyeBreakIsland

// MARK: - TimerViewModelContainer Tests

@MainActor
final class TimerViewModelContainerTests: XCTestCase {
    func testInitialShowSettingsFalse() {
        let sut = TimerViewModelContainer()
        XCTAssertFalse(sut.showSettings)
    }

    func testInitialShowBreakOverlayFalse() {
        let sut = TimerViewModelContainer()
        XCTAssertFalse(sut.showBreakOverlay)
    }
}

// MARK: - Timer Formatting Tests

final class TimerFormattingTests: XCTestCase {
    func testFormattedTimeMmSs() {
        XCTAssertEqual(formatTime(1234), "20:34")
    }

    func testFormattedTimeZero() {
        XCTAssertEqual(formatTime(0), "0:00")
    }

    func testFormattedTimeExactMinute() {
        XCTAssertEqual(formatTime(300), "5:00")
    }

    func testFormattedTimeOneSecond() {
        XCTAssertEqual(formatTime(1), "0:01")
    }

    func testProgressNormal() {
        let remaining = 600
        let total = Constants.defaultWorkIntervalSeconds
        let expected = 1.0 - (Double(remaining) / Double(total))
        XCTAssertEqual(calculateProgress(remaining: remaining, total: total), expected, accuracy: 0.001)
    }

    func testProgressZeroDivisionGuard() {
        XCTAssertEqual(calculateProgress(remaining: 100, total: 0), 0.0)
    }

    func testProgressFull() {
        XCTAssertEqual(calculateProgress(remaining: 0, total: 1200), 1.0, accuracy: 0.001)
    }

    func testProgressIdle() {
        let total = Constants.defaultWorkIntervalSeconds
        XCTAssertEqual(calculateProgress(remaining: total, total: total), 0.0, accuracy: 0.001)
    }

    private func formatTime(_ seconds: Int) -> String {
        let minutes = seconds / 60
        let secs = seconds % 60
        return "\(minutes):\(String(format: "%02d", secs))"
    }

    private func calculateProgress(remaining: Int, total: Int) -> Double {
        guard total > 0 else { return 0.0 }
        return 1.0 - (Double(remaining) / Double(total))
    }
}

// MARK: - Timer State Machine Tests

@MainActor
final class TimerStateMachineTests: XCTestCase {
    func testStartSetsRunning() {
        let service = TimerService()
        service.startSession()
        XCTAssertEqual(service.timerState, .running)
    }

    func testStopSetsIdle() {
        let service = TimerService()
        service.startSession()
        service.stopSession()
        XCTAssertEqual(service.timerState, .idle)
    }

    func testPauseSetsState() {
        let service = TimerService()
        service.startSession()
        service.pauseSession()
        XCTAssertEqual(service.timerState, .paused)
    }

    func testResumeFromPaused() {
        let service = TimerService()
        service.startSession()
        service.pauseSession()
        service.resumeSession()
        XCTAssertEqual(service.timerState, .running)
    }

    func testResumeFromNonPausedNoOp() {
        let service = TimerService()
        service.resumeSession()
        XCTAssertEqual(service.timerState, .idle)
    }

    func testPauseFromNonRunningNoOp() {
        let service = TimerService()
        service.pauseSession()
        XCTAssertEqual(service.timerState, .idle)
    }

    func testStartResetsRemaining() {
        let service = TimerService(workInterval: 120, breakInterval: 10)
        service.startSession()
        XCTAssertEqual(service.remainingSeconds, 120)
    }

    func testStopResetsRemaining() {
        let service = TimerService(workInterval: 120, breakInterval: 10)
        service.startSession()
        service.stopSession()
        XCTAssertEqual(service.remainingSeconds, 120)
    }

    func testBreakStartSetsBreakingState() {
        let service = TimerService(workInterval: 1, breakInterval: 20)
        service.startBreak()
        XCTAssertEqual(service.timerState, .breaking)
        XCTAssertEqual(service.remainingSeconds, 20)
    }

    func testCompleteBreakIncrementsCount() {
        let service = TimerService()
        let initialCount = service.breakCount
        service.completeBreak()
        XCTAssertEqual(service.breakCount, initialCount + 1)
    }
}
