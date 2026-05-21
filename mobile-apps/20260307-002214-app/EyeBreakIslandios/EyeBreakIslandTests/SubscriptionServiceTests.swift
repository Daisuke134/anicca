import XCTest
@testable import EyeBreakIsland

final class SubscriptionServiceTests: XCTestCase {

    func testInitialStatusIsFree() {
        let sut = SubscriptionService()
        XCTAssertEqual(sut.status, .free)
    }

    func testConfigureWithEmptyKeyDoesNotCrash() {
        let sut = SubscriptionService()
        sut.configure(apiKey: "")
        XCTAssertEqual(sut.status, .free)
    }

    func testProtocolConformance() {
        let sut = SubscriptionService()
        XCTAssertTrue(sut is SubscriptionServiceProtocol)
    }
}
