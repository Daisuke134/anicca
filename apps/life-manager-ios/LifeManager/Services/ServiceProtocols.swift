import Foundation

protocol AuthServicing: Sendable {
    func restoreSession() async throws -> Session?
    func connectCalendar() async throws -> Session
    func refresh(_ session: Session) async throws -> Session
    func signOut() async throws
}

protocol ProfileServicing: Sendable {
    func fetch() async throws -> UserProfile
    func update(_ draft: ProfileDraft, idempotencyKey: UUID) async throws -> ProfilePatchReceipt
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

private struct CalendarStartRequest: Encodable, Sendable {}

private struct CalendarExchangeRequest: Codable, Sendable {
    let state: String
    let status: String
    let connectedAccountId: String

    enum CodingKeys: String, CodingKey {
        case state
        case status
        case connectedAccountId
    }
}

private struct CalendarOAuthCallback: Sendable {
    let state: String
    let status: String
    let connectedAccountId: String

    static func parse(url: URL, expectedState: String) throws -> Self {
        guard
            !expectedState.isEmpty,
            expectedState.rangeOfCharacter(from: .whitespacesAndNewlines.union(.controlCharacters)) == nil,
            let components = URLComponents(url: url, resolvingAgainstBaseURL: false)
        else {
            throw APIError.transport("OAuth callback state is invalid")
        }

        let queryItems = components.queryItems ?? []
        func uniqueValue(named name: String) -> String? {
            let values = queryItems.filter { $0.name == name }.compactMap(\.value)
            guard values.count == 1 else { return nil }
            return values[0]
        }

        guard
            let state = uniqueValue(named: "state"),
            !state.isEmpty,
            state.rangeOfCharacter(from: .whitespacesAndNewlines.union(.controlCharacters)) == nil,
            state == expectedState,
            let status = uniqueValue(named: "status"),
            status == "success",
            let connectedAccountId = uniqueValue(named: "connected_account_id"),
            connectedAccountId.hasPrefix("ca_"),
            connectedAccountId.count > 3,
            connectedAccountId.rangeOfCharacter(
                from: CharacterSet(charactersIn: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-").inverted
            ) == nil
        else {
            throw APIError.transport("OAuth callback state, status, or connected account is invalid")
        }

        return Self(state: state, status: status, connectedAccountId: connectedAccountId)
    }
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
        let startBody = try JSONEncoder.lifeManager.encode(CalendarStartRequest())
        let startKey = await retryStore.operationKey(for: .sessionStart, input: startBody)
        let start: SessionStart
        do {
            start = try await api.send(
                .unauthenticatedMutation(path: "/session/calendar/start", method: .post, body: startBody),
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
        let callbackFacts = try CalendarOAuthCallback.parse(url: callback, expectedState: start.state)
        let proposedBody = try JSONEncoder.lifeManager.encode(
            CalendarExchangeRequest(
                state: callbackFacts.state,
                status: callbackFacts.status,
                connectedAccountId: callbackFacts.connectedAccountId
            )
        )
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

    func update(_ draft: ProfileDraft, idempotencyKey: UUID) async throws -> ProfilePatchReceipt {
        let body = try JSONEncoder.lifeManager.encode(draft)
        return try await api.send(
            .mutation(path: "/profile", method: .patch, body: body),
            as: ProfilePatchReceipt.self,
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
