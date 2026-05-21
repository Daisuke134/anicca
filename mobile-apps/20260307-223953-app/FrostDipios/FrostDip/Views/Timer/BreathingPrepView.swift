import SwiftUI

struct BreathingPrepView: View {
    let phase: BreathPhase
    let onSkip: () -> Void

    @State private var circleScale: CGFloat = 0.6

    var body: some View {
        VStack(spacing: Theme.Spacing.xl) {
            Spacer()

            Text(phaseText)
                .font(Theme.Typography.title)
                .foregroundStyle(Theme.Colors.accent)
                .accessibilityIdentifier(AccessibilityID.breathingPhaseLabel)

            Circle()
                .fill(Theme.Colors.accent.opacity(0.3))
                .frame(width: 200, height: 200)
                .scaleEffect(circleScale)
                .animation(Theme.Animation.slow, value: circleScale)
                .accessibilityIdentifier(AccessibilityID.breathingCircle)
                .onChange(of: phase) { _, newPhase in
                    switch newPhase {
                    case .inhale: circleScale = 1.0
                    case .hold: break
                    case .exhale: circleScale = 0.6
                    }
                }

            Text(phaseDetail)
                .font(Theme.Typography.subheadline)
                .foregroundStyle(Theme.Colors.secondaryLabel)

            Spacer()

            Button {
                onSkip()
            } label: {
                Text("Skip")
                    .font(Theme.Typography.headline)
                    .frame(maxWidth: .infinity, minHeight: 44)
            }
            .buttonStyle(.bordered)
            .accessibilityIdentifier(AccessibilityID.breathingSkip)
        }
        .padding(Theme.Spacing.md)
    }

    private var phaseText: String {
        switch phase {
        case .inhale: return "Breathe In"
        case .hold: return "Hold"
        case .exhale: return "Breathe Out"
        }
    }

    private var phaseDetail: String {
        switch phase {
        case .inhale: return "4 seconds"
        case .hold: return "7 seconds"
        case .exhale: return "8 seconds"
        }
    }
}
