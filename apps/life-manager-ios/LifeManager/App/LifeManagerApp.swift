import SwiftUI

@main
struct LifeManagerApp: App {
    private let environment: AppEnvironment

    init() {
        environment = AppEnvironment()
    }

    var body: some Scene {
        WindowGroup {
            RootView(environment: environment)
        }
    }
}
