import SwiftUI
import SwiftData
import RevenueCat

struct ContentView: View {
    @State private var viewModel = AppViewModel()
    @State private var showPaywall: Bool = false

    private var language: AppLanguage { viewModel.language }

    var body: some View {
        Group {
            if !viewModel.hasCompletedOnboarding {
                OnboardingView(language: language) {
                    viewModel.hasCompletedOnboarding = true
                    showPaywall = true
                }
            } else {
                mainTabView
            }
        }
        .fullScreenCover(isPresented: $showPaywall) {
            PaywallView(
                language: language,
                onDismiss: { showPaywall = false },
                onPurchaseSuccess: {
                    viewModel.isPro = true
                    showPaywall = false
                }
            )
        }
        .task {
            await checkSubscriptionStatus()
        }
    }

    private var mainTabView: some View {
        TabView {
            HomeView(viewModel: viewModel)
                .tabItem {
                    Label(L10n.homeTab(language), systemImage: "house.fill")
                }

            HistoryView(viewModel: viewModel)
                .tabItem {
                    Label(L10n.historyTab(language), systemImage: "calendar")
                }

            SettingsView(viewModel: viewModel)
                .tabItem {
                    Label(L10n.settingsTab(language), systemImage: "gearshape.fill")
                }
        }
        .tint(Color(red: 0.83, green: 0.65, blue: 0.46))
    }

    private func checkSubscriptionStatus() async {
        guard RevenueCat.Purchases.isConfigured else { return }
        do {
            let info = try await RevenueCat.Purchases.shared.customerInfo()
            viewModel.isPro = info.entitlements["pro"]?.isActive == true
        } catch {
            // Silently fail
        }
    }
}
