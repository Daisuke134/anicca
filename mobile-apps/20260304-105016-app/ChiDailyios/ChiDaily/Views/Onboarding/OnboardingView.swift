import SwiftUI

struct OnboardingView: View {
    @Binding var hasCompletedOnboarding: Bool
    @State private var currentPage = 0
    @Environment(SubscriptionService.self) private var subscriptionService

    var body: some View {
        TabView(selection: $currentPage) {
            OnboardingScreen1(onNext: { currentPage = 1 })
                .tag(0)
            OnboardingScreen2(onNext: { currentPage = 2 })
                .tag(1)
            OnboardingScreen3(
                onComplete: { hasCompletedOnboarding = true },
                onSkip: { hasCompletedOnboarding = true }
            )
            .tag(2)
        }
        .tabViewStyle(.page(indexDisplayMode: .always))
        .indexViewStyle(.page(backgroundDisplayMode: .always))
        .background(Color.brandCream.ignoresSafeArea())
    }
}
