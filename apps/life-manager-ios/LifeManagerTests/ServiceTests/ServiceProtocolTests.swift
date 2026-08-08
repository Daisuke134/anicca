import Foundation
import XCTest
@testable import LifeManager

final class ServiceProtocolTests: XCTestCase {
    func testProfileServiceProjectsBootstrapAndSendsAllowlistedDraft() async throws {
        let api = RecordingAPI()
        await api.setBootstrap(TestFixtures.bootstrap)
        await api.setProfilePatch(TestFixtures.profilePatch)
        let service = ProfileService(api: api)

        let profile = try await service.fetch()
        let patch = try await service.update(
            ProfileDraft(name: "Alex Morgan", home: "100 Market Street"),
            idempotencyKey: UUID(uuidString: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")!
        )

        XCTAssertEqual(profile.id, "user:v1:server-derived-8f3a")
        XCTAssertEqual(profile.home.display, nil)
        XCTAssertEqual(patch, TestFixtures.profilePatch)
        let endpoints = await api.endpoints()
        XCTAssertEqual(endpoints.map(\.path), ["/bootstrap", "/profile"])
        XCTAssertEqual(endpoints[1].method, .patch)
        let sentDraft = try JSONDecoder.lifeManager.decode(ProfileDraft.self, from: endpoints[1].body!)
        XCTAssertEqual(sentDraft, ProfileDraft(name: "Alex Morgan", home: "100 Market Street"))
    }

    func testAnalysisServiceCarriesCallerIdempotencyKey() async throws {
        let api = RecordingAPI()
        await api.setAnalysis(TestFixtures.analysis)
        let service = AnalysisService(api: api)
        let key = UUID(uuidString: "11111111-2222-3333-4444-555555555555")!

        let result = try await service.analyzeNextCommitment(idempotencyKey: key)

        XCTAssertEqual(result, TestFixtures.analysis)
        let analysisKeys = await api.idempotencyKeys()
        XCTAssertEqual(analysisKeys, [key])
    }

    func testChatServiceEncodesCursorAndQuestionReply() async throws {
        let api = RecordingAPI()
        await api.setChat(TestFixtures.chatPage)
        await api.setMessage(TestFixtures.chatPage.messages[0])
        let service = ChatService(api: api)
        let key = UUID(uuidString: "66666666-7777-8888-9999-AAAAAAAAAAAA")!

        let page = try await service.fetch(after: "cursor:v1/a")
        let reply = try await service.reply(questionID: "question:v1:8f3a", text: "yes", idempotencyKey: key)

        XCTAssertEqual(page, TestFixtures.chatPage)
        XCTAssertEqual(reply, TestFixtures.chatPage.messages[0])
        let endpoints = await api.endpoints()
        XCTAssertEqual(endpoints[0].path, "/chat?cursor=cursor:v1/a")
        XCTAssertEqual(endpoints[1].path, "/questions/question%3Av1%3A8f3a/reply")
        let replyJSON = try JSONSerialization.jsonObject(with: endpoints[1].body!) as! [String: String]
        XCTAssertEqual(replyJSON["questionId"], "question:v1:8f3a")
        XCTAssertEqual(replyJSON["text"], "yes")
        let replyKeys = await api.idempotencyKeys()
        XCTAssertEqual(replyKeys, [key])
    }

    func testAuthServiceRestoresRefreshesAndSignsOutThroughSessionStore() async throws {
        let original = TestFixtures.session
        let rotated = TestFixtures.rotatedSession
        let store = InMemorySessionStore(session: original)
        let api = RecordingAPI()
        await api.setSession(rotated)
        let service = AuthService(api: api, sessionStore: store)

        let restored = try await service.restoreSession()
        let refreshed = try await service.refresh(original)
        XCTAssertEqual(restored, original)
        XCTAssertEqual(refreshed, rotated)
        try await service.signOut()

        let currentSession = await store.currentSession()
        let voidEndpointCount = await api.voidEndpointCount()
        let lastEndpointPath = await api.endpoints().last?.path
        XCTAssertNil(currentSession)
        XCTAssertEqual(voidEndpointCount, 1)
        XCTAssertEqual(lastEndpointPath, "/session")
    }

    func testAuthServiceExchangesOnlyTheBackendValidatedOAuthState() async throws {
        let store = InMemorySessionStore(session: nil)
        let api = RecordingAPI()
        await api.setSessionStart(TestFixtures.sessionStart)
        await api.setSession(TestFixtures.rotatedSession)
        let callback = URL(string: "lifemanager://oauth/callback?code=one-use-code&state=state:v1:calendar-consent-8f3a")!
        let authorizer = TestOAuthCallbackAuthorizer(callback: callback)
        let service = AuthService(api: api, sessionStore: store, callbackAuthorizer: authorizer)

        let session = try await service.connectCalendar()

        XCTAssertEqual(session, TestFixtures.rotatedSession)
        let endpoints = await api.endpoints()
        let savedSession = await store.currentSession()
        XCTAssertEqual(endpoints.map(\.path), ["/session/calendar/start", "/session/exchange"])
        let exchangeBody = endpoints[1].body!
        let exchangeJSON = try JSONSerialization.jsonObject(with: exchangeBody) as! [String: String]
        XCTAssertEqual(exchangeJSON["code"], "one-use-code")
        XCTAssertEqual(exchangeJSON["state"], "state:v1:calendar-consent-8f3a")
        XCTAssertEqual(savedSession, TestFixtures.rotatedSession)
    }

    func testOAuthExchangePropagatesSessionToAuthenticatedAPI() async throws {
        let store = InMemorySessionStore(session: nil)
        let api = RecordingAPI()
        await api.setSessionStart(TestFixtures.sessionStart)
        await api.setSession(TestFixtures.rotatedSession)
        let sessionAPISink = SessionPropagationProbe()
        let authenticatedAPISink = SessionPropagationProbe()
        let relay = SessionPropagationRelay()
        relay.attach(sessionAPISink)
        relay.attach(authenticatedAPISink)
        let callback = URL(string: "lifemanager://oauth/callback?code=one-use-code&state=state:v1:calendar-consent-8f3a")!
        let service = AuthService(
            api: api,
            sessionStore: store,
            callbackAuthorizer: TestOAuthCallbackAuthorizer(callback: callback),
            sessionRelay: relay
        )

        _ = try await service.connectCalendar()

        let sessionAPISession = await sessionAPISink.session()
        let authenticatedAPISession = await authenticatedAPISink.session()
        XCTAssertEqual(sessionAPISession, TestFixtures.rotatedSession)
        XCTAssertEqual(authenticatedAPISession, TestFixtures.rotatedSession)
    }

    func testRefreshPropagatesRotatedSessionToSessionAndAuthenticatedAPIs() async throws {
        let store = InMemorySessionStore(session: TestFixtures.session)
        let api = RecordingAPI()
        let sessionAPISink = SessionPropagationProbe()
        let authenticatedAPISink = SessionPropagationProbe()
        let relay = SessionPropagationRelay()
        relay.attach(sessionAPISink)
        relay.attach(authenticatedAPISink)
        let service = AuthService(
            api: api,
            sessionStore: store,
            sessionRelay: relay
        )
        await api.setSession(TestFixtures.rotatedSession)

        let refreshed = try await service.refresh(TestFixtures.session)

        XCTAssertEqual(refreshed, TestFixtures.rotatedSession)
        let sessionAPISession = await sessionAPISink.session()
        let authenticatedAPISession = await authenticatedAPISink.session()
        XCTAssertEqual(sessionAPISession, TestFixtures.rotatedSession)
        XCTAssertEqual(authenticatedAPISession, TestFixtures.rotatedSession)
    }

    func testOAuthExchangeReusesDurableKeyAndBodyAfterAmbiguousFailure() async throws {
        let store = TestOperationRetryStore()
        let api = RetryingAuthMutationAPI(mode: .exchange)
        let callback = URL(string: "lifemanager://oauth/callback?code=one-use-code&state=state:v1:calendar-consent-8f3a")!
        let service = AuthService(
            api: api,
            sessionStore: InMemorySessionStore(session: nil),
            callbackAuthorizer: TestOAuthCallbackAuthorizer(callback: callback),
            retryStore: store
        )

        do {
            _ = try await service.connectCalendar()
            XCTFail("expected an ambiguous exchange failure")
        } catch let error as APIError {
            XCTAssertEqual(error, .transport("offline"))
        }
        let pendingValue = await store.pending(for: .sessionExchange)
        let pending = try XCTUnwrap(pendingValue)

        _ = try await service.connectCalendar()

        let exchangeRequests = await api.requests(path: "/session/exchange")
        XCTAssertEqual(exchangeRequests.count, 2)
        XCTAssertEqual(exchangeRequests[0].idempotencyKey, pending.idempotencyKey)
        XCTAssertEqual(exchangeRequests[1].idempotencyKey, pending.idempotencyKey)
        XCTAssertEqual(exchangeRequests[0].body, pending.input)
        XCTAssertEqual(exchangeRequests[1].body, pending.input)
        let exchangePendingAfterSuccess = await store.pending(for: .sessionExchange)
        XCTAssertNil(exchangePendingAfterSuccess)
    }

    func testSessionRefreshReusesDurableKeyAndBodyAfterAmbiguousFailure() async throws {
        let store = TestOperationRetryStore()
        let api = RetryingAuthMutationAPI(mode: .refresh)
        let service = AuthService(
            api: api,
            sessionStore: InMemorySessionStore(session: TestFixtures.session),
            retryStore: store
        )

        do {
            _ = try await service.refresh(TestFixtures.session)
            XCTFail("expected an ambiguous refresh failure")
        } catch let error as APIError {
            XCTAssertEqual(error, .transport("offline"))
        }
        let pendingValue = await store.pending(for: .sessionRefresh)
        let pending = try XCTUnwrap(pendingValue)

        _ = try await service.refresh(TestFixtures.session)

        let refreshRequests = await api.requests(path: "/session/refresh")
        XCTAssertEqual(refreshRequests.count, 2)
        XCTAssertEqual(refreshRequests[0].idempotencyKey, pending.idempotencyKey)
        XCTAssertEqual(refreshRequests[1].idempotencyKey, pending.idempotencyKey)
        XCTAssertEqual(refreshRequests[0].body, pending.input)
        XCTAssertEqual(refreshRequests[1].body, pending.input)
        let refreshPendingAfterSuccess = await store.pending(for: .sessionRefresh)
        XCTAssertNil(refreshPendingAfterSuccess)
    }

    func testSessionRevokeReusesDurableKeyAfterAmbiguousFailure() async throws {
        let store = TestOperationRetryStore()
        let api = RetryingAuthMutationAPI(mode: .revoke)
        let service = AuthService(
            api: api,
            sessionStore: InMemorySessionStore(session: TestFixtures.session),
            retryStore: store
        )

        do {
            try await service.signOut()
            XCTFail("expected an ambiguous revoke failure")
        } catch let error as APIError {
            XCTAssertEqual(error, .transport("offline"))
        }
        let pendingValue = await store.pending(for: .sessionRevoke)
        let pending = try XCTUnwrap(pendingValue)

        try await service.signOut()

        let revokeRequests = await api.requests(path: "/session")
        XCTAssertEqual(revokeRequests.count, 2)
        XCTAssertEqual(revokeRequests[0].idempotencyKey, pending.idempotencyKey)
        XCTAssertEqual(revokeRequests[1].idempotencyKey, pending.idempotencyKey)
        let revokePendingAfterSuccess = await store.pending(for: .sessionRevoke)
        XCTAssertNil(revokePendingAfterSuccess)
    }

    func testMutationRetryPolicyRetainsAmbiguousFailuresOnly() {
        XCTAssertTrue(MutationRetryPolicy.shouldRetain(after: APIError.transport("offline")))
        XCTAssertTrue(MutationRetryPolicy.shouldRetain(after: APIError.server(statusCode: 409)))
        XCTAssertTrue(MutationRetryPolicy.shouldRetain(after: APIError.server(statusCode: 500)))
        XCTAssertFalse(MutationRetryPolicy.shouldRetain(after: APIError.server(statusCode: 400)))
        XCTAssertFalse(MutationRetryPolicy.shouldRetain(after: APIError.server(statusCode: 422)))
    }
}

private enum TestFixtures {
    static let bootstrap = Bootstrap(
        user: BootstrapUser(
            id: "user:v1:server-derived-8f3a",
            name: nil,
            productLocale: .en,
            timezone: "America/Los_Angeles",
            home: HomeAddress(status: .missing, display: nil)
        ),
        calendar: CalendarConnection(status: .connected),
        analysis: BootstrapAnalysis(status: .idle)
    )

