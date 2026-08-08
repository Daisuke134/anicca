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
    private let sessionRelay: SessionPropagationRelay?
    private let retryStore: OperationRetryStoring

    init(
        api: APIRequesting,
        sessionStore: SessionStoring,
        callbackAuthorizer: OAuthCallbackAuthorizing? = nil,
        sessionRelay: SessionPropagationRelay? = nil,
        retryStore: OperationRetryStoring = UserDefaultsOperationRetryStore()
    ) {
        self.api = api
        self.sessionStore = sessionStore
        self.callbackAuthorizer = callbackAuthorizer
        self.sessionRelay = sessionRelay
        self.retryStore = retryStore
    }

    func restoreSession() async throws -> Session? {
        try await sessionStore.load()
    }

    func connectCalendar() async throws -> Session {
        guard let callbackAuthorizer else {
            throw APIError.transport("OAuth callback authorizer is unavailable")
        }
        let startKey = await retryStore.operationKey(for: .sessionStart)
        let start: SessionStart
        do {
            start = try await api.send(
                .unauthenticatedMutation(path: "/session/calendar/start", method: .post),
                as: SessionStart.self,
                idempotencyKey: startKey
            )
        } catch {
            await retryStore.clearIfDefinitive(.sessionStart, after: error)
            throw error
        }
        await retryStore.clear(.sessionStart)
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

        let proposedBody = try JSONEncoder.lifeManager.encode(CalendarExchangeRequest(code: code, state: state))
        let pendingExchange = await retryStore.pending(for: .sessionExchange)
        let body = pendingExchange?.input ?? proposedBody
        let exchangeKey: UUID
        if let pendingExchange {
            exchangeKey = pendingExchange.idempotencyKey
        } else {
            exchangeKey = await retryStore.operationKey(for: .sessionExchange, input: body)
        }
        let session: Session
        do {
            session = try await api.send(
                .unauthenticatedMutation(path: "/session/exchange", method: .post, body: body),
                as: Session.self,
                idempotencyKey: exchangeKey
            )
        } catch {
            await retryStore.clearIfDefinitive(.sessionExchange, after: error)
            throw error
        }
        await retryStore.clear(.sessionExchange)
        try await sessionStore.save(session)
        await sessionRelay?.propagate(session)
        return session
    }

    func refresh(_ session: Session) async throws -> Session {
        let proposedBody = try JSONEncoder.lifeManager.encode(RefreshRequest(refreshToken: session.refreshToken))
        let pendingRefresh = await retryStore.pending(for: .sessionRefresh)
        let body = pendingRefresh?.input ?? proposedBody
        let refreshKey: UUID
        if let pendingRefresh {
            refreshKey = pendingRefresh.idempotencyKey
        } else {
            refreshKey = await retryStore.operationKey(for: .sessionRefresh, input: body)
        }
        let rotated: Session
        do {
            rotated = try await api.send(
                .unauthenticatedMutation(path: "/session/refresh", method: .post, body: body),
                as: Session.self,
                idempotencyKey: refreshKey
            )
        } catch {
            await retryStore.clearIfDefinitive(.sessionRefresh, after: error)
            throw error
        }
        await retryStore.clear(.sessionRefresh)
        try await sessionStore.save(rotated)
        await sessionRelay?.propagate(rotated)
        return rotated
    }

    func signOut() async throws {
        let revokeKey = await retryStore.operationKey(for: .sessionRevoke)
        do {
            try await api.sendVoid(
                .mutation(path: "/session", method: .delete),
                idempotencyKey: revokeKey
            )
        } catch {
            await retryStore.clearIfDefinitive(.sessionRevoke, after: error)
            if !MutationRetryPolicy.shouldRetain(after: error) {
                try? await sessionStore.clear()
                await sessionRelay?.propagate(nil)
            }
            throw error
        }
        await retryStore.clear(.sessionRevoke)
        try await sessionStore.clear()
        await sessionRelay?.propagate(nil)
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
        var components = URLComponents()
        components.path = "/chat"
        if let cursor {
            components.queryItems = [URLQueryItem(name: "cursor", value: cursor)]
        }
        let path = components.string ?? "/chat"
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
