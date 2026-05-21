import SwiftUI
import SwiftData

@main
struct AffirmFlowApp: App {
    @State private var settings = UserSettings()
    @State private var affirmationService = AffirmationService()

    init() {
        SubscriptionService.shared.configure()
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(settings)
                .environment(affirmationService)
        }
        .modelContainer(for: Affirmation.self)
    }
}
