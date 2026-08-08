import Foundation

protocol AuthServicing: Sendable {
    func restoreSession() async throws -> Session?
    func connectCalendar() async throws -> Session
    func refresh(_ session: Session) async throws -> Session
    func signOut() async throws
}

protocol ProfileServicing: Sendable {
    func fetch() async throws -> UserProfile
    func update(_ draft: ProfileDraft, idempotencyKey: UUID) async throws -> UserProfile
}

protocol AnalysisServicing: Sendable {
    func analyzeNextCommitment(idempotencyKey: UUID) async throws -> AnalysisResult
}

protocol ChatServicing: Sendable {
    func fetch(after cursor: String?) async throws -> ChatPage
    func reply(questionID: String, text: String, idempotencyKey: UUID) async throws -> ChatMessage
}

protocol CallServicing: Sendable {
    func placeTestCall(idempotencyKey: UUID) async throws -> CallReceipt
}

protocol AccountServicing: Sendable {
    func deleteAccount(idempotencyKey: UUID) async throws -> AccountDeletionReceipt
}

protocol OAuthCallbackAuthorizing: Sendable {
    func authorize(url: URL, expectedState: String) async throws -> URL
}

private struct CalendarExchangeRequest: Codable, Sendable {
    let code: String
    let state: String
}

private struct RefreshRequest: Codable, Sendable {
    let refreshToken: String
}

private struct ReplyRequest: Codable, Sendable {
    let questionID: String
    let text: String

    enum CodingKeys: String, CodingKey {
        case questionID = "questionId"
        case text
    }
}

struct AuthService: AuthServicing {
    private let api: APIRequesting
    private let sessionStore: SessionStoring
    private let callbackAuthorizer: OAuthCallbackAuthorizing?

    init(
        api: APIRequesting,
        sessionStore: SessionStoring,
        callbackAuthorizer: OAuthCallbackAuthorizing? = nil
    ) {
        self.api = api
        self.sessionStore = sessionStore
        self.callbackAuthorizer = callbackAuthorizer
    }

    func restoreSession() async throws -> Session? {
        try await sessionStore.load()
    }

    func connectCalendar() async throws -> Session {
        guard let callbackAuthorizer else {
            throw APIError.transport("OAuth callback authorizer is unavailable")
        }
        let start: SessionStart = try await api.send(
            .unauthenticatedMutation(path: "/session/calendar/start", method: .post),
            as: SessionStart.self,
            idempotencyKey: UUID()
        )
        let callback = try await callbackAuthorizer.authorize(
            url: start.authorizationURL,
            expectedState: start.state
        )
        guard
            let components = URLComponents(url: callback, resolvingAgainstBaseURL: false),
            let code = components.queryItems?.first(where: { $0.name == "code" })?.value,
            let state = components.queryItems?.first(where: { $0.name == "state" })?.value,
            state == start.state
        else {
            throw APIError.transport("OAuth callback state or code is invalid")
        }

        let body = try JSONEncoder.lifeManager.encode(CalendarExchangeRequest(code: code, state: state))
        let session: Session = try await api.send(
            .unauthenticatedMutation(path: "/session/exchange", method: .post, body: body),
            as: Session.self,
            idempotencyKey: UUID()
        )
        try await sessionStore.save(session)
        return session
    }

    func refresh(_ session: Session) async throws -> Session {
        let body = try JSONEncoder.lifeManager.encode(RefreshRequest(refreshToken: session.refreshToken))
        let rotated: Session = try await api.send(
            .unauthenticatedMutation(path: "/session/refresh", method: .post, body: body),
            as: Session.self,
            idempotencyKey: UUID()
        )
        try await sessionStore.save(rotated)
        return rotated
    }

    func signOut() async throws {
        do {
            try await api.sendVoid(
                .mutation(path: "/session", method: .delete),
                idempotencyKey: UUID()
            )
        } catch {
            try? await sessionStore.clear()
            throw error
        }
        try await sessionStore.clear()
    }
}

struct ProfileService: ProfileServicing {
    private let api: APIRequesting

    init(api: APIRequesting) {
        self.api = api
    }

    func fetch() async throws -> UserProfile {
        let bootstrap: Bootstrap = try await api.send(
            .get(path: "/bootstrap"),
            as: Bootstrap.self,
            idempotencyKey: nil
        )
        return UserProfile(bootstrap: bootstrap)
    }

    func update(_ draft: ProfileDraft, idempotencyKey: UUID) async throws -> UserProfile {
        let body = try JSONEncoder.lifeManager.encode(draft)
        return try await api.send(
            .mutation(path: "/profile", method: .patch, body: body),
            as: UserProfile.self,
            idempotencyKey: idempotencyKey
        )
    }
}

struct AnalysisService: AnalysisServicing {
    private let api: APIRequesting

    init(api: APIRequesting) {
        self.api = api
    }

    func analyzeNextCommitment(idempotencyKey: UUID) async throws -> AnalysisResult {
        try await api.send(
            .mutation(path: "/analysis", method: .post),
            as: AnalysisResult.self,
            idempotencyKey: idempotencyKey
        )
    }
}

struct ChatService: ChatServicing {
    private let api: APIRequesting

    init(api: APIRequesting) {
        self.api = api
    }

    func fetch(after cursor: String?) async throws -> ChatPage {
        let path: String
        if let cursor {
            let unreserved = CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~")
            let encodedCursor = cursor.addingPercentEncoding(withAllowedCharacters: unreserved) ?? cursor
            path = "/chat?cursor=\(encodedCursor)"
        } else {
            path = "/chat"
        }
        return try await api.send(
            .get(path: path),
            as: ChatPage.self,
            idempotencyKey: nil
        )
    }

    func reply(questionID: String, text: String, idempotencyKey: UUID) async throws -> ChatMessage {
        let body = try JSONEncoder.lifeManager.encode(ReplyRequest(questionID: questionID, text: text))
        let encodedQuestionID = questionID.addingPercentEncoding(
            withAllowedCharacters: CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~")
        ) ?? questionID
        return try await api.send(
            .mutation(
                path: "/questions/\(encodedQuestionID)/reply",
                method: .post,
                body: body
            ),
            as: ChatMessage.self,
            idempotencyKey: idempotencyKey
        )
    }
}

struct CallService: CallServicing {
    private let api: APIRequesting

    init(api: APIRequesting) {
        self.api = api
    }

    func placeTestCall(idempotencyKey: UUID) async throws -> CallReceipt {
        try await api.send(
            .mutation(path: "/calls/test", method: .post),
            as: CallReceipt.self,
            idempotencyKey: idempotencyKey
        )
    }
}

struct AccountService: AccountServicing {
    private let api: APIRequesting

    init(api: APIRequesting) {
        self.api = api
    }

    func deleteAccount(idempotencyKey: UUID) async throws -> AccountDeletionReceipt {
        try await api.send(
            .mutation(path: "/account", method: .delete),
            as: AccountDeletionReceipt.self,
            idempotencyKey: idempotencyKey
        )
    }
}
