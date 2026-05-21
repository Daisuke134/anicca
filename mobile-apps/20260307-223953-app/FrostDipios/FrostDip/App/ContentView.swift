import SwiftUI

struct ContentView: View {
    @AppStorage("has_completed_onboarding") private var hasCompletedOnboarding = false

    var body: some View {
        if hasCompletedOnboarding {
            MainTabView()
        } else {
            OnboardingContainerView(onComplete: {
                hasCompletedOnboarding = true
            })
        }
    }
}

struct MainTabView: View {
    @AppStorage("selected_tab") private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            TimerView()
                .tabItem {
                    Label("Timer", systemImage: "timer")
                }
                .tag(0)
                .accessibilityIdentifier(AccessibilityID.tabTimer)

            HistoryView()
                .tabItem {
                    Label("History", systemImage: "clock.arrow.circlepath")
                }
                .tag(1)
                .accessibilityIdentifier(AccessibilityID.tabHistory)

            ProgressDashboardView()
                .tabItem {
                    Label("Progress", systemImage: "chart.line.uptrend.xyaxis")
                }
                .tag(2)
                .accessibilityIdentifier(AccessibilityID.tabProgress)

            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gearshape")
                }
                .tag(3)
                .accessibilityIdentifier(AccessibilityID.tabSettings)
        }
    }
}
