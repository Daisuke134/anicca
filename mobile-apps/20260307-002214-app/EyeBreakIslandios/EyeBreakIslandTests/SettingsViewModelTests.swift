import XCTest
import RevenueCat
@testable import EyeBreakIsland

@MainActor
final class SettingsViewModelTests: XCTestCase {
    private var sut: SettingsViewModel!
    private var mockSubscription: MockSubscriptionServiceForSettings!

    override func setUp() {
        super.setUp()
        mockSubscription = MockSubscriptionServiceForSettings()
        sut = SettingsViewModel(subscriptionService: mockSubscription)
    }

    override func tearDown() {
        sut = nil
        mockSubscription = nil
        super.tearDown()
    }

    // MARK: - Initial State

    func testInitialState() {
        XCTAssertFalse(sut.showPaywall)
        XCTAssertEqual(sut.subscriptionStatus, .free)
    }

    // MARK: - Pro Status

    func testIsProReturnsTrueWhenPro() {
        sut.subscriptionStatus = .pro
        XCTAssertTrue(sut.isPro)
    }

    func testIsProReturnsFalseWhenFree() {
        sut.subscriptionStatus = .free
        XCTAssertFalse(sut.isPro)
    }

    // MARK: - Show Paywall

    func testShowPaywallSetsTrue() {
        sut.openPaywall()
        XCTAssertTrue(sut.showPaywall)
    }

    // MARK: - Restore

    func testRestoreUpdatesStatus() async {
        mockSubscription.restoreResult = .pro
        await sut.restorePurchases()
        XCTAssertEqual(sut.subscriptionStatus, .pro)
    }

    func testRestoreKeepsFreeOnFailure() async {
        mockSubscription.restoreResult = .free
        await sut.restorePurchases()
        XCTAssertEqual(sut.subscriptionStatus, .free)
    }

    func testRestoreErrorShowsMessage() async {
        mockSubscription.shouldThrowOnRestore = true
        await sut.restorePurchases()
        XCTAssertNotNil(sut.errorMessage)
    }

    // MARK: - Check Status

    func testCheckStatusUpdates() async {
        mockSubscription.checkResult = .pro
        await sut.checkSubscriptionStatus()
        XCTAssertEqual(sut.subscriptionStatus, .pro)
    }

    // MARK: - Timer Interval

    func testTimerIntervalMinutesDefault() {
        XCTAssertEqual(sut.timerIntervalMinutes, Constants.defaultWorkIntervalMinutes)
    }

    // MARK: - Privacy Policy URL

    func testPrivacyPolicyURL() {
        XCTAssertNotNil(sut.privacyPolicyURL)
    }
}

// MARK: - Mocks

final class MockSubscriptionServiceForSettings: SubscriptionServiceProtocol {
    var status: SubscriptionStatus = .free
    var restoreResult: SubscriptionStatus = .free
    var checkResult: SubscriptionStatus = .free
    var shouldThrowOnRestore = false

    func configure(apiKey: String) {}
    func loadOfferings() async throws -> [RevenueCat.Package] { [] }
    func purchase(package: RevenueCat.Package) async throws -> Bool { true }

    func restorePurchases() async throws -> SubscriptionStatus {
        if shouldThrowOnRestore {
            throw NSError(domain: "test", code: -1)
        }
        status = restoreResult
        return restoreResult
    }

    func checkStatus() async -> SubscriptionStatus {
        status = checkResult
        return checkResult
    }
}
