import Foundation

@MainActor
final class AppComposition {
    let viewModel: AppViewModel
    let deviceService: DeviceServicing

    init(
        baseURL: URL,
        callbackScheme: String,
        transport: HTTPTransport? = nil,
        sessionStore: SessionStoring? = nil,
        callbackAuthorizer: OAuthCallbackAuthorizing? = nil
    ) {
        let sessionStore = sessionStore ?? KeychainSessionStore()
        let transport = transport ?? URLSessionTransport()
        let sessionRelay = SessionPropagationRelay()
        let sessionAPI = APIClient(
            baseURL: baseURL,
            transport: transport,
            sessionStore: sessionStore,
            refresh: { _ in throw APIError.refreshRejected }
        )
        let auth = AuthService(
            api: sessionAPI,
            sessionStore: sessionStore,
            callbackAuthorizer: callbackAuthorizer ?? WebOAuthCallbackAuthorizer(callbackScheme: callbackScheme),
            sessionRelay: sessionRelay
        )
        let authenticatedAPI = APIClient(
            baseURL: baseURL,
            transport: transport,
            sessionStore: sessionStore,
            refresh: { session in try await auth.refresh(session) }
        )
        sessionRelay.attach(sessionAPI)
        sessionRelay.attach(authenticatedAPI)
        let profileService = ProfileService(api: authenticatedAPI)
        let callService = CallService(api: authenticatedAPI)
        let accountService = AccountService(api: authenticatedAPI)
        deviceService = DeviceService(api: authenticatedAPI)
        let paywallViewModel = SoftPaywallViewModel(purchasing: nil)
        let appViewModel = AppViewModel(
            auth: auth,
            profile: profileService,
            analysis: AnalysisService(api: authenticatedAPI),
            chat: ChatService(api: authenticatedAPI),
            settings: SettingsViewModel(
                profile: profileService,
                auth: auth,
                calls: callService,
                account: accountService,
                device: deviceService
            ),
            paywall: paywallViewModel
        )
        appViewModel.bindSettingsProfileHandler()
        viewModel = appViewModel
    }
}
