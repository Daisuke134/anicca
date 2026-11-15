import AuthenticationServices
import Combine
import CryptoKit
import Foundation
import OSLog

@MainActor
final class AuthCoordinator: ObservableObject {
    static let shared = AuthCoordinator()
    @Published private(set) var isSigningIn = false
    @Published private(set) var signInFailed = false
    private let logger = Logger(subsystem: "com.anicca.ios", category: "AuthCoordinator")
    private var currentNonce: String?
    private var attemptID = UUID()
    private var revocationObserver: NSObjectProtocol?
    private var signInCompletion: ((Bool) -> Void)?

    private init() {}

    lazy var presentationDelegate = AuthPresentationDelegate(coordinator: self)

    func configure(_ request: ASAuthorizationAppleIDRequest) {
        attemptID = UUID()
        isSigningIn = true
        signInFailed = false
        let nonce = randomNonceString()
        currentNonce = nonce
        request.requestedScopes = [.fullName, .email]
        request.nonce = sha256Base64(nonce)
        AnalyticsManager.shared.track(.appleSignInStarted)
    }

    func startSignIn() {
        guard !isSigningIn else { return }
        let request = ASAuthorizationAppleIDProvider().createRequest()
        configure(request)
        let controller = ASAuthorizationController(authorizationRequests: [request])
        controller.delegate = presentationDelegate
        controller.presentationContextProvider = presentationDelegate
        controller.performRequests()
    }

    func completeSignIn(result: Result<ASAuthorization, Error>) {
        completeSignIn(result: result, completion: nil)
    }

    func completeSignIn(result: Result<ASAuthorization, Error>, completion: ((Bool) -> Void)?) {
        guard isSigningIn else { completion?(false); return }
        signInCompletion = completion
        switch result {
        case .success(let authorization):
            handleAuthorization(authorization)
        case .failure(let error):
            finishSignIn(outcome: (error as? ASAuthorizationError)?.code == .canceled ? "cancelled" : "failed")
        }
    }

    private func finishSignIn(outcome: String) {
        currentNonce = nil
        isSigningIn = false
        signInFailed = outcome == "failed"
        AnalyticsManager.shared.track(.appleSignInResult, properties: ["result": outcome])
        let completion = signInCompletion
        signInCompletion = nil
        completion?(outcome == "succeeded")
    }

    func invalidatePendingSignIn() {
        attemptID = UUID()
        currentNonce = nil
        isSigningIn = false
        signInCompletion?(false)
        signInCompletion = nil
    }

    func signOut() {
        AppState.shared.signOutPreservingSensorAccess()
    }

    func deleteAccount() async -> Bool {
        guard case .signedIn(let credentials) = AppState.shared.authStatus else { return false }
        var request = URLRequest(url: AppConfig.proxyBaseURL.appendingPathComponent("mobile/account"))
        request.httpMethod = "DELETE"
        request.setValue(AppState.shared.resolveDeviceId(), forHTTPHeaderField: "device-id")
        request.setValue(credentials.userId, forHTTPHeaderField: "user-id")
        do {
            try await NetworkSessionManager.shared.setAuthHeaders(for: &request)
            let (_, response) = try await NetworkSessionManager.shared.session.data(for: request)
            guard (response as? HTTPURLResponse)?.statusCode == 204,
                  AppState.shared.authStatus.userId == credentials.userId else { return false }
            AppState.shared.signOutAndWipe()
            return true
        } catch {
            return false
        }
    }

    func startObservingCredentials() {
        guard revocationObserver == nil else { return }
        revocationObserver = NotificationCenter.default.addObserver(
            forName: ASAuthorizationAppleIDProvider.credentialRevokedNotification,
            object: nil, queue: .main
        ) { _ in
            Task { @MainActor in await self.validateCredentialState() }
        }
        Task { await validateCredentialState() }
    }

    func validateCredentialState() async {
        guard case .signedIn(let credentials) = AppState.shared.authStatus else { return }
        // Backend IDs are not Apple subjects. Old sessions must authorize again.
        guard let appleUserID = credentials.appleUserId else {
            AppState.shared.requireAppleReauthentication()
            return
        }
        let generation = attemptID
        do {
            let state = try await ASAuthorizationAppleIDProvider().credentialState(forUserID: appleUserID)
            guard generation == attemptID,
                  case .signedIn(let current) = AppState.shared.authStatus,
                  current.appleUserId == appleUserID else { return }
            switch state {
            case .authorized:
                break
            case .revoked, .notFound, .transferred:
                // Transferred subjects require fresh authorization and backend migration.
                AppState.shared.signOutAndWipe()
            @unknown default:
                AppState.shared.signOutAndWipe()
            }
        } catch {
            // Offline is not revocation. Retry on the next foreground transition.
            logger.notice("Apple credential state unavailable")
        }
    }

    struct FirstGrant: Codable {
        let userId: String
        let displayName: String
        let email: String?

        init(userId: String, displayName: String, email: String?, previous: FirstGrant? = nil) {
            let matching = previous?.userId == userId ? previous : nil
            self.userId = userId
            self.displayName = displayName.isEmpty ? (matching?.displayName ?? "") : displayName
            self.email = email ?? matching?.email
        }
    }

