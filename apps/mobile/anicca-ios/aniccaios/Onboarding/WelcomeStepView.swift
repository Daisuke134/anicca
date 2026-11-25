import SwiftUI

struct WelcomeStepView: View {
    let next: () -> Void

    var body: some View {
        OnboardingPage {
            Text("Anicca")
                .font(.system(.title, design: .serif))
            Spacer(minLength: 24)
            Image(systemName: "sun.max")
                .font(.system(size: 48, weight: .ultraLight))
                .foregroundStyle(AppTheme.Colors.accent)
                .accessibilityHidden(true)
            // Poyo introduces itself first (design doc §3: the mascot is
            // the one who speaks). One screen, no extra steps added.
            PoyoView(expression: .happy, size: 96)
            Text(String(localized: "onboarding_welcome_poyo_intro"))
                .font(.system(size: 16, weight: .medium))
                .foregroundStyle(AppTheme.Colors.label.opacity(0.85))
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)
            Text(String(localized: "onboarding_welcome_title"))
                .font(AppTheme.Typography.onboardingTitle)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)
                .accessibilityAddTraits(.isHeader)
            Text(String(localized: "onboarding_welcome_subtitle_line1"))
                .font(.body)
                .foregroundStyle(AppTheme.Colors.secondaryLabel)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 24)
        } footer: {
            PrimaryButton(title: String(localized: "onboarding_welcome_cta"), action: next)
                .accessibilityIdentifier("onboarding-welcome-cta")
        }
    }
}
