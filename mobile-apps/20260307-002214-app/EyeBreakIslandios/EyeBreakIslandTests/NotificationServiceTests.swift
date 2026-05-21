import XCTest
@testable import EyeBreakIsland

final class NotificationServiceTests: XCTestCase {

    func testProtocolConformance() {
        let sut = NotificationService()
        XCTAssertTrue(sut is NotificationServiceProtocol)
    }

    func testCancelAllDoesNotCrash() {
        let sut = NotificationService()
        sut.cancelAll()
    }

    func testScheduleBreakNotificationDoesNotCrash() {
        let sut = NotificationService()
        sut.scheduleBreakNotification(after: 60)
    }
}