    static let profile = UserProfile(
        id: "user:v1:server-derived-8f3a",
        name: "Alex Morgan",
        home: HomeAddress(status: .ready, display: "100 Market Street"),
        productLocale: .en,
        timezone: "America/Los_Angeles"
    )

    static let profilePatch = ProfilePatchReceipt(
        name: "Alex Morgan",
        home: "100 Market Street",
        productLocale: .en
    )

    static let analysis = AnalysisResult(
        status: .noUpcomingEvent,
        analysisID: "analysis:v1:no-event-8f3a",
        nextCursor: "cursor:v1:no-event",
        message: ChatMessage(
            id: "message:v1:no-event",
            cursor: "cursor:v1:no-event",
            createdAt: Date.iso8601("2026-08-10T08:10:00.000Z"),
            locale: .en,
            type: .system,
            text: "No upcoming event.",
            userContent: CalendarUserContent(eventTitle: nil, eventLocation: nil),
            question: nil,
            route: nil,
            actions: []
        )
    )

    static let chatPage = ChatPage(messages: [analysis.message], nextCursor: nil, hasMore: false)
    static let session = Session(
        accessToken: "old-access",
        refreshToken: "old-refresh",
        tokenType: "Bearer",
        expiresAt: Date.iso8601("2026-08-10T08:20:00.000Z"),
        refreshExpiresAt: Date.iso8601("2026-09-09T08:05:00.000Z")
    )
    static let rotatedSession = Session(
        accessToken: "rotated-access",
        refreshToken: "rotated-refresh",
        tokenType: "Bearer",
        expiresAt: Date.iso8601("2026-08-10T09:20:00.000Z"),
        refreshExpiresAt: Date.iso8601("2026-09-09T09:05:00.000Z")
    )
    static let sessionStart = SessionStart(
        state: "state:v1:calendar-consent-8f3a",
        authorizationURL: URL(string: "https://accounts.google.com/o/oauth2/v2/auth")!,
        expiresAt: Date.iso8601("2026-08-10T08:05:00.000Z")
    )
}

private actor RecordingAPI: APIRequesting {
    private var bootstrap: Bootstrap?
    private var profilePatch: ProfilePatchReceipt?
    private var sessionStart: SessionStart?
    private var analysis: AnalysisResult?
    private var chat: ChatPage?
    private var message: ChatMessage?
    private var session: Session?
    private var recordedEndpoints: [APIEndpoint] = []
    private var recordedKeys: [UUID] = []
    private var voidCalls = 0

    func setBootstrap(_ value: Bootstrap) { bootstrap = value }
    func setProfilePatch(_ value: ProfilePatchReceipt) { profilePatch = value }
    func setSessionStart(_ value: SessionStart) { sessionStart = value }
    func setAnalysis(_ value: AnalysisResult) { analysis = value }
    func setChat(_ value: ChatPage) { chat = value }
    func setMessage(_ value: ChatMessage) { message = value }
    func setSession(_ value: Session) { session = value }

    func send<Response: Decodable & Sendable>(
        _ endpoint: APIEndpoint,
        as responseType: Response.Type,
        idempotencyKey: UUID?
    ) async throws -> Response {
        recordedEndpoints.append(endpoint)
        if let idempotencyKey { recordedKeys.append(idempotencyKey) }
        if Response.self == Bootstrap.self, let value = bootstrap { return value as! Response }
        if Response.self == ProfilePatchReceipt.self, let value = profilePatch { return value as! Response }
        if Response.self == SessionStart.self, let value = sessionStart { return value as! Response }
        if Response.self == AnalysisResult.self, let value = analysis { return value as! Response }
        if Response.self == ChatPage.self, let value = chat { return value as! Response }
        if Response.self == ChatMessage.self, let value = message { return value as! Response }
        if Response.self == Session.self, let value = session { return value as! Response }
        throw APIError.server(statusCode: 500)
    }

    func sendVoid(_ endpoint: APIEndpoint, idempotencyKey: UUID?) async throws {
        recordedEndpoints.append(endpoint)
        if let idempotencyKey { recordedKeys.append(idempotencyKey) }
        voidCalls += 1
    }

    func endpoints() -> [APIEndpoint] { recordedEndpoints }
    func idempotencyKeys() -> [UUID] { recordedKeys }
    func voidEndpointCount() -> Int { voidCalls }
}

private struct TestOAuthCallbackAuthorizer: OAuthCallbackAuthorizing, Sendable {
    let callback: URL

