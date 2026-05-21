import SwiftUI

@main
struct EyeBreakIslandApp: App {
    @StateObject private var subscriptionService = SubscriptionService()
    @StateObject private var timerService = TimerService()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(subscriptionService)
                .environmentObject(timerService)
                .task {
                    let apiKey = Bundle.main.infoDictionary?["RC_PUBLIC_KEY"] as? String ?? ""
                    subscriptionService.configure(apiKey: apiKey)
                }
        }
    }
}
