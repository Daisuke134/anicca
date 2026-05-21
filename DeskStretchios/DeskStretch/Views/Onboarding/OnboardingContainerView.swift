import SwiftUI

struct OnboardingContainerView: View {
    @Environment(AppState.self) private var appState
    @State private var currentStep = 0

    var body: some View {
        NavigationStack {
            Group {
                switch currentStep {
                case 0:
                    ProblemEmpathyView(onNext: { currentStep = 1 })
                case 1:
                    PainAreaSelectionView(onNext: { currentStep = 2 })
                case 2:
                    PaywallView(onDismiss: { completeOnboarding() })
                default:
                    EmptyView()
                }
            }
            .animation(.easeInOut, value: currentStep)
        }
        .accessibilityIdentifier("onboarding_container")
    }

    private func completeOnboarding() {
        appState.persistOnboardingComplete()
    }
}
