import SwiftUI

struct TimerRing: View {
    let progress: Double
    let timerState: TimerState
    let formattedTime: String

    private var ringColor: Color {
        switch timerState {
        case .running: return AppColors.brandPrimary
        case .breaking: return AppColors.brandBreak
        case .paused: return AppColors.brandWarning
        case .idle: return AppColors.textTertiary
        }
    }

    var body: some View {
        ZStack {
            Circle()
                .stroke(AppColors.bgTertiary, lineWidth: 12)
            Circle()
                .trim(from: 0, to: progress)
                .stroke(ringColor, style: StrokeStyle(lineWidth: 12, lineCap: .round))
                .rotationEffect(.degrees(-90))
                .animation(AppAnimations.timerTick, value: progress)
            Text(formattedTime)
                .font(AppTypography.display)
                .foregroundStyle(AppColors.textPrimary)
                .monospacedDigit()
                .accessibilityIdentifier(AccessibilityID.timerTimeLabel)
        }
        .frame(width: 280, height: 280)
        .accessibilityIdentifier(AccessibilityID.timerRing)
    }
}
