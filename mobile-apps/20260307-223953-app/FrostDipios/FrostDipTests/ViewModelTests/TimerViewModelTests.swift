import XCTest
@testable import FrostDip

final class TimerViewModelTests: XCTestCase {
    private var sut: TimerViewModel!
    private var mockTimer: MockTimerService!
    private var defaults: UserDefaults!

    override func setUp() {
        super.setUp()
        defaults = UserDefaults(suiteName: "TimerViewModelTests")!
        defaults.removePersistentDomain(forName: "TimerViewModelTests")
        mockTimer = MockTimerService()
        sut = TimerViewModel(timerService: mockTimer, defaults: defaults)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: "TimerViewModelTests")
        sut = nil
        mockTimer = nil
        defaults = nil
        super.tearDown()
    }

    // MARK: - Initial State

    func testInitialStateIsIdle() {
        XCTAssertEqual(sut.timerState, .idle)
    }

    func testInitialRemainingTimeMatchesProtocol() {
        XCTAssertEqual(sut.remainingTime, sut.selectedProtocol.coldTime)
    }

    func testInitialTemperatureIsNil() {
        XCTAssertNil(sut.waterTemperature)
    }

    // MARK: - Timer Start/Stop

    func testStartTimerChangesStateToRunning() {
        sut.startTimer()
        XCTAssertEqual(sut.timerState, .running)
    }

    func testStartTimerCallsTimerService() {
        sut.startTimer()
        XCTAssertTrue(mockTimer.startTimerCalled)
    }

    func testPauseTimerChangesStateToPaused() {
        sut.startTimer()
        sut.pauseTimer()
        XCTAssertEqual(sut.timerState, .paused)
    }

    func testResumeTimerChangesStateToRunning() {
        sut.startTimer()
        sut.pauseTimer()
        sut.resumeTimer()
        XCTAssertEqual(sut.timerState, .running)
    }

    func testStopTimerResetsState() {
        sut.startTimer()
        sut.stopTimer()
        XCTAssertEqual(sut.timerState, .idle)
    }

    // MARK: - Breathing Prep

    func testStartBreathingPrepChangesState() {
        sut.startBreathingPrep()
        XCTAssertEqual(sut.timerState, .breathing)
    }

    func testStartBreathingPrepCallsService() {
        sut.startBreathingPrep()
        XCTAssertTrue(mockTimer.startBreathingCalled)
    }

    // MARK: - Protocol Selection

    func testSelectProtocolUpdatesSelectedProtocol() {
        let protocols = PlungeProtocol.defaultProtocols()
        let advanced = protocols[2]
        sut.selectProtocol(advanced)
        XCTAssertEqual(sut.selectedProtocol.name, "Advanced")
        XCTAssertEqual(sut.remainingTime, 300)
    }

    // MARK: - Zero Division Guard

    func testZeroDurationProtocolDoesNotCrash() {
        let zeroProt = PlungeProtocol(name: "Zero", prepTime: 0, coldTime: 0)
        sut.selectProtocol(zeroProt)
        sut.startTimer()
        XCTAssertEqual(sut.timerState, .idle, "Zero duration should not start")
    }

    // MARK: - Temperature

    func testSetTemperatureUpdatesValue() {
        sut.waterTemperature = 4.0
        XCTAssertEqual(sut.waterTemperature, 4.0)
    }

    // MARK: - Session Completion

    func testTimerCompletionCreatesSession() {
        sut.startTimer()
        mockTimer.simulateComplete()
        XCTAssertEqual(sut.timerState, .completed)
        XCTAssertNotNil(sut.completedSession)
    }

    func testCompletedSessionHasCorrectDuration() {
        let protocols = PlungeProtocol.defaultProtocols()
        sut.selectProtocol(protocols[0]) // Beginner: 60s
        sut.startTimer()
        mockTimer.simulateComplete()
        XCTAssertEqual(sut.completedSession?.duration, 60)
    }

    func testCompletedSessionIncludesTemperature() {
        sut.waterTemperature = 3.5
        sut.startTimer()
        mockTimer.simulateComplete()
        XCTAssertEqual(sut.completedSession?.waterTemperature, 3.5)
    }

    // MARK: - Formatted Time

    func testFormattedTimeDisplaysCorrectly() {
        sut.remainingTime = 125
        XCTAssertEqual(sut.formattedTime, "2:05")
    }

    func testFormattedTimeZero() {
        sut.remainingTime = 0
        XCTAssertEqual(sut.formattedTime, "0:00")
    }
}

// MARK: - Mock

final class MockTimerService: TimerServiceProtocol {
    var startTimerCalled = false
    var startBreathingCalled = false
    private var onTickHandler: ((TimeInterval) -> Void)?
    private var onCompleteHandler: (() -> Void)?

    func startTimer(duration: TimeInterval, onTick: @escaping (TimeInterval) -> Void, onComplete: @escaping () -> Void) {
        startTimerCalled = true
        onTickHandler = onTick
        onCompleteHandler = onComplete
    }

    func pauseTimer() {}
    func resumeTimer() {}
    func stopTimer() {}

    func startBreathingPrep(duration: TimeInterval, onPhaseChange: @escaping (BreathPhase) -> Void, onComplete: @escaping () -> Void) {
        startBreathingCalled = true
        onCompleteHandler = onComplete
    }

    func simulateComplete() {
        onCompleteHandler?()
    }

    func simulateTick(_ time: TimeInterval) {
        onTickHandler?(time)
    }
}
