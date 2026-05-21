import SwiftUI

struct ContentView: View {
    @Environment(AppState.self) private var appState

    var body: some View {
        if !appState.hasCompletedOnboarding {
            OnboardingContainerView()
        } else {
            MainTabView()
        }
    }
}

struct MainTabView: View {
    var body: some View {
        TabView {
            TimerView()
                .tabItem {
                    Label(String(localized: "Timer"), systemImage: "timer")
                }

            StretchLibraryView()
                .tabItem {
                    Label(String(localized: "Library"), systemImage: "books.vertical")
                }

            ProgressDashboardView()
                .tabItem {
                    Label(String(localized: "Progress"), systemImage: "chart.bar")
                }

            SettingsView()
                .tabItem {
                    Label(String(localized: "Settings"), systemImage: "gearshape")
                }
        }
    }
}
