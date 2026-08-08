import Foundation
import XCTest
@testable import LifeManager

final class CallAccountServiceTests: XCTestCase {
    func testCallServiceUsesAuthenticatedMutationAndPreservesReceipt() async throws {
        let receipt = CallReceipt(
            requestID: "call-request-1",
            status: .accepted,
            cooldownSeconds: 120,
            dailyRemaining: 2,
            message: "Call queued"
        )
        let api = ReceiptAPI(call: receipt, deletion: nil)
        let service = CallService(api: api)
        let key = UUID(uuidString: "11111111-2222-3333-4444-555555555555")!

        let result = try await service.placeTestCall(idempotencyKey: key)

        XCTAssertEqual(result, receipt)
        let endpoints = await api.endpoints()
        XCTAssertEqual(endpoints.map(\.path), ["/calls/test"])
        XCTAssertEqual(endpoints[0].method, .post)
        let callBody = try XCTUnwrap(endpoints[0].body)
        let callJSON = try XCTUnwrap(JSONSerialization.jsonObject(with: callBody) as? [String: Any])
        XCTAssertEqual(callJSON["confirmed"] as? Bool, true)
        XCTAssertEqual(callJSON.count, 1)
        let callKeys = await api.idempotencyKeys()
        XCTAssertEqual(callKeys, [key])
    }

    func testAccountServiceUsesAuthenticatedDeleteAndPreservesDeletionReceipt() async throws {
        let receipt = AccountDeletionReceipt(
            receiptID: "deletion-1",
            deletedAt: Date.iso8601("2026-08-10T08:20:00.000Z"),
            sessionsRevoked: true,
            providerConnectionsRevoked: true
        )
        let api = ReceiptAPI(call: nil, deletion: receipt)
        let service = AccountService(api: api)
        let key = UUID(uuidString: "66666666-7777-8888-9999-AAAAAAAAAAAA")!

        let result = try await service.deleteAccount(idempotencyKey: key)

        XCTAssertEqual(result, receipt)
        let endpoints = await api.endpoints()
        XCTAssertEqual(endpoints.map(\.path), ["/account"])
        XCTAssertEqual(endpoints[0].method, .delete)
        let deletionBody = try XCTUnwrap(endpoints[0].body)
        let deletionJSON = try XCTUnwrap(JSONSerialization.jsonObject(with: deletionBody) as? [String: Any])
        XCTAssertEqual(deletionJSON["confirmed"] as? Bool, true)
        XCTAssertEqual(deletionJSON.count, 1)
        let deletionKeys = await api.idempotencyKeys()
        XCTAssertEqual(deletionKeys, [key])
    }
}

private actor ReceiptAPI: APIRequesting {
    private let call: CallReceipt?
    private let deletion: AccountDeletionReceipt?
    private var recordedEndpoints: [APIEndpoint] = []
    private var recordedKeys: [UUID] = []

    init(call: CallReceipt?, deletion: AccountDeletionReceipt?) {
        self.call = call
        self.deletion = deletion
    }

    func send<Response: Decodable & Sendable>(
        _ endpoint: APIEndpoint,
        as responseType: Response.Type,
        idempotencyKey: UUID?
    ) async throws -> Response {
        recordedEndpoints.append(endpoint)
        if let idempotencyKey { recordedKeys.append(idempotencyKey) }
        if Response.self == CallReceipt.self, let call { return call as! Response }
        if Response.self == AccountDeletionReceipt.self, let deletion { return deletion as! Response }
        throw APIError.server(statusCode: 500)
    }

    func sendVoid(_ endpoint: APIEndpoint, idempotencyKey: UUID?) async throws {
        recordedEndpoints.append(endpoint)
        if let idempotencyKey { recordedKeys.append(idempotencyKey) }
    }

    func endpoints() -> [APIEndpoint] { recordedEndpoints }
    func idempotencyKeys() -> [UUID] { recordedKeys }
}
