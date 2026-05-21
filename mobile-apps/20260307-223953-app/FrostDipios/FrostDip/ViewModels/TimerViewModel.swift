import Foundation
import SwiftData

enum TimerState: Equatable {
    case idle, breathing, running, paused, completed
}

@Observable
final class TimerViewModel {
    var timerState: TimerState = .idle
    var remainingTime: TimeInterval = 0
    var breathPhase: BreathPhase = .inhale
    var waterTemperature: Double?
    var heartRate: Double?
    var completedSession: PlungeSession?
    var showSummary = false

    private(set) var selectedProtocol: PlungeProtocol
    private let timerService: TimerServiceProtocol
    private let preferences: UserPreferences
    private var sessionDuration: TimeInterval = 0

    var formattedTime: String {
        let minutes = Int(remainingTime) / 60
        let seconds = Int(remainingTime) % 60
        return "\(minutes):\(String(format: "%02d", seconds))"
    }

    var availableProtocols: [PlungeProtocol] {
        PlungeProtocol.defaultProtocols()
    }

    init(timerService: TimerServiceProtocol = TimerService(), defaults: UserDefaults = .standard) {
        self.timerService = timerService
        self.preferences = UserPreferences(defaults: defaults)

        let protocols = PlungeProtocol.defaultProtocols()
        let level = preferences.experienceLevel
        switch level {
        case .beginner: self.selectedProtocol = protocols[0]
        case .intermediate: self.selectedProtocol = protocols[1]
        case .advanced: self.selectedProtocol = protocols[2]
        }
        self.remainingTime = self.selectedProtocol.coldTime
    }

    func selectProtocol(_ proto: PlungeProtocol) {
        selectedProtocol = proto
        remainingTime = proto.coldTime
        sessionDuration = proto.coldTime
    }

    func startTimer() {
        guard selectedProtocol.coldTime > 0 else { return }
        sessionDuration = selectedProtocol.coldTime
        timerState = .running
        timerService.startTimer(duration: selectedProtocol.coldTime, onTick: { [weak self] remaining in
            self?.remainingTime = remaining
        }, onComplete: { [weak self] in
            self?.completeSession()
        })
    }

    func pauseTimer() {
        timerState = .paused
        timerService.pauseTimer()
    }

    func resumeTimer() {
        timerState = .running
        timerService.resumeTimer()
    }

    func stopTimer() {
        timerService.stopTimer()
        remainingTime = selectedProtocol.coldTime
        timerState = .idle
        completedSession = nil
    }

    func startBreathingPrep() {
        guard selectedProtocol.prepTime > 0 else {
            startTimer()
            return
        }
        timerState = .breathing
        timerService.startBreathingPrep(duration: selectedProtocol.prepTime, onPhaseChange: { [weak self] phase in
            self?.breathPhase = phase
        }, onComplete: { [weak self] in
            self?.startTimer()
        })
    }

    func skipBreathingPrep() {
        timerService.stopTimer()
        startTimer()
    }

    func dismissSummary() {
        showSummary = false
        completedSession = nil
        timerState = .idle
        remainingTime = selectedProtocol.coldTime
    }

    private func completeSession() {
        let session = PlungeSession(duration: sessionDuration, waterTemperature: waterTemperature)
        session.protocolName = selectedProtocol.name
        completedSession = session
        timerState = .completed
        showSummary = true
    }
}
