import Foundation
import XCTest
@testable import LifeManager

@MainActor
final class AppViewModelTests: XCTestCase {
    func testWelcomeCalendarProfilePhoneSkipAndAnalysisReachChat() async {
        let auth = StateAuthService(restored: nil, connected: StateFixtures.session)
        let profile = StateProfileService(profile: StateFixtures.profile)
        let analysis = StateAnalysisService(results: [StateFixtures.analysis(status: .routeReady)])
        let viewModel = AppViewModel(auth: auth, profile: profile, analysis: analysis)

        await viewModel.restoreSession()
        XCTAssertEqual(viewModel.route, .welcome)

        await viewModel.connectCalendar()
        XCTAssertEqual(viewModel.route, .profile)

        await viewModel.submitProfile(ProfileDraft(name: "Alex Morgan", home: "100 Market Street"))
        XCTAssertEqual(viewModel.route, .phone)

        await viewModel.skipPhone()
        XCTAssertEqual(viewModel.route, .chat)
        XCTAssertEqual(viewModel.lastAnalysisStatus, .routeReady)
        let requestCount = await analysis.requestCount()
        XCTAssertEqual(requestCount, 1)
    }

    func testSkippingPhonePersistsNullAndKeepsCallsDisabledBeforeAnalysis() async {
        let auth = StateAuthService(restored: nil, connected: StateFixtures.session)
        let profile = StateProfileService(profile: StateFixtures.profile)
        let analysis = StateAnalysisService(results: [StateFixtures.analysis(status: .routeReady)])
        let viewModel = AppViewModel(auth: auth, profile: profile, analysis: analysis)

        await viewModel.restoreSession()
        await viewModel.connectCalendar()
        await viewModel.submitProfile(ProfileDraft(name: "Alex", home: "Home", productLocale: .ja))
        await viewModel.skipPhone()

        let drafts = await profile.drafts()
        XCTAssertEqual(drafts.last?.phone, nil)
        XCTAssertEqual(drafts.last?.callsEnabled, false)
        XCTAssertEqual(drafts.last?.productLocale, .ja)
        XCTAssertEqual(viewModel.route, .chat)
    }

    func testAddingPhoneValidatesE164AndStillLeavesCallsDisabled() async {
        let auth = StateAuthService(restored: nil, connected: StateFixtures.session)
        let profile = StateProfileService(profile: StateFixtures.profile)
        let analysis = StateAnalysisService(results: [StateFixtures.analysis(status: .routeReady)])
        let viewModel = AppViewModel(auth: auth, profile: profile, analysis: analysis)

        await viewModel.restoreSession()
        await viewModel.connectCalendar()
        await viewModel.submitProfile(ProfileDraft(name: "Alex", home: "Home"))
        await viewModel.submitPhone("not-a-phone")

        XCTAssertEqual(viewModel.phoneValidationError, "settings.phoneInvalid")
        XCTAssertEqual(viewModel.route, .phone)
        let invalidDrafts = await profile.drafts()
        XCTAssertEqual(invalidDrafts.count, 1)

        await viewModel.submitPhone("+14155552671")

        let draft = await profile.drafts().last
        XCTAssertEqual(draft?.phone, "+14155552671")
        XCTAssertEqual(draft?.callsEnabled, false)
        XCTAssertEqual(viewModel.route, .chat)
    }

    func testAllTerminalAnalysisStatesEnterChat() async {
        for status in AnalysisStatus.allCases {
            let auth = StateAuthService(restored: StateFixtures.session, connected: StateFixtures.session)
            let profile = StateProfileService(profile: StateFixtures.profile)
            let analysis = StateAnalysisService(results: [StateFixtures.analysis(status: status)])
            let viewModel = AppViewModel(auth: auth, profile: profile, analysis: analysis)

            await viewModel.restoreSession()
            await viewModel.retryAnalysis()

            XCTAssertEqual(viewModel.route, .chat, "terminal status \(status.rawValue) must enter chat")
            XCTAssertEqual(viewModel.lastAnalysisStatus, status)
        }
    }

    func testBackendFailureBecomesPresentationErrorInsteadOfRawTransportError() async {
        let auth = StateAuthService(restored: nil, connected: nil)
        await auth.setRestoreError(APIError.server(statusCode: 503))
        let viewModel = AppViewModel(
            auth: auth,
            profile: StateProfileService(profile: StateFixtures.profile),
            analysis: StateAnalysisService(results: [])
        )

        await viewModel.restoreSession()

        guard case let .fatal(error) = viewModel.route else {
            return XCTFail("expected fatal presentation route")
        }
        XCTAssertEqual(error.backendErrorCode, "http_503")
        XCTAssertEqual(error.localizedMessageKey, "error.server")
        XCTAssertTrue(error.retryAllowed)
    }

