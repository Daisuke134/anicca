import SwiftUI

@main
@MainActor
struct LifeManagerApp: App {
    private let environment: AppEnvironment
    private let viewModel: AppViewModel?

    init() {
        environment = AppEnvironment()
        viewModel = environment.makeViewModel()
    }

    var body: some Scene {
        WindowGroup {
            RootView(environment: environment, viewModel: viewModel)
        }
    }
}
