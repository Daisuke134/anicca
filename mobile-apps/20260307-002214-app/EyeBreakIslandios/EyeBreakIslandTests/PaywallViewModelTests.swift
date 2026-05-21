import XCTest
@testable import EyeBreakIsland
import RevenueCat

@MainActor
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

    func testInitialStateIsIdle() {
        XCTAssertFalse(sut.isPurchasing)
        XCTAssertFalse(sut.isLoading)
        XCTAssertNil(sut.selectedPackage)
        XCTAssertTrue(sut.packages.isEmpty)
        XCTAssertNil(sut.errorMessage)
    }

    // MARK: - Load Offerings

    func testLoadOfferingsSuccessClearsError() async {
        mockService.shouldThrowOnLoad = false
        await sut.loadOfferings()
        XCTAssertFalse(sut.isLoading)
        XCTAssertNil(sut.errorMessage)
    }

    func testLoadOfferingsFailureSetsError() async {
        mockService.shouldThrowOnLoad = true
        await sut.loadOfferings()
        XCTAssertFalse(sut.isLoading)
        XCTAssertNotNil(sut.errorMessage)
    }

    func testLoadOfferingSetsLoadingDuringFetch() async {
        let expectation = XCTestExpectation(description: "loading set")
        mockService.loadDelay = 0.1
        Task {
            await sut.loadOfferings()
            expectation.fulfill()
        }
        try? await Task.sleep(nanoseconds: 50_000_000)
        XCTAssertTrue(sut.isLoading)
        await fulfillment(of: [expectation], timeout: 2)
    }

    // MARK: - Purchase

    func testPurchaseWithNoPackageDoesNothing() async {
        sut.selectedPackage = nil
        await sut.purchase()
        XCTAssertFalse(mockService.purchaseCalled)
    }

    func testPurchaseWithNoPackageKeepsState() async {
        await sut.purchase()
        XCTAssertFalse(sut.purchaseCompleted)
        XCTAssertFalse(sut.isPurchasing)
        XCTAssertNil(sut.errorMessage)
    }

    // MARK: - Restore

    func testRestoreSuccess() async {
        mockService.restoreResult = .pro
        await sut.restore()
        XCTAssertTrue(sut.purchaseCompleted)
    }

    func testRestoreFailureSetsError() async {
        mockService.shouldThrowOnRestore = true
        await sut.restore()
        XCTAssertNotNil(sut.errorMessage)
    }

    func testRestoreToFreeDoesNotComplete() async {
        mockService.restoreResult = .free
        await sut.restore()
        XCTAssertFalse(sut.purchaseCompleted)
    }
}

// MARK: - MockSubscriptionService

final class MockSubscriptionService: SubscriptionServiceProtocol {
    var status: SubscriptionStatus = .free
    var mockPackages: [Package] = []
    var shouldThrowOnLoad = false
    var shouldThrowOnPurchase = false
    var shouldThrowOnRestore = false
    var purchaseResult = true
    var restoreResult: SubscriptionStatus = .free
    var purchaseCalled = false
    var loadDelay: TimeInterval = 0

    func configure(apiKey: String) {}

    func loadOfferings() async throws -> [Package] {
        if loadDelay > 0 {
            try await Task.sleep(nanoseconds: UInt64(loadDelay * 1_000_000_000))
        }
        if shouldThrowOnLoad {
            throw NSError(domain: "test", code: -1, userInfo: [NSLocalizedDescriptionKey: "Load failed"])
        }
        return mockPackages
    }

    func purchase(package: Package) async throws -> Bool {
        purchaseCalled = true
        if shouldThrowOnPurchase {
            throw NSError(domain: "test", code: -1, userInfo: [NSLocalizedDescriptionKey: "Purchase failed"])
        }
        if purchaseResult { status = .pro }
        return purchaseResult
    }

    func restorePurchases() async throws -> SubscriptionStatus {
        if shouldThrowOnRestore {
            throw NSError(domain: "test", code: -1, userInfo: [NSLocalizedDescriptionKey: "Restore failed"])
        }
        status = restoreResult
        return restoreResult
    }

    func checkStatus() async -> SubscriptionStatus {
        return status
    }
}
