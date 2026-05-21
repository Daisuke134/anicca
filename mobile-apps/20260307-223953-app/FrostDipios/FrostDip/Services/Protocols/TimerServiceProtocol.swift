import Foundation

enum BreathPhase {
    case inhale, hold, exhale
}

protocol TimerServiceProtocol {
    func startTimer(duration: TimeInterval, onTick: @escaping (TimeInterval) -> Void, onComplete: @escaping () -> Void)
    func pauseTimer()
    func resumeTimer()
    func stopTimer()
    func startBreathingPrep(duration: TimeInterval, onPhaseChange: @escaping (BreathPhase) -> Void, onComplete: @escaping () -> Void)
}
