import SwiftUI

struct ContentView: View {
    @AppStorage("hasCompletedOnboarding") private var hasCompletedOnboarding = false

    var body: some View {
        if hasCompletedOnboarding {
            MainTabView()
        } else {
            OnboardingView(hasCompletedOnboarding: $hasCompletedOnboarding)
        }
    }
}

struct MainTabView: View {
    @Environment(SubscriptionService.self) private var subscriptionService

    var body: some View {
        TabView {
            HomeView()
                .tabItem {
                    Label(NSLocalizedString("Today", comment: ""), systemImage: "sun.max")
                }
            HistoryView()
                .tabItem {
                    Label(NSLocalizedString("History", comment: ""), systemImage: "calendar")
                }
        }
        .tint(Color.chiAccent)
    }
}
