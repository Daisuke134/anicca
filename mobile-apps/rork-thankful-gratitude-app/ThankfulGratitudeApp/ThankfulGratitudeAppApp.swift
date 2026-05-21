import SwiftUI
import SwiftData
import RevenueCat

@main
struct ThankfulGratitudeAppApp: App {
    var sharedModelContainer: ModelContainer = {
        let schema = Schema([GratitudeEntry.self])
        do {
            let config = ModelConfiguration(schema: schema, isStoredInMemoryOnly: false)
            return try ModelContainer(for: schema, configurations: [config])
        } catch {
            // Fallback to in-memory to avoid crash. Data won't persist but app stays alive.
            let fallback = ModelConfiguration(schema: schema, isStoredInMemoryOnly: true)
            return try! ModelContainer(for: schema, configurations: [fallback])
        }
    }()

    init() {
        RevenueCatService.configure()
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .modelContainer(sharedModelContainer)
    }
}
