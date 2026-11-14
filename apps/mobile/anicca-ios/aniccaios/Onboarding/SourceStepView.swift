import SwiftUI

struct SourceStepView: View {
    let next: () -> Void
    @EnvironmentObject private var appState: AppState
    @State private var isOtherSelected = false
    @State private var otherText = ""

    private let options: [(key: String, labelKey: String)] = [
        ("tiktok", "onboarding_source_tiktok"),
        ("instagram", "onboarding_source_instagram"),
        ("youtube", "onboarding_source_youtube"),
        ("x", "onboarding_source_x"),
        ("app_store_search", "onboarding_source_app_store_search"),
        ("friend", "onboarding_source_friend"),
        ("reddit", "onboarding_source_reddit"),
        ("other", "onboarding_source_other")
    ]

    var body: some View {
        VStack(spacing: 24) {
            ScrollViewReader { proxy in
                ScrollView {
                    VStack(spacing: 24) {
                        Text(String(localized: "onboarding_source_title"))
                            .font(.system(size: 32, weight: .bold))
                            .multilineTextAlignment(.center)
                            .foregroundStyle(AppTheme.Colors.label)
                            .padding(.horizontal, 24)
                            .padding(.top, 40)
                            .accessibilityIdentifier("onboarding-source-title")

                        VStack(spacing: 12) {
                            ForEach(options, id: \.key) { option in
                                Button {
                                    if option.key == "other" {
                                        isOtherSelected = true
                                    } else {
                                        selectSource(option.key)
                                    }
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
                                .accessibilityIdentifier("onboarding-source-\(option.key)")
                            }
                        }
                        .padding(.horizontal, 24)

                        if isOtherSelected {
                            VStack(spacing: 12) {
                                TextField(String(localized: "onboarding_source_other_placeholder"), text: $otherText)
                                    .font(.system(size: 18))
                                    .foregroundStyle(AppTheme.Colors.label)
                                    .padding(16)
                                    .background(AppTheme.Colors.buttonUnselected)
                                    .clipShape(RoundedRectangle(cornerRadius: 12))
                                    .accessibilityIdentifier("onboarding-source-other-text")

                                Button {
                                    selectSource("other")
                                } label: {
                                    Text(String(localized: "common_continue"))
                                        .font(.system(size: 18, weight: .semibold))
                                        .foregroundStyle(.white)
                                        .frame(maxWidth: .infinity)
                                        .frame(height: 56)
                                        .background(AppTheme.Colors.buttonSelected)
                                        .clipShape(RoundedRectangle(cornerRadius: 28))
                                }
                                .accessibilityIdentifier("onboarding-source-continue")
                            }
                            .padding(.horizontal, 24)
                            .id("onboarding-source-other-input")
                        }
                    }
                    .padding(.bottom, 24)
                }
                .onChange(of: isOtherSelected) { selected in
                    if selected {
                        withAnimation {
                            proxy.scrollTo("onboarding-source-other-input", anchor: .bottom)
                        }
                    }
                }
            }

            Button {
                next()
            } label: {
                Text(String(localized: "common_skip"))
                    .font(.subheadline).foregroundStyle(AppTheme.Colors.secondaryLabel)
                    .frame(minHeight: 44)
            }
            .accessibilityIdentifier("onboarding-source-skip")
            .padding(.bottom, 24)
        }
        .background(AppBackground())
    }

    private func selectSource(_ source: String) {
        var profile = appState.userProfile
        profile.acquisitionSource = source
        appState.updateUserProfile(profile, sync: true)

        var properties = ["source": source]
        let trimmedText = otherText.trimmingCharacters(in: .whitespacesAndNewlines)
        if source == "other", !trimmedText.isEmpty {
            properties["other_text"] = trimmedText
        }
        AnalyticsManager.shared.track(.onboardingSourceAnswered, properties: properties)
        SubscriptionManager.shared.setAcquisitionSourceAttribute(source)
        next()
    }
}
