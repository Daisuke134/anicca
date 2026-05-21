import XCTest
@testable import FrostDip
import RevenueCat

final class MockSubscriptionService: SubscriptionServiceProtocol {
    var isPremium: Bool = false
    var mockPackages: [Package] = []
    var shouldThrowOnFetch = false
    var shouldThrowOnPurchase = false
    var purchaseResult = true
    var restoreResult = true

    func configure(apiKey: String) {}

    func fetchOfferings() async throws -> [Package] {
        if shouldThrowOnFetch {
            throw NSError(domain: "MockError", code: -1, userInfo: [NSLocalizedDescriptionKey: "Fetch failed"])
        }
        return mockPackages
    }

    func purchase(package: Package) async throws -> Bool {
        if shouldThrowOnPurchase {
            throw NSError(domain: "MockError", code: 1, userInfo: [NSLocalizedDescriptionKey: "Cancelled"])
        }
        isPremium = purchaseResult
        return purchaseResult
    }

    func restorePurchases() async throws -> Bool {
        isPremium = restoreResult
        return restoreResult
    }

    func listenForUpdates(onChange: @escaping (Bool) -> Void) {}
}

final class PaywallViewModelTests: XCTestCase {
    private var sut: PaywallViewModel!
    private var mockService: MockSubscriptionService!

    override func setUp() {
        super.setUp()
        mockService = MockSubscriptionService()
        sut = PaywallViewModel(subscriptionService: mockService)
    }

    override func tearDown() {
        sut = nil
        mockService = nil
        super.tearDown()
    }

    // MARK: - Initial State

    func testInitialSelectedPlanIsAnnual() {
        XCTAssertEqual(sut.selectedPlanIndex, 2, "Annual (best value) should be pre-selected")
    }

    func testInitialStateIsIdle() {
        XCTAssertFalse(sut.isLoading)
        XCTAssertFalse(sut.isPurchased)
        XCTAssertNil(sut.errorMessage)
    }

    // MARK: - Loading Offerings

    func testLoadOfferingsShowsLoading() async {
        await sut.loadOfferings()
        XCTAssertFalse(sut.isLoading, "Loading should be false after completion")
    }

    func testLoadOfferingsErrorSetsMessage() async {
        mockService.shouldThrowOnFetch = true
        await sut.loadOfferings()
        XCTAssertNotNil(sut.errorMessage)
    }

    // MARK: - Purchase

    func testPurchaseWithNoPackagesSetsError() async {
        await sut.purchase()
        XCTAssertNotNil(sut.errorMessage)
        XCTAssertFalse(sut.isPurchased)
    }

    // MARK: - Restore

    func testRestoreSuccessSetsIsPurchased() async {
        mockService.restoreResult = true
        await sut.restore()
        XCTAssertTrue(sut.isPurchased)
    }

    func testRestoreNoActiveEntitlementShowsMessage() async {
        mockService.restoreResult = false
        await sut.restore()
        XCTAssertFalse(sut.isPurchased)
        XCTAssertNotNil(sut.errorMessage)
    }

    // MARK: - Plan Selection

    func testSelectPlanUpdatesIndex() {
        sut.selectPlan(at: 0)
        XCTAssertEqual(sut.selectedPlanIndex, 0)
        sut.selectPlan(at: 1)
        XCTAssertEqual(sut.selectedPlanIndex, 1)
    }
}
