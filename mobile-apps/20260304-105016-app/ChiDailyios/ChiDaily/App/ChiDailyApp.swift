import SwiftUI
import SwiftData
import RevenueCat

@main
struct ChiDailyApp: App {
    @State private var subscriptionService = SubscriptionService()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(subscriptionService)
                .modelContainer(for: CheckIn.self)
                .onAppear {
                    subscriptionService.configure()
                }
        }
    }
}
