import SwiftUI

struct MainTabView: View {
    @EnvironmentObject var subscriptionManager: SubscriptionManager
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            DashboardView()
                .environmentObject(subscriptionManager)
                .tabItem {
                    Image(systemName: "house.fill")
                    Text(L10n.isJapaneseLang ? "ホーム" : "Home")
                }
                .tag(0)

            SettingsView()
                .environmentObject(subscriptionManager)
                .tabItem {
                    Image(systemName: "gearshape.fill")
                    Text(L10n.settingsTitle)
                }
                .tag(1)
        }
        .accentColor(Color(hex: "#2dd4bf"))
        .preferredColorScheme(.dark)
    }
}
