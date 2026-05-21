import SwiftUI

struct ExperienceLevelView: View {
    var selectedLevel: ExperienceLevel?
    var onSelect: (ExperienceLevel) -> Void
    var onContinue: () -> Void

    private var mirrorText: String {
        guard let level = selectedLevel else { return "" }
        switch level {
        case .beginner: return "Great, we'll set you up with a beginner protocol"
        case .intermediate: return "Nice, we'll match you with intermediate challenges"
        case .advanced: return "Impressive, you'll get our advanced protocols"
        }
    }

    var body: some View {
        VStack(spacing: Theme.Spacing.lg) {
            Spacer()

            Text("How experienced are you with cold plunging?")
                .font(Theme.Typography.title2)
                .multilineTextAlignment(.center)
                .foregroundStyle(Theme.Colors.label)
                .padding(.horizontal, Theme.Spacing.lg)

            VStack(spacing: Theme.Spacing.sm) {
                levelButton(.beginner, icon: "leaf", title: "Beginner", subtitle: "New to cold exposure", id: AccessibilityID.onboardingExperienceBeginner)
                levelButton(.intermediate, icon: "flame", title: "Intermediate", subtitle: "Regular cold plunger", id: AccessibilityID.onboardingExperienceIntermediate)
                levelButton(.advanced, icon: "bolt.fill", title: "Advanced", subtitle: "Seasoned ice warrior", id: AccessibilityID.onboardingExperienceAdvanced)
            }
            .padding(.horizontal, Theme.Spacing.lg)

            if selectedLevel != nil {
                Text(mirrorText)
                    .font(Theme.Typography.callout)
                    .foregroundStyle(Theme.Colors.accent)
                    .transition(.opacity)
            }

            Spacer()

            Button(action: onContinue) {
                Text("Continue")
                    .font(Theme.Typography.headline)
                    .foregroundStyle(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, Theme.Spacing.md)
                    .background(selectedLevel != nil ? Theme.Colors.primary : Theme.Colors.primary.opacity(0.4))
                    .clipShape(RoundedRectangle(cornerRadius: Theme.CornerRadius.medium))
            }
            .disabled(selectedLevel == nil)
            .accessibilityIdentifier(AccessibilityID.onboardingContinue)
            .padding(.horizontal, Theme.Spacing.lg)
            .padding(.bottom, Theme.Spacing.xl)
        }
        .animation(Theme.Animation.standard, value: selectedLevel)
    }

    private func levelButton(_ level: ExperienceLevel, icon: String, title: String, subtitle: String, id: String) -> some View {
        Button(action: { onSelect(level) }) {
            HStack(spacing: Theme.Spacing.md) {
                Image(systemName: icon)
                    .font(.title2)
                    .foregroundStyle(selectedLevel == level ? Theme.Colors.accent : Theme.Colors.secondaryLabel)
                    .frame(width: 32)

                VStack(alignment: .leading, spacing: Theme.Spacing.xxs) {
                    Text(title)
                        .font(Theme.Typography.headline)
                        .foregroundStyle(Theme.Colors.label)
                    Text(subtitle)
                        .font(Theme.Typography.caption)
                        .foregroundStyle(Theme.Colors.secondaryLabel)
                }

                Spacer()

                if selectedLevel == level {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(Theme.Colors.accent)
                }
            }
            .padding(Theme.Spacing.md)
            .background(
                RoundedRectangle(cornerRadius: Theme.CornerRadius.medium)
                    .stroke(selectedLevel == level ? Theme.Colors.accent : Theme.Colors.secondaryLabel.opacity(0.3), lineWidth: selectedLevel == level ? 2 : 1)
            )
        }
        .accessibilityIdentifier(id)
    }
}
