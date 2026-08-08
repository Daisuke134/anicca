import Foundation

enum APNsEnvironment: String, Codable, Equatable, Sendable {
    case sandbox
    case production
}

struct DeviceRegistrationRequest: Codable, Equatable, Sendable {
    let token: String
    let environment: APNsEnvironment
    let locale: ProductLocale
    let timezone: String
}

protocol DeviceServicing: Sendable {
    func register(
        token: Data,
        environment: APNsEnvironment,
        locale: ProductLocale,
        timezone: String,
        idempotencyKey: UUID
    ) async throws
    func unregister(idempotencyKey: UUID) async throws
}

struct DeviceService: DeviceServicing {
    private let api: APIRequesting

    init(api: APIRequesting) {
        self.api = api
    }

    func register(
        token: Data,
        environment: APNsEnvironment,
        locale: ProductLocale,
        timezone: String,
        idempotencyKey: UUID
    ) async throws {
        guard token.count == 32 else { throw APIError.invalidAPNsToken }
        let body = try JSONEncoder.lifeManager.encode(
            DeviceRegistrationRequest(
                token: token.map { String(format: "%02x", $0) }.joined(),
                environment: environment,
                locale: locale,
                timezone: timezone
            )
        )
        try await api.sendVoid(
            .mutation(path: "/devices/apns", method: .put, body: body),
            idempotencyKey: idempotencyKey
        )
    }

    func unregister(idempotencyKey: UUID) async throws {
        try await api.sendVoid(
            .mutation(path: "/devices/apns", method: .delete),
            idempotencyKey: idempotencyKey
        )
    }
}
