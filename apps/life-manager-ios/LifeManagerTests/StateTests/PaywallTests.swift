import XCTest
@testable import LifeManager

@MainActor
final class PaywallTests: XCTestCase {
    func testPaywallAppearsOnlyAfterFirstUsefulResolvedAnalysis() async {
        for status in AnalysisStatus.allCases {
            let viewModel = makeAppViewModel(status: status)
            await viewModel.restoreSession()
            await viewModel.retryAnalysis()

            viewModel.showSoftPaywall()

            if status == .routeReady {
                XCTAssertEqual(viewModel.route, .softPaywall)
            } else {
                XCTAssertEqual(viewModel.route, .chat, "paywall must wait for useful result: \(status.rawValue)")
            }
        }
    }

    func testContinueFreeAndCancelReturnToChatWithoutEntitlementGate() async {
        let viewModel = makeAppViewModel(status: .routeReady)
        await viewModel.restoreSession()
        await viewModel.retryAnalysis()

        viewModel.showSoftPaywall()
        viewModel.continueFree()
        XCTAssertEqual(viewModel.route, .chat)

        viewModel.showSoftPaywall()
        viewModel.cancelSoftPaywall()
        XCTAssertEqual(viewModel.route, .chat)
    }

    func testAutomaticPaywallUsesBootstrapOfferAndDurableOneShotReceiptAfterRouteCard() async throws {
        let receiptStore = TestSoftPaywallReceiptStore()
        let routeAnalysis = try JSONDecoder.lifeManager.decode(
            AnalysisResult.self,
            from: ContractFixtureLoader.data(named: "analysis-route_ready.json")
        )
        let first = makeAppViewModel(
            result: routeAnalysis,
            offerStatus: .available,
            receiptStore: receiptStore
        )

        await first.restoreSession()
        await first.retryAnalysis()
        XCTAssertEqual(first.route, .chat)
        await first.presentSoftPaywallIfEligible()
        XCTAssertEqual(first.route, .softPaywall)

        first.continueFree()
        await first.presentSoftPaywallIfEligible()
        XCTAssertEqual(first.route, .chat)

        let second = makeAppViewModel(
            result: routeAnalysis,
            offerStatus: .available,
            receiptStore: receiptStore
        )
        await second.restoreSession()
        await second.retryAnalysis()
        await second.presentSoftPaywallIfEligible()
        XCTAssertEqual(second.route, .chat)
    }

    func testAutomaticPaywallDoesNotPresentWhenBootstrapOfferIsUnavailable() async throws {
        let routeAnalysis = try JSONDecoder.lifeManager.decode(
            AnalysisResult.self,
            from: ContractFixtureLoader.data(named: "analysis-route_ready.json")
        )
        let viewModel = makeAppViewModel(result: routeAnalysis, offerStatus: .unavailable)

        await viewModel.restoreSession()
        await viewModel.retryAnalysis()
        await viewModel.presentSoftPaywallIfEligible()

        XCTAssertEqual(viewModel.route, .chat)
    }

    func testChatProjectionWiresAutomaticPaywallAfterInitialRouteCard() throws {
        let chatSource = try String(
            contentsOf: URL(fileURLWithPath: #filePath)
                .deletingLastPathComponent()
                .deletingLastPathComponent()
                .deletingLastPathComponent()
                .appendingPathComponent("LifeManager/Features/Chat/ChatView.swift"),
            encoding: .utf8
        )
        let rootSource = try String(
            contentsOf: URL(fileURLWithPath: #filePath)
                .deletingLastPathComponent()
                .deletingLastPathComponent()
                .deletingLastPathComponent()
                .appendingPathComponent("LifeManager/App/RootView.swift"),
            encoding: .utf8
        )

        XCTAssertTrue(chatSource.contains("await onUsefulRouteCard?()"))
        XCTAssertTrue(rootSource.contains("presentSoftPaywallIfEligible"))
    }

    func testPurchaseAndRestoreFailuresRemainVisibleAndDoNotClaimSuccess() async {
        let paywall = SoftPaywallViewModel(purchasing: FailingPaywallPurchasing())

        await paywall.upgrade()
        XCTAssertEqual(paywall.failure?.localizedMessageKey, "paywall.purchaseFailed")
        XCTAssertFalse(paywall.didPurchase)

        await paywall.restorePurchases()
        XCTAssertEqual(paywall.failure?.localizedMessageKey, "paywall.restoreFailed")
        XCTAssertFalse(paywall.didRestore)
    }

    private func makeAppViewModel(
        status: AnalysisStatus = .routeReady,
        result: AnalysisResult? = nil,
        offerStatus: OfferStatus = .available,
        receiptStore: SoftPaywallReceiptStoring = TestSoftPaywallReceiptStore()
    ) -> AppViewModel {
        AppViewModel(
            auth: PaywallAuthService(session: PaywallFixtures.session),
            profile: PaywallProfileService(profile: PaywallFixtures.profile(offerStatus: offerStatus)),
            analysis: PaywallAnalysisService(result: result ?? PaywallFixtures.analysis(status: status)),
            paywallReceiptStore: receiptStore
        )
    }
}

private struct FailingPaywallPurchasing: PaywallPurchasing {
    func purchase() async throws { throw APIError.transport("purchase unavailable") }
    func restore() async throws { throw APIError.transport("restore unavailable") }
}

private enum PaywallFixtures {
    static let session = Session(
        accessToken: "access",
        refreshToken: "refresh",
        tokenType: "Bearer",
        expiresAt: Date.iso8601("2026-08-10T08:20:00.000Z"),
        refreshExpiresAt: Date.iso8601("2026-09-09T08:05:00.000Z")
    )

    static func profile(offerStatus: OfferStatus) -> UserProfile {
        UserProfile(
            id: "user-1",
            name: "Alex",
            home: HomeAddress(status: .ready, display: "Home"),
            productLocale: .en,
            timezone: "America/Los_Angeles",
            offerStatus: offerStatus
        )
    }

    static func analysis(status: AnalysisStatus) -> AnalysisResult {
        AnalysisResult(
            status: status,
            analysisID: "analysis-\(status.rawValue)",
            nextCursor: "cursor-\(status.rawValue)",
            message: ChatMessage(
                id: "message-\(status.rawValue)",
                cursor: "cursor-\(status.rawValue)",
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

private actor PaywallAuthService: AuthServicing {
    let session: Session
    init(session: Session) { self.session = session }
    func restoreSession() async throws -> Session? { session }
    func connectCalendar() async throws -> Session { session }
    func refresh(_ session: Session) async throws -> Session { session }
    func signOut() async throws {}
}

private actor PaywallProfileService: ProfileServicing {
    let profile: UserProfile
    init(profile: UserProfile) { self.profile = profile }
    func fetch() async throws -> UserProfile { profile }
    func update(_ draft: ProfileDraft, idempotencyKey: UUID) async throws -> UserProfile { profile }
}

private actor PaywallAnalysisService: AnalysisServicing {
    let result: AnalysisResult
    init(result: AnalysisResult) { self.result = result }
    func analyzeNextCommitment(idempotencyKey: UUID) async throws -> AnalysisResult { result }
}

private actor TestSoftPaywallReceiptStore: SoftPaywallReceiptStoring {
    private var presentedUserIDs = Set<String>()

    func hasPresented(for userID: String) async -> Bool {
        presentedUserIDs.contains(userID)
    }

    func markPresented(for userID: String) async {
        presentedUserIDs.insert(userID)
    }
}
