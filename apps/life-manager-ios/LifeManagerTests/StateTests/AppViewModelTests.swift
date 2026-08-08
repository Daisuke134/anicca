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
}

private enum StateFixtures {
    static let session = Session(
        accessToken: "access-token",
        refreshToken: "refresh-token",
        tokenType: "Bearer",
        expiresAt: Date.iso8601("2026-08-10T08:20:00.000Z"),
        refreshExpiresAt: Date.iso8601("2026-09-09T08:05:00.000Z")
    )

    static let profile = UserProfile(
        id: "user:v1:server-derived-8f3a",
        name: "Alex Morgan",
        home: HomeAddress(status: .ready, display: "100 Market Street"),
        productLocale: .en,
        timezone: "America/Los_Angeles"
    )

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

    init(profile: UserProfile) {
        self.profile = profile
    }

    func fetch() async throws -> UserProfile { profile }
    func update(_ draft: ProfileDraft, idempotencyKey: UUID) async throws -> UserProfile { profile }
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
