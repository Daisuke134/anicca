import SwiftUI

struct TimerView: View {
    @EnvironmentObject private var timerService: TimerService
    @EnvironmentObject private var subscriptionService: SubscriptionService
    @StateObject private var viewModel = TimerViewModelContainer()

    var body: some View {
        VStack(spacing: AppSpacing.lg) {
            HStack {
                Spacer()
                Button {
                    viewModel.showSettings = true
                } label: {
                    Image(systemName: "gearshape.fill")
                        .font(.title3)
                        .foregroundStyle(AppColors.textSecondary)
                }
                .accessibilityIdentifier(AccessibilityID.settingsGearButton)
                .padding(.trailing, AppSpacing.md)
            }

            Spacer()

            TimerRing(
                progress: progress,
                timerState: timerService.timerState,
                formattedTime: formattedTime
            )

            statusLabel

            breakCountLabel

            actionButtons

            Spacer()
        }
        .padding(.horizontal, AppSpacing.md)
        .background(AppColors.bgPrimary.ignoresSafeArea())
        .sheet(isPresented: $viewModel.showSettings) {
            SettingsView(subscriptionService: subscriptionService)
        }
        .fullScreenCover(isPresented: $viewModel.showBreakOverlay) {
            BreakOverlayView(
                timerState: timerService.timerState,
                remainingSeconds: timerService.remainingSeconds,
                breakInterval: timerService.breakInterval
            )
        }
        .onChange(of: timerService.timerState) { newState in
            viewModel.showBreakOverlay = (newState == .breaking)
        }
    }

    private var formattedTime: String {
        let minutes = timerService.remainingSeconds / 60
        let seconds = timerService.remainingSeconds % 60
        return "\(minutes):\(String(format: "%02d", seconds))"
    }

    private var progress: Double {
        let total: Int
        if timerService.timerState == .breaking {
            total = timerService.breakInterval
        } else {
            total = timerService.workInterval
        }
        guard total > 0 else { return 0.0 }
        return 1.0 - (Double(timerService.remainingSeconds) / Double(total))
    }

    private var statusLabel: some View {
        Group {
            switch timerService.timerState {
            case .idle:
                Text("timer.status.ready")
            case .running:
                Text("timer.status.running")
            case .paused:
                Text("timer.status.paused")
            case .breaking:
                Text("timer.status.breaking")
            }
        }
        .font(AppTypography.body)
        .foregroundStyle(AppColors.textSecondary)
    }

    private var breakCountLabel: some View {
        Text("timer.break.count \(timerService.breakCount)")
            .font(AppTypography.subheadline)
            .foregroundStyle(AppColors.textSecondary)
            .accessibilityIdentifier(AccessibilityID.timerBreakCount)
    }

    @ViewBuilder
    private var actionButtons: some View {
        switch timerService.timerState {
        case .idle:
            PrimaryButton(title: NSLocalizedString("timer.button.start", comment: "")) {
                timerService.startSession()
            }
            .accessibilityIdentifier(AccessibilityID.timerStartButton)

        case .running:
            PrimaryButton(title: NSLocalizedString("timer.button.pause", comment: "")) {
                timerService.pauseSession()
            }
            .accessibilityIdentifier(AccessibilityID.timerPauseButton)

            SecondaryButton(title: NSLocalizedString("timer.button.stop", comment: "")) {
                timerService.stopSession()
            }
            .accessibilityIdentifier(AccessibilityID.timerStopButton)

        case .paused:
            PrimaryButton(title: NSLocalizedString("timer.button.resume", comment: "")) {
                timerService.resumeSession()
            }
            .accessibilityIdentifier(AccessibilityID.timerPauseButton)

            SecondaryButton(title: NSLocalizedString("timer.button.stop", comment: "")) {
                timerService.stopSession()
            }
            .accessibilityIdentifier(AccessibilityID.timerStopButton)

        case .breaking:
            EmptyView()
        }
    }
}

@MainActor
final class TimerViewModelContainer: ObservableObject {
    @Published var showSettings = false
    @Published var showBreakOverlay = false
}
