import SwiftUI

struct WelcomeView: View {
    var onGetStarted: () -> Void

    var body: some View {
        VStack(spacing: Theme.Spacing.lg) {
            Spacer()

            Image(systemName: "snowflake")
                .font(.system(size: 80))
                .foregroundStyle(Theme.Colors.accent)
                .symbolEffect(.pulse)

            VStack(spacing: Theme.Spacing.sm) {
                Text("Tired of timing your cold plunge with a stopwatch?")
                    .font(Theme.Typography.title2)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(Theme.Colors.label)

                Text("FrostDip tracks your sessions, monitors your heart rate, and builds your cold exposure streak.")
                    .font(Theme.Typography.body)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(Theme.Colors.secondaryLabel)
            }
            .padding(.horizontal, Theme.Spacing.lg)

            Spacer()

            Button(action: onGetStarted) {
                Text("Get Started")
                    .font(Theme.Typography.headline)
                    .foregroundStyle(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, Theme.Spacing.md)
                    .background(Theme.Colors.primary)
                    .clipShape(RoundedRectangle(cornerRadius: Theme.CornerRadius.medium))
            }
            .accessibilityIdentifier(AccessibilityID.onboardingGetStarted)
            .padding(.horizontal, Theme.Spacing.lg)
            .padding(.bottom, Theme.Spacing.xl)
        }
    }
}
