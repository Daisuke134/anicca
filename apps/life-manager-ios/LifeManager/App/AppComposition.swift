import Foundation

@MainActor
final class AppComposition {
    let viewModel: AppViewModel

    init(baseURL: URL, callbackScheme: String) {
        let sessionStore = KeychainSessionStore()
        let sessionAPI = APIClient(
            baseURL: baseURL,
            sessionStore: sessionStore,
            refresh: { _ in throw APIError.refreshRejected }
        )
        let auth = AuthService(
            api: sessionAPI,
            sessionStore: sessionStore,
            callbackAuthorizer: WebOAuthCallbackAuthorizer(callbackScheme: callbackScheme)
        )
        let authenticatedAPI = APIClient(
            baseURL: baseURL,
            sessionStore: sessionStore,
            refresh: { session in try await auth.refresh(session) }
        )
        viewModel = AppViewModel(
            auth: auth,
            profile: ProfileService(api: authenticatedAPI),
            analysis: AnalysisService(api: authenticatedAPI),
            chat: ChatService(api: authenticatedAPI)
        )
    }
}
