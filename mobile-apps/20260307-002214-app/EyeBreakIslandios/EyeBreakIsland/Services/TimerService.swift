import Foundation
import ActivityKit

protocol TimerServiceProtocol {
    var timerState: TimerState { get }
    var remainingSeconds: Int { get }
    var breakCount: Int { get }
    func startSession()
    func stopSession()
    func pauseSession()
    func resumeSession()
}

@MainActor
final class TimerService: ObservableObject, TimerServiceProtocol {
    @Published var timerState: TimerState = .idle
    @Published var remainingSeconds: Int = 20 * 60
    @Published var breakCount: Int = 0

    private var timer: Timer?
    private var activity: Activity<EyeBreakAttributes>?
    let workInterval: Int
    let breakInterval: Int

    init(workInterval: Int = 20 * 60, breakInterval: Int = 20) {
        self.workInterval = workInterval
        self.breakInterval = breakInterval
        self.remainingSeconds = workInterval
    }

    func startSession() {
        timerState = .running
        remainingSeconds = workInterval
        startTimer()
        startLiveActivity()
    }

    func stopSession() {
        timerState = .idle
        timer?.invalidate()
        timer = nil
        remainingSeconds = workInterval
        endLiveActivity()
    }

    func pauseSession() {
        guard timerState == .running else { return }
        timerState = .paused
        timer?.invalidate()
        timer = nil
    }

    func resumeSession() {
        guard timerState == .paused else { return }
        timerState = .running
        startTimer()
    }

    func startBreak() {
        timerState = .breaking
        remainingSeconds = breakInterval
        startTimer()
        updateLiveActivityState()
    }

    func completeBreak() {
        breakCount += 1
        persistBreakCount()
        timerState = .running
        remainingSeconds = workInterval
        startTimer()
        updateLiveActivityState()
    }

    private func startTimer() {
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            guard let self else { return }
            if self.remainingSeconds > 0 {
                self.remainingSeconds -= 1
                self.updateLiveActivityState()
            } else {
                self.timer?.invalidate()
                switch self.timerState {
                case .running:
                    self.startBreak()
                case .breaking:
                    self.completeBreak()
                default:
                    break
                }
            }
        }
    }

    private func persistBreakCount() {
        UserDefaults.standard.set(breakCount, forKey: Constants.todayBreakCountKey)
    }

    // MARK: - Live Activity

    private func startLiveActivity() {
        guard ActivityAuthorizationInfo().areActivitiesEnabled else { return }
        if #available(iOS 16.2, *) {
            let attributes = EyeBreakAttributes(sessionId: UUID().uuidString)
            let state = currentContentState()
            do {
                activity = try Activity.request(
                    attributes: attributes,
                    content: .init(state: state, staleDate: nil),
                    pushType: nil
                )
            } catch {
                // Fallback: notification-only mode
            }
        }
    }

    private func endLiveActivity() {
        if #available(iOS 16.2, *) {
            Task {
                await activity?.end(nil, dismissalPolicy: .immediate)
                activity = nil
            }
        }
    }

    private func updateLiveActivityState() {
        if #available(iOS 16.2, *) {
            let state = currentContentState()
            Task {
                await activity?.update(ActivityContent(state: state, staleDate: nil))
            }
        }
    }

    private func currentContentState() -> EyeBreakAttributes.ContentState {
        EyeBreakAttributes.ContentState(
            timerState: timerState.rawValue,
            remainingSeconds: remainingSeconds,
            breakCount: breakCount
        )
    }
}
