// File: Views/Onboarding/OnboardingContainerView.swift
// F-002: Onboarding flow (Age → Zone2 Explainer → Notification → Paywall)
// Source: Apple HIG — https://developer.apple.com/design/human-interface-guidelines/onboarding
// "Guide people quickly to the experience they're looking for."

import SwiftUI

struct OnboardingContainerView: View {
    @AppStorage("hasCompletedOnboarding") private var hasCompletedOnboarding = false
    @Environment(SubscriptionService.self) private var subscriptionService
    @State private var viewModel = OnboardingViewModel()

    var body: some View {
        TabView(selection: $viewModel.currentStep) {
            AgeInputView(viewModel: viewModel)
                .tag(0)
            Zone2ExplainerView(viewModel: viewModel)
                .tag(1)
            NotificationPermissionView(viewModel: viewModel)
                .tag(2)
            PaywallView(subscriptionService: subscriptionService, onComplete: {
                hasCompletedOnboarding = true
            })
                .tag(3)
        }
        .tabViewStyle(.page(indexDisplayMode: .never))
        .accessibilityIdentifier("screen_onboarding")
    }
}
