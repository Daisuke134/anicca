import Foundation
import XCTest
@testable import LifeManager

final class PushDeviceServiceTests: XCTestCase {
    func testAPNsTokenConversionRequires32BytesAndUsesLowercaseHex() async throws {
        let token = Data((0..<32).map(UInt8.init))
        let api = PushAPI()
        let service = DeviceService(api: api)

        try await service.register(
            token: token,
            environment: .sandbox,
            locale: .ja,
            timezone: "Asia/Tokyo",
            idempotencyKey: UUID(uuidString: "00000000-0000-0000-0000-000000000001")!
        )

        let requests = await api.requests()
        let request = try XCTUnwrap(requests.first)
        let body = try XCTUnwrap(request.endpoint.body)
        let registration = try JSONDecoder.lifeManager.decode(DeviceRegistrationRequest.self, from: body)
        XCTAssertEqual(registration.token, "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f")
        XCTAssertEqual(registration.environment, .sandbox)
        XCTAssertEqual(registration.locale, .ja)
        XCTAssertEqual(registration.timezone, "Asia/Tokyo")

        do {
            try await service.register(
                token: Data(repeating: 1, count: 31),
                environment: .sandbox,
                locale: .en,
                timezone: "UTC",
                idempotencyKey: UUID()
            )
            XCTFail("expected invalid APNs token length")
        } catch {
            XCTAssertEqual(error as? APIError, .invalidAPNsToken)
        }
    }

    func testDeviceRegistrationUsesAuthenticatedPutAndLogoutUsesDelete() async throws {
        let api = PushAPI()
        let service = DeviceService(api: api)
        let key = UUID(uuidString: "00000000-0000-0000-0000-000000000002")!

        try await service.register(
            token: Data(repeating: 7, count: 32),
            environment: .production,
            locale: .en,
            timezone: "America/Los_Angeles",
            idempotencyKey: key
        )
        try await service.unregister(idempotencyKey: key)

        let requests = await api.requests()
        XCTAssertEqual(requests.map(\.endpoint.path), ["/devices/apns", "/devices/apns"])
        XCTAssertEqual(requests.map(\.endpoint.method), [.put, .delete])
        XCTAssertTrue(requests.allSatisfy { $0.endpoint.requiresAuthentication })
        XCTAssertTrue(requests.allSatisfy { $0.endpoint.requiresIdempotencyKey })
        XCTAssertEqual(requests.map(\.idempotencyKey), [key, key])
    }

    func testNotificationDestinationAcceptsOnlyStableChatPointer() throws {
        let payload = try JSONSerialization.data(withJSONObject: [
            "type": "chat_message",
            "messageId": "message:v1:stable-1",
            "cursor": "cursor:v1:opaque-1"
        ])

        let destination = try NotificationDestination(data: payload)

        XCTAssertEqual(destination.type, .chatMessage)
        XCTAssertEqual(destination.messageID, "message:v1:stable-1")
        XCTAssertEqual(destination.cursor, "cursor:v1:opaque-1")
        XCTAssertNotNil(NotificationDestination(userInfo: [
            "aps": ["alert": ["title": "New message"]],
            "type": "chat_message",
            "messageId": "message:v1:stable-1",
            "cursor": "cursor:v1:opaque-1"
        ]))
        XCTAssertThrowsError(try NotificationDestination(data: JSONSerialization.data(withJSONObject: [
            "type": "chat_message",
            "messageId": "message:v1:stable-1",
            "route": ["origin": "secret"]
        ])))
        XCTAssertThrowsError(try NotificationDestination(data: JSONSerialization.data(withJSONObject: [
            "type": "chat_message",
            "messageId": "message:v1:stable-1",
            "accessToken": "secret"
        ])))
        XCTAssertThrowsError(try NotificationDestination(data: JSONSerialization.data(withJSONObject: [
            "type": "route",
            "messageId": "message:v1:stable-1"
        ])))
    }
}

private struct RecordedPushRequest: Sendable {
    let endpoint: APIEndpoint
    let idempotencyKey: UUID?
}

private actor PushAPI: APIRequesting {
    private var recorded: [RecordedPushRequest] = []

    func send<Response: Decodable & Sendable>(
        _ endpoint: APIEndpoint,
        as responseType: Response.Type,
        idempotencyKey: UUID?
    ) async throws -> Response {
        throw APIError.invalidResponse
    }

    func sendVoid(_ endpoint: APIEndpoint, idempotencyKey: UUID?) async throws {
        recorded.append(RecordedPushRequest(endpoint: endpoint, idempotencyKey: idempotencyKey))
    }

    func requests() -> [RecordedPushRequest] { recorded }
}
