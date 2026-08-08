import Foundation

enum APNsEnvironment: String, Codable, Equatable, Sendable {
    case development
    case production

    // Keep the old source-level spelling working while using the backend's wire value.
    static var sandbox: Self { .development }
}

struct DeviceRegistrationRequest: Codable, Equatable, Sendable {
    let token: String
    let environment: APNsEnvironment
    let locale: ProductLocale
    let timezone: String
}

struct DeviceUnregistrationRequest: Codable, Equatable, Sendable {
    let token: String
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
    func unregister(token: Data, idempotencyKey: UUID) async throws
}

extension DeviceServicing {
    func unregister(token: Data, idempotencyKey: UUID) async throws {
        try await unregister(idempotencyKey: idempotencyKey)
    }
}

actor DeviceService: DeviceServicing {
    private let api: APIRequesting
    private var registeredToken: String?

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
        let token = try Self.hexToken(from: token)
        registeredToken = token
        let body = try JSONEncoder.lifeManager.encode(
            DeviceRegistrationRequest(
                token: token,
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
        guard let registeredToken else { throw APIError.invalidAPNsToken }
        try await unregister(token: registeredToken, idempotencyKey: idempotencyKey)
    }

    func unregister(token: Data, idempotencyKey: UUID) async throws {
        let token = try Self.hexToken(from: token)
        registeredToken = token
        try await unregister(token: token, idempotencyKey: idempotencyKey)
    }

    private func unregister(token: String, idempotencyKey: UUID) async throws {
        let body = try JSONEncoder.lifeManager.encode(DeviceUnregistrationRequest(token: token))
        try await api.sendVoid(
            .mutation(path: "/devices/apns", method: .delete, body: body),
            idempotencyKey: idempotencyKey
        )
        registeredToken = nil
    }

    private static func hexToken(from token: Data) throws -> String {
        guard token.count == 32 else { throw APIError.invalidAPNsToken }
        return token.map { String(format: "%02x", $0) }.joined()
    }
}
