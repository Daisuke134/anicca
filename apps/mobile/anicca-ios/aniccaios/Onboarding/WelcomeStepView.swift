import SwiftUI

struct WelcomeStepView: View {
    let next: () -> Void
    @EnvironmentObject private var appState: AppState

    var body: some View {
        VStack {
            Spacer()

            VStack(spacing: 24) {
                // Poyo introduces itself first (design doc §3: the mascot is
                // the one who speaks). One screen, no extra steps added.
                PoyoView(expression: .happy, size: 96)

                Text(String(localized: "onboarding_welcome_poyo_intro"))
                    .font(.system(size: 16, weight: .medium))
                    .foregroundStyle(AppTheme.Colors.label.opacity(0.85))
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)

                Text(String(localized: "onboarding_welcome_title"))
                    .font(.system(size: 44, weight: .bold))
                    .lineLimit(3)
                    .minimumScaleFactor(0.7)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(AppTheme.Colors.label)

                VStack(spacing: 8) {
                    Text(String(localized: "onboarding_welcome_subtitle_line1"))
                        .font(.system(size: 18, weight: .medium))
                        .foregroundStyle(AppTheme.Colors.label.opacity(0.8))
                        .multilineTextAlignment(.center)

                    Text(String(localized: "onboarding_welcome_subtitle_line2"))
                        .font(.system(size: 18, weight: .medium))
                        .foregroundStyle(AppTheme.Colors.label.opacity(0.8))
                        .multilineTextAlignment(.center)
                }
                .padding(.horizontal, 32)
            }

            Spacer()

            Button {
                next()
            } label: {
                Text(String(localized: "onboarding_welcome_cta"))
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(.white)
                    .frame(maxWidth: .infinity)
                    .frame(height: 56)
                    .background(AppTheme.Colors.accent)
                    .clipShape(RoundedRectangle(cornerRadius: 28))
            }
            .accessibilityIdentifier("onboarding-welcome-cta")
            .padding(.horizontal, 16)
            .padding(.bottom, 48)
        }
        .background(AppBackground())
    }
}