    func authorize(url: URL, expectedState: String) async throws -> URL {
        callback
    }
}

private actor InMemorySessionStore: SessionStoring {
    private var session: Session?

    init(session: Session?) {
        self.session = session
    }

    func load() async throws -> Session? { session }
    func save(_ session: Session) async throws { self.session = session }
    func clear() async throws { session = nil }
    func currentSession() -> Session? { session }
}

private actor SessionPropagationProbe: SessionPropagating {
    private var current: Session?

    func setSession(_ session: Session?) async {
        current = session
    }

    func session() -> Session? { current }
}

private enum AuthRetryMutationMode: Sendable {
    case exchange
    case refresh
    case revoke
}

private struct RecordedAuthMutation: Sendable {
    let endpoint: APIEndpoint
    let idempotencyKey: UUID?
    let body: Data?
}

private actor RetryingAuthMutationAPI: APIRequesting {
    private let mode: AuthRetryMutationMode
    private var shouldFail = true
    private var recorded: [RecordedAuthMutation] = []

    init(mode: AuthRetryMutationMode) {
        self.mode = mode
    }

    func send<Response: Decodable & Sendable>(
        _ endpoint: APIEndpoint,
        as responseType: Response.Type,
        idempotencyKey: UUID?
    ) async throws -> Response {
        recorded.append(RecordedAuthMutation(endpoint: endpoint, idempotencyKey: idempotencyKey, body: endpoint.body))
        if shouldFail && isTarget(endpoint) {
            shouldFail = false
            throw APIError.transport("offline")
        }
        if Response.self == SessionStart.self {
            return ServiceProtocolTests.sessionStartFixture as! Response
        }
        if Response.self == Session.self {
            return ServiceProtocolTests.rotatedSessionFixture as! Response
        }
        throw APIError.server(statusCode: 500)
    }

    func sendVoid(_ endpoint: APIEndpoint, idempotencyKey: UUID?) async throws {
        recorded.append(RecordedAuthMutation(endpoint: endpoint, idempotencyKey: idempotencyKey, body: endpoint.body))
        if shouldFail && isTarget(endpoint) {
            shouldFail = false
            throw APIError.transport("offline")
        }
    }

    func requests(path: String) -> [RecordedAuthMutation] {
        recorded.filter { $0.endpoint.path == path }
    }

    private func isTarget(_ endpoint: APIEndpoint) -> Bool {
        switch (mode, endpoint.path) {
        case (.exchange, "/session/exchange"), (.refresh, "/session/refresh"), (.revoke, "/session"):
            return true
        default:
            return false
        }
    }
}

private extension ServiceProtocolTests {
    static var sessionStartFixture: SessionStart {
        SessionStart(
            state: "state:v1:calendar-consent-8f3a",
            authorizationURL: URL(string: "https://accounts.google.com/o/oauth2/v2/auth")!,
            expiresAt: Date.iso8601("2026-08-10T08:05:00.000Z")
        )
    }

    static var rotatedSessionFixture: Session {
        Session(
            accessToken: "rotated-access",
            refreshToken: "rotated-refresh",
            tokenType: "Bearer",
            expiresAt: Date.iso8601("2026-08-10T09:20:00.000Z"),
            refreshExpiresAt: Date.iso8601("2026-09-09T09:05:00.000Z")
        )
    }
}
