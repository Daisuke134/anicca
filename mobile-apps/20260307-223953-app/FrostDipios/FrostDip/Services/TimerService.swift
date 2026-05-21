import Foundation

/// Service classes (reference types) are exempt from the struct immutability rule.
final class TimerService: TimerServiceProtocol {
    private var timer: Timer?
    private var remaining: TimeInterval = 0
    private var onTickHandler: ((TimeInterval) -> Void)?
    private var onCompleteHandler: (() -> Void)?

    func startTimer(duration: TimeInterval, onTick: @escaping (TimeInterval) -> Void, onComplete: @escaping () -> Void) {
        stopTimer()
        remaining = duration
        onTickHandler = onTick
        onCompleteHandler = onComplete

        onTick(remaining)
        scheduleCountdownTimer()
    }

    func pauseTimer() {
        timer?.invalidate()
        timer = nil
    }

    func resumeTimer() {
        guard onTickHandler != nil, onCompleteHandler != nil else { return }
        scheduleCountdownTimer()
    }

    func stopTimer() {
        timer?.invalidate()
        timer = nil
        remaining = 0
        onTickHandler = nil
        onCompleteHandler = nil
    }

    func startBreathingPrep(duration: TimeInterval, onPhaseChange: @escaping (BreathPhase) -> Void, onComplete: @escaping () -> Void) {
        stopTimer()

        let cycleLength: TimeInterval = 19 // 4s inhale + 7s hold + 8s exhale
        var elapsed: TimeInterval = 0

        onPhaseChange(.inhale)

        let newTimer = Timer(timeInterval: 1.0, repeats: true) { [weak self] _ in
            guard let self else { return }
            elapsed += 1

            if elapsed >= duration {
                self.stopTimer()
                onComplete()
                return
            }

            let positionInCycle = elapsed.truncatingRemainder(dividingBy: cycleLength)
            if positionInCycle < 4 {
                onPhaseChange(.inhale)
            } else if positionInCycle < 11 {
                onPhaseChange(.hold)
            } else {
                onPhaseChange(.exhale)
            }
        }
        RunLoop.current.add(newTimer, forMode: .common)
        timer = newTimer
    }

    // MARK: - Private

    private func scheduleCountdownTimer() {
        guard let onTick = onTickHandler, let onComplete = onCompleteHandler else { return }
        let newTimer = Timer(timeInterval: 1.0, repeats: true) { [weak self] _ in
            guard let self else { return }
            self.remaining -= 1
            if self.remaining <= 0 {
                self.remaining = 0
                onTick(0)
                self.stopTimer()
                onComplete()
            } else {
                onTick(self.remaining)
            }
        }
        RunLoop.current.add(newTimer, forMode: .common)
        timer = newTimer
    }
}
