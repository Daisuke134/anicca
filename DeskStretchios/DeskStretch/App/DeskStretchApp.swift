import SwiftUI
import RevenueCat

@main
struct DeskStretchApp: App {
    @State private var appState = AppState()

    init() {
        SubscriptionService.shared.configure(apiKey: "appl_OnzEebYgDRvFDkPgGmiChsmRStQ")
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(appState)
                .task {
                    appState.loadPersistedState()
                    appState.isPremium = await SubscriptionService.shared.checkPremiumStatus()
                }
        }
    }
}
