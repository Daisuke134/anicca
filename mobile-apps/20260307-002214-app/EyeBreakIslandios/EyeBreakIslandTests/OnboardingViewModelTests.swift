import XCTest
@testable import EyeBreakIsland

@MainActor
final class OnboardingViewModelTests: XCTestCase {

    private var sut: OnboardingViewModel!

    override func setUp() {
        super.setUp()
        UserDefaults.standard.removeObject(forKey: Constants.hasCompletedOnboardingKey)
        sut = OnboardingViewModel(notificationService: MockNotificationService())
    }

    override func tearDown() {
        UserDefaults.standard.removeObject(forKey: Constants.hasCompletedOnboardingKey)
        sut = nil
        super.tearDown()
    }

    // MARK: - Initial State

    func testInitialPageIsZero() {
        XCTAssertEqual(sut.currentPage, 0)
    }

    func testTotalPagesIsFour() {
        XCTAssertEqual(sut.totalPages, 4)
    }

    // MARK: - Page Navigation

    func testNextPageIncrementsPage() {
        sut.nextPage()
        XCTAssertEqual(sut.currentPage, 1)
    }

    func testNextPageDoesNotExceedMaxPage() {
        sut.currentPage = 3
        sut.nextPage()
        XCTAssertEqual(sut.currentPage, 3)
    }

    func testCanGoNextIsTrueForPages0To2() {
        XCTAssertTrue(sut.canGoNext)
        sut.currentPage = 1
        XCTAssertTrue(sut.canGoNext)
        sut.currentPage = 2
        XCTAssertTrue(sut.canGoNext)
    }

    func testCanGoNextIsFalseForLastPage() {
        sut.currentPage = 3
        XCTAssertFalse(sut.canGoNext)
    }

    // MARK: - Notification Permission

    func testRequestNotificationPermissionCallsService() async {
        let mockService = sut.notificationService as! MockNotificationService
        mockService.permissionResult = true
        await sut.requestNotificationPermission()
        XCTAssertTrue(mockService.requestPermissionCalled)
    }

    func testRequestNotificationPermissionGrantedAdvancesPage() async {
        sut.currentPage = 2
        let mockService = sut.notificationService as! MockNotificationService
        mockService.permissionResult = true
        await sut.requestNotificationPermission()
        XCTAssertEqual(sut.currentPage, 3)
    }

    func testRequestNotificationPermissionDeniedStillAdvances() async {
        sut.currentPage = 2
        let mockService = sut.notificationService as! MockNotificationService
        mockService.permissionResult = false
        await sut.requestNotificationPermission()
        XCTAssertEqual(sut.currentPage, 3)
    }

    // MARK: - Completion

    func testCompleteOnboardingSetsFlag() {
        sut.completeOnboarding()
        XCTAssertTrue(UserDefaults.standard.bool(forKey: Constants.hasCompletedOnboardingKey))
    }

    func testIsOnboardingCompletedReturnsFalseInitially() {
        XCTAssertFalse(OnboardingViewModel.isOnboardingCompleted)
    }

    func testIsOnboardingCompletedReturnsTrueAfterCompletion() {
        sut.completeOnboarding()
        XCTAssertTrue(OnboardingViewModel.isOnboardingCompleted)
    }

    // MARK: - Onboarding Pages Data

    func testPagesHaveCorrectContent() {
        XCTAssertEqual(sut.pages.count, 3)
        XCTAssertEqual(sut.pages[0].iconName, "eye")
        XCTAssertEqual(sut.pages[1].iconName, "timer")
        XCTAssertEqual(sut.pages[2].iconName, "bell.fill")
    }
}

// MARK: - Mock

final class MockNotificationService: NotificationServiceProtocol {
    var requestPermissionCalled = false
    var permissionResult = true
    var scheduledInterval: TimeInterval?

    func requestPermission() async -> Bool {
        requestPermissionCalled = true
        return permissionResult
    }

    func scheduleBreakNotification(after interval: TimeInterval) {
        scheduledInterval = interval
    }

    func cancelAll() {}
}
