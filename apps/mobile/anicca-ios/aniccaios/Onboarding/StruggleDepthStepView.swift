import SwiftUI

/// Phase 1: HOOK — frequency question with 1-tap auto-advance.
struct StruggleDepthStepView: View {
    let next: () -> Void
    @EnvironmentObject private var appState: AppState

    /// Phase 1 answer set from the answer→change mapping:
    /// rarely / weekly / daily / many_times_daily.
    private let options: [(key: String, labelKey: String)] = [
        ("rarely", "onboarding_depth_rarely"),
        ("weekly", "onboarding_depth_weekly"),
        ("daily", "onboarding_depth_daily"),
        ("many_times_daily", "onboarding_depth_many_times_daily")
    ]

    var body: some View {
        VStack(spacing: 24) {
            Spacer()

            Text(String(localized: "onboarding_depth_title"))
                .font(.system(size: 32, weight: .bold))
                .multilineTextAlignment(.center)
                .foregroundStyle(AppTheme.Colors.label)
                .padding(.horizontal, 24)

            VStack(spacing: 12) {
                ForEach(options, id: \.key) { option in
                    Button {
                        selectFrequency(option.key)
                    } label: {
                        Text(String(localized: String.LocalizationValue(option.labelKey)))
                            .font(.system(size: 18, weight: .medium))
                            .foregroundStyle(AppTheme.Colors.label)
                            .frame(maxWidth: .infinity)
                            .frame(height: 56)
                            .background(AppTheme.Colors.buttonUnselected)
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                    .buttonStyle(.plain)
                    .accessibilityIdentifier("onboarding-depth-\(option.key)")
                }
            }
            .padding(.horizontal, 24)

            Spacer()
            Spacer()
        }
        .background(AppBackground())
    }

    private func selectFrequency(_ frequency: String) {
        var profile = appState.userProfile
        profile.struggleFrequency = frequency
        appState.updateUserProfile(profile, sync: true)
        // Phase 1: the same answer drives the schedule proposal and the
        // message intensity through the personalization profile.
        var personalization = appState.personalizationProfile
        personalization.struggleFrequency = frequency
        appState.updatePersonalizationProfile(personalization)
        AnalyticsManager.shared.track(.onboardingStruggleDepthCompleted, properties: [
            "frequency": frequency
        ])
        next()
    }
}