    private func handleAuthorization(_ authorization: ASAuthorization) {
        guard let credential = authorization.credential as? ASAuthorizationAppleIDCredential,
              let nonce = currentNonce,
              let tokenData = credential.identityToken,
              let token = String(data: tokenData, encoding: .utf8),
              let codeData = credential.authorizationCode,
              let code = String(data: codeData, encoding: .utf8), !code.isEmpty else {
            finishSignIn(outcome: "failed")
            return
        }
        currentNonce = nil
        let name = credential.fullName.map { PersonNameComponentsFormatter().string(from: $0) } ?? ""
        let saved = KeychainService.load(account: "appleFirstGrant")
            .flatMap { try? JSONDecoder().decode(FirstGrant.self, from: $0) }
        let grant = FirstGrant(userId: credential.user, displayName: name,
                               email: credential.email, previous: saved)
        do {
            // Apple supplies these once; retain them even if the network request fails.
            try KeychainService.save(JSONEncoder().encode(grant), account: "appleFirstGrant")
        } catch {
            finishSignIn(outcome: "failed")
            return
        }
        let generation = attemptID
        Task {
            await verifyWithBackend(identityToken: token, authorizationCode: code,
                                    nonce: nonce, grant: grant, generation: generation)
        }
    }

    private func verifyWithBackend(identityToken: String, authorizationCode: String,
                                   nonce: String, grant: FirstGrant, generation: UUID) async {
        var request = URLRequest(url: AppConfig.appleAuthURL)
        request.httpMethod = "POST"
        request.setValue(AppState.shared.resolveDeviceId(), forHTTPHeaderField: "device-id")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        var payload: [String: Any] = [
            "identity_token": identityToken, "authorization_code": authorizationCode,
            "nonce": nonce, "user_id": grant.userId
        ]
        if !grant.displayName.isEmpty { payload["display_name"] = grant.displayName }
        if let email = grant.email { payload["email"] = email }
        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: payload)
            let (data, response) = try await warmSession.data(for: request)
            guard generation == attemptID else { return }
            guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode),
                  let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let backendUserID = json["userId"] as? String, !backendUserID.isEmpty,
                  let token = json["token"] as? String, !token.isEmpty,
                  let refreshToken = json["refreshToken"] as? String, !refreshToken.isEmpty else {
                finishSignIn(outcome: "failed")
                return
            }
            let saved = KeychainService.load(account: "com.anicca.userCredentials")
                .flatMap { try? JSONDecoder().decode(UserCredentials.self, from: $0) }
            let previous = saved?.userId == backendUserID &&
                (saved?.appleUserId == nil || saved?.appleUserId == grant.userId) ? saved : nil
            let name = (json["displayName"] as? String).flatMap { $0.isEmpty ? nil : $0 }
            var credentials = UserCredentials(
                userId: backendUserID,
                displayName: name ?? (grant.displayName.isEmpty ? (previous?.displayName ?? "") : grant.displayName),
                email: json["email"] as? String ?? grant.email ?? previous?.email
            )
            credentials.appleUserId = grant.userId
            credentials.jwtAccessToken = token
            credentials.accessTokenExpiresAt = (json["expiresAt"] as? TimeInterval)
                .map { Date(timeIntervalSince1970: $0 / 1000) }
            try KeychainService.save(Data(refreshToken.utf8), account: "rt")
            do {
                try AppState.shared.persistAuthenticatedCredentials(credentials)
            } catch {
                KeychainService.delete(account: "rt")
                throw error
            }
            if let saved, saved.userId != backendUserID {
                AppState.shared.updateUserProfile(UserProfile(), sync: false)
                AppState.shared.updateSubscriptionInfo(.free)
            }
            AppState.shared.updateUserCredentials(credentials)
            finishSignIn(outcome: "succeeded")
            await AppState.shared.bootstrapProfileFromServerIfAvailable()
        } catch {
            guard generation == attemptID else { return }
            logger.error("Apple sign-in verification or secure storage failed")
            finishSignIn(outcome: "failed")
        }
    }

    // MARK: - Nonce generation
    
    private func randomNonceString(length: Int = 32) -> String {
        precondition(length > 0)
        let charset: [Character] = Array("0123456789ABCDEFGHIJKLMNOPQRSTUVXYZabcdefghijklmnopqrstuvwxyz-._")
        var result = ""
        var remainingLength = length
        
        while remainingLength > 0 {
            let randoms: [UInt8] = (0..<16).map { _ in
                var random: UInt8 = 0
                let errorCode = SecRandomCopyBytes(kSecRandomDefault, 1, &random)
                if errorCode != errSecSuccess {
                    fatalError("Unable to generate nonce. SecRandomCopyBytes failed with OSStatus \(errorCode)")
                }
                return random
            }
            
            randoms.forEach { random in
                if remainingLength == 0 {
                    return
                }
                
                if random < charset.count {
                    result.append(charset[Int(random)])
                    remainingLength -= 1
                }
            }
        }
        
        return result
    }
    
    private func sha256Base64(_ input: String) -> String? {
        let inputData = Data(input.utf8)
        let hashedData = SHA256.hash(data: inputData)
        return Data(hashedData).base64EncodedString()
    }
    
    private var warmSession: URLSession {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.waitsForConnectivity = false
        configuration.timeoutIntervalForRequest = 10
        return URLSession(configuration: configuration)
    }
    
}
