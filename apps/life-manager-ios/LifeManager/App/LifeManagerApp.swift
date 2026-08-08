import SwiftUI

@main
@MainActor
struct LifeManagerApp: App {
    @UIApplicationDelegateAdaptor(LifeManagerAppDelegate.self) private var appDelegate
    private let environment: AppEnvironment
    private let composition: AppComposition?
    private let viewModel: AppViewModel?

    init() {
        let environment = AppEnvironment()
        self.environment = environment
        composition = environment.makeComposition()
        viewModel = composition?.viewModel
    }

    var body: some Scene {
        WindowGroup {
            RootView(
                environment: environment,
                viewModel: viewModel,
                onChatReady: { await appDelegate.retryDeviceRegistration() }
            )
                .task {
                    guard let composition else { return }
                    appDelegate.configure(
                        deviceService: composition.deviceService,
                        locale: preferredProductLocale,
                        timezone: TimeZone.current.identifier
                    )
                    _ = try? await appDelegate.requestAuthorizationAndRegisterIfNeeded()
                }
        }
    }

    private var preferredProductLocale: ProductLocale {
        guard let language = Locale.preferredLanguages.first?.lowercased(), language.hasPrefix("ja") else {
            return .en
        }
        return .ja
    }
}
