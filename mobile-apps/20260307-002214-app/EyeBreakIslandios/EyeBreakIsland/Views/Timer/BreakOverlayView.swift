import SwiftUI

struct BreakOverlayView: View {
    let timerState: TimerState
    let remainingSeconds: Int
    let breakInterval: Int

    private var progress: Double {
        guard breakInterval > 0 else { return 0.0 }
        return 1.0 - (Double(remainingSeconds) / Double(breakInterval))
    }

    private var formattedTime: String {
        let seconds = remainingSeconds % 60
        return "\(remainingSeconds / 60):\(String(format: "%02d", seconds))"
    }

    var body: some View {
        ZStack {
            AppColors.bgBreakOverlay
                .ignoresSafeArea()

            VStack(spacing: AppSpacing.xl) {
                Image(systemName: "eye.fill")
                    .font(.system(size: 64))
                    .foregroundStyle(AppColors.brandBreak)

                Text("break.overlay.title")
                    .font(AppTypography.headline1)
                    .foregroundStyle(.white)

                TimerRing(
                    progress: progress,
                    timerState: timerState,
                    formattedTime: formattedTime
                )
                .accessibilityIdentifier(AccessibilityID.breakCountdown)

                Text("break.overlay.instruction")
                    .font(AppTypography.body)
                    .foregroundStyle(AppColors.textSecondary)
                    .multilineTextAlignment(.center)
                    .accessibilityIdentifier(AccessibilityID.breakInstruction)
            }
        }
        .accessibilityIdentifier(AccessibilityID.breakOverlay)
    }
}