    func testRestoreFetchesBootstrapAndChatProjectionBeforeChoosingChat() async {
        let auth = StateAuthService(restored: StateFixtures.session, connected: StateFixtures.session)
        let profile = StateProfileService(profile: StateFixtures.profile(analysisStatus: .routeReady, phone: .configured("+14155552671")))
        let chat = RestoreChatService(page: ChatPage(
            messages: [StateFixtures.analysis(status: .routeReady).message],
            nextCursor: nil,
            hasMore: false
        ))
        let viewModel = AppViewModel(
            auth: auth,
            profile: profile,
            analysis: StateAnalysisService(results: []),
            chat: chat
        )

        await viewModel.restoreSession()

        XCTAssertEqual(viewModel.route, .chat)
        XCTAssertEqual(viewModel.profile?.productLocale, .en)
        let profileFetchCount = await profile.fetchCount()
        let chatFetchCount = await chat.fetchCount()
        XCTAssertEqual(profileFetchCount, 1)
        XCTAssertEqual(chatFetchCount, 1)
        XCTAssertEqual(viewModel.chatViewModel?.messages.count, 1)
    }

    func testRestoreValidatesRequiredServerProfileBeforeChat() async {
        let auth = StateAuthService(restored: StateFixtures.session, connected: StateFixtures.session)
        let incomplete = UserProfile(
            id: "user:v1:incomplete",
            name: nil,
            home: HomeAddress(status: .missing, display: nil),
            productLocale: .en,
            timezone: "America/Los_Angeles",
            analysisStatus: .routeReady
        )
        let chat = RestoreChatService(page: ChatPage(messages: [], nextCursor: nil, hasMore: false))
        let viewModel = AppViewModel(
            auth: auth,
            profile: StateProfileService(profile: incomplete),
            analysis: StateAnalysisService(results: []),
            chat: chat
        )

        await viewModel.restoreSession()

        XCTAssertEqual(viewModel.route, .profile)
        let chatFetchCount = await chat.fetchCount()
        XCTAssertEqual(chatFetchCount, 0)
    }

    func testUsefulAnalysisReceiptIsRetainedAndSoftPaywallAppearsOnlyOnce() async {
        let result = StateFixtures.analysis(status: .routeReady)
        let viewModel = AppViewModel(
            auth: StateAuthService(restored: StateFixtures.session, connected: StateFixtures.session),
            profile: StateProfileService(profile: StateFixtures.profile),
            analysis: StateAnalysisService(results: [result])
        )

        await viewModel.restoreSession()
        await viewModel.retryAnalysis()
        XCTAssertEqual(viewModel.lastAnalysisReceipt, result)

        viewModel.showSoftPaywall()
        XCTAssertEqual(viewModel.route, .softPaywall)
        viewModel.continueFree()
        viewModel.showSoftPaywall()
        XCTAssertEqual(viewModel.route, .chat)
    }

    func testAmbiguousAnalysisReusesDurableOperationKeyUntilReceipt() async {
        let store = TestOperationRetryStore()
        let analysis = RetryingAnalysisService()
        let viewModel = AppViewModel(
            auth: StateAuthService(restored: StateFixtures.session, connected: StateFixtures.session),
            profile: StateProfileService(profile: StateFixtures.profile),
            analysis: analysis,
            retryStore: store
        )

        await viewModel.retryAnalysis()
        let pendingAfterFailure = await store.pending(for: .analysis)
        XCTAssertNotNil(pendingAfterFailure)

        await viewModel.retryAnalysis()
        let pendingAfterSuccess = await store.pending(for: .analysis)
        XCTAssertNil(pendingAfterSuccess)
        let keys = await analysis.keys()
        XCTAssertEqual(keys.count, 2)
        XCTAssertEqual(keys.first, keys.last)
        XCTAssertEqual(viewModel.route, .chat)
    }
}

private enum StateFixtures {
    static let session = Session(
        accessToken: "access-token",
        refreshToken: "refresh-token",
        tokenType: "Bearer",
        expiresAt: Date.iso8601("2026-08-10T08:20:00.000Z"),
        refreshExpiresAt: Date.iso8601("2026-09-09T08:05:00.000Z")
    )

