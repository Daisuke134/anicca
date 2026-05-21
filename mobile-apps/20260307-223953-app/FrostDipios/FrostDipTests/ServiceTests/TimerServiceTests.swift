import XCTest
@testable import FrostDip

final class TimerServiceTests: XCTestCase {
    private var sut: TimerService!

    override func setUp() {
        super.setUp()
        sut = TimerService()
    }

    override func tearDown() {
        sut.stopTimer()
        sut = nil
        super.tearDown()
    }

    func testStartTimer_callsOnTickImmediately() {
        let expectation = expectation(description: "onTick called")
        sut.startTimer(duration: 5, onTick: { remaining in
            if remaining == 5 {
                expectation.fulfill()
            }
        }, onComplete: {})
        wait(for: [expectation], timeout: 1.0)
    }

    func testStartTimer_ticksDown() {
        let expectation = expectation(description: "tick down")
        var ticks: [TimeInterval] = []

        sut.startTimer(duration: 3, onTick: { remaining in
            ticks.append(remaining)
            if remaining == 2 {
                expectation.fulfill()
            }
        }, onComplete: {})

        wait(for: [expectation], timeout: 3.0)
        XCTAssertTrue(ticks.contains(3))
        XCTAssertTrue(ticks.contains(2))
    }

    func testStartTimer_callsOnComplete() {
        let expectation = expectation(description: "complete")
        sut.startTimer(duration: 2, onTick: { _ in }, onComplete: {
            expectation.fulfill()
        })
        wait(for: [expectation], timeout: 4.0)
    }

    func testPauseTimer_stopsCountdown() {
        let expectation = expectation(description: "pause")
        var lastRemaining: TimeInterval = 0

        sut.startTimer(duration: 10, onTick: { remaining in
            lastRemaining = remaining
            if remaining == 9 {
                self.sut.pauseTimer()
                DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                    XCTAssertEqual(lastRemaining, 9)
                    expectation.fulfill()
                }
            }
        }, onComplete: {})

        wait(for: [expectation], timeout: 5.0)
    }

    func testStopTimer_resetsState() {
        sut.startTimer(duration: 10, onTick: { _ in }, onComplete: {})
        sut.stopTimer()
        // Starting a new timer should work without issues
        let expectation = expectation(description: "new timer")
        sut.startTimer(duration: 2, onTick: { remaining in
            if remaining == 2 { expectation.fulfill() }
        }, onComplete: {})
        wait(for: [expectation], timeout: 1.0)
    }

    func testBreathingPrep_callsPhaseChange() {
        let expectation = expectation(description: "breathing")
        var phases: [BreathPhase] = []

        sut.startBreathingPrep(duration: 2, onPhaseChange: { phase in
            phases.append(phase)
        }, onComplete: {
            expectation.fulfill()
        })

        wait(for: [expectation], timeout: 4.0)
        XCTAssertFalse(phases.isEmpty)
        XCTAssertEqual(phases.first, .inhale)
    }
}
