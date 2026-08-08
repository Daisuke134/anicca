import AuthenticationServices
import UIKit

@MainActor
final class WebOAuthCallbackAuthorizer: NSObject, OAuthCallbackAuthorizing, ASWebAuthenticationPresentationContextProviding {
    private let callbackScheme: String
    private var activeSession: ASWebAuthenticationSession?

    init(callbackScheme: String) {
        self.callbackScheme = callbackScheme
    }

    func authorize(url: URL, expectedState: String) async throws -> URL {
        try await withCheckedThrowingContinuation { continuation in
            let session = ASWebAuthenticationSession(url: url, callbackURLScheme: callbackScheme) { [weak self] callbackURL, error in
                self?.activeSession = nil
                if let callbackURL {
                    continuation.resume(returning: callbackURL)
                } else {
                    let message = error?.localizedDescription ?? "OAuth callback was not received"
                    continuation.resume(throwing: APIError.transport(message))
                }
            }
            session.presentationContextProvider = self
            session.prefersEphemeralWebBrowserSession = false
            activeSession = session
            guard session.start() else {
                activeSession = nil
                continuation.resume(throwing: APIError.transport("OAuth session could not start"))
                return
            }
        }
    }

    func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        let window = UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }
            .flatMap(\.windows)
            .first(where: \.isKeyWindow)
        return window ?? UIWindow(frame: .zero)
    }
}
