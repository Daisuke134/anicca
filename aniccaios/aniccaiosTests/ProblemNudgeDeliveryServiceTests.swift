import XCTest
@testable import aniccaios

final class ProblemNudgeDeliveryServiceTests: XCTestCase {
    override func setUp() {
        super.setUp()
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [TestURLProtocol.self]
        NetworkSessionManager.testSession = URLSession(configuration: config)
    }

    override func tearDown() {
        NetworkSessionManager.testSession = nil
        TestURLProtocol.requestHandler = nil
        super.tearDown()
    }

    func testFetchDelivery_decodesPayload() async throws {
        let exp = expectation(description: "fetch")
        TestURLProtocol.requestHandler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertNotNil(request.value(forHTTPHeaderField: "device-id"))
            exp.fulfill()
            let resp = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
            let json = """
            {
              "id": "11111111-1111-1111-1111-111111111111",
              "problemType": "anxiety",
              "scheduledTime": "12:15",
              "deliveryDayLocal": "2026-02-13",
              "timezone": "UTC",
              "lang": "en",
              "variantIndex": 5,
              "title": "You're Safe",
              "hook": "Midday: Breathe",
              "detail": "Midday: One breath"
            }
            """
            return (resp, Data(json.utf8))
        }

        let d = try await ProblemNudgeDeliveryService.shared.fetchDelivery(id: "11111111-1111-1111-1111-111111111111")
        XCTAssertEqual(d.problemType, "anxiety")
        XCTAssertEqual(d.variantIndex, 5)
        XCTAssertEqual(d.hook, "Midday: Breathe")
        await fulfillment(of: [exp], timeout: 2.0)
    }
}