    static let profile = profile()

    static func profile(
        analysisStatus: BootstrapAnalysisStatus = .idle,
        phone: PhoneSettings = .missing
    ) -> UserProfile {
        UserProfile(
        id: "user:v1:server-derived-8f3a",
        name: "Alex Morgan",
        home: HomeAddress(status: .ready, display: "100 Market Street"),
        productLocale: .en,
        timezone: "America/Los_Angeles",
        phone: phone,
        offerStatus: .available,
        analysisStatus: analysisStatus
        )
    }

    static func analysis(status: AnalysisStatus) -> AnalysisResult {
        AnalysisResult(
            status: status,
            analysisID: "analysis:v1:\(status.rawValue)",
            nextCursor: "cursor:v1:\(status.rawValue)",
            message: ChatMessage(
                id: "message:v1:\(status.rawValue)",
                cursor: "cursor:v1:\(status.rawValue)",
                createdAt: Date.iso8601("2026-08-10T08:10:00.000Z"),
                locale: .en,
                type: .system,
                text: status.rawValue,
                userContent: CalendarUserContent(eventTitle: nil, eventLocation: nil),
                question: nil,
                route: nil,
                actions: []
            )
        )
    }
}

private actor StateAuthService: AuthServicing {
    private var restored: Session?
    private let connected: Session?
    private var restoreError: Error?

    init(restored: Session?, connected: Session?) {
        self.restored = restored
        self.connected = connected
    }

    func setRestoreError(_ error: Error) {
        restoreError = error
    }

    func restoreSession() async throws -> Session? {
        if let restoreError { throw restoreError }
        return restored
    }

    func connectCalendar() async throws -> Session {
        guard let connected else { throw APIError.server(statusCode: 503) }
        restored = connected
        return connected
    }

    func refresh(_ session: Session) async throws -> Session { session }
    func signOut() async throws { restored = nil }
}

private actor StateProfileService: ProfileServicing {
    private let profile: UserProfile
    private var recordedDrafts: [ProfileDraft] = []
    private var fetches = 0

    init(profile: UserProfile) {
        self.profile = profile
    }

    func fetch() async throws -> UserProfile {
        fetches += 1
        return profile
    }
    func update(_ draft: ProfileDraft, idempotencyKey: UUID) async throws -> UserProfile {
        recordedDrafts.append(draft)
        return UserProfile(
            id: profile.id,
            name: draft.name,
            home: HomeAddress(status: draft.home == nil ? .missing : .ready, display: draft.home),
            productLocale: draft.productLocale,
            timezone: profile.timezone,
            phone: draft.phone.map(PhoneSettings.configured) ?? .missing,
            callsEnabled: draft.callsEnabled,
            callLanguage: draft.callLanguage,
            calendarStatus: profile.calendarStatus,
            offerStatus: profile.offerStatus
        )
    }

    func drafts() -> [ProfileDraft] { recordedDrafts }
    func fetchCount() -> Int { fetches }
}

private actor RestoreChatService: ChatServicing {
    private let page: ChatPage
    private var fetches = 0

    init(page: ChatPage) { self.page = page }

    func fetch(after cursor: String?) async throws -> ChatPage {
        XCTAssertNil(cursor)
        fetches += 1
        return page
    }

    func reply(questionID: String, text: String, idempotencyKey: UUID) async throws -> ChatMessage {
        fatalError("not used")
    }

    func fetchCount() -> Int { fetches }
}

private actor StateAnalysisService: AnalysisServicing {
    private var results: [AnalysisResult]
    private var requests = 0

    init(results: [AnalysisResult]) {
        self.results = results
    }

    func analyzeNextCommitment(idempotencyKey: UUID) async throws -> AnalysisResult {
        requests += 1
        guard !results.isEmpty else { throw APIError.server(statusCode: 500) }
        return results.removeFirst()
    }

    func requestCount() -> Int { requests }
}

private actor RetryingAnalysisService: AnalysisServicing {
    private var attempts = 0
    private var recordedKeys: [UUID] = []

    func analyzeNextCommitment(idempotencyKey: UUID) async throws -> AnalysisResult {
        attempts += 1
        recordedKeys.append(idempotencyKey)
        if attempts == 1 { throw APIError.transport("offline") }
        return StateFixtures.analysis(status: .routeReady)
    }

    func keys() -> [UUID] { recordedKeys }
}
