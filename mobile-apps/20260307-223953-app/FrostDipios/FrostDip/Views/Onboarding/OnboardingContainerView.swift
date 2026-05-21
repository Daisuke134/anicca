import SwiftUI

struct OnboardingContainerView: View {
    @State private var viewModel = OnboardingViewModel()
    var onComplete: () -> Void

    var body: some View {
        ZStack {
            Theme.Colors.background
                .ignoresSafeArea()

            switch viewModel.currentStep {
            case .welcome:
                WelcomeView(onGetStarted: { viewModel.advance() })
                    .transition(.asymmetric(
                        insertion: .move(edge: .trailing),
                        removal: .move(edge: .leading)
                    ))
            case .experience:
                ExperienceLevelView(
                    selectedLevel: viewModel.selectedExperienceLevel,
                    onSelect: { viewModel.selectExperienceLevel($0) },
                    onContinue: { viewModel.advance() }
                )
                .transition(.asymmetric(
                    insertion: .move(edge: .trailing),
                    removal: .move(edge: .leading)
                ))
            case .notification:
                NotificationPermissionView(onComplete: { viewModel.advance() })
                    .transition(.asymmetric(
                        insertion: .move(edge: .trailing),
                        removal: .move(edge: .leading)
                    ))
            case .paywall:
                PaywallView(
                    isOnboarding: true,
                    onDismiss: {
                        viewModel.completeOnboarding()
                        onComplete()
                    }
                )
                .transition(.opacity)
            }
        }
        .animation(Theme.Animation.standard, value: viewModel.currentStep)
    }
}
