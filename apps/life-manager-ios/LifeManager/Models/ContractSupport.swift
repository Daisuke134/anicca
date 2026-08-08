import Foundation

extension JSONDecoder {
    static var lifeManager: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }
}

extension JSONEncoder {
    static var lifeManager: JSONEncoder {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        return encoder
    }
}

extension Date {
    static func iso8601(_ value: String) -> Date {
        let fractionalFormatter = ISO8601DateFormatter()
        fractionalFormatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        guard let date = fractionalFormatter.date(from: value) ?? formatter.date(from: value) else {
            preconditionFailure("Invalid ISO-8601 fixture date: \(value)")
        }
        return date
    }
}

indirect enum JSONValue: Codable, Equatable, Sendable {
    case string(String)
    case number(Double)
    case bool(Bool)
    case object([String: JSONValue])
    case array([JSONValue])
    case null

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .null
        } else if let value = try? container.decode(Bool.self) {
            self = .bool(value)
        } else if let value = try? container.decode(Double.self) {
            self = .number(value)
        } else if let value = try? container.decode(String.self) {
            self = .string(value)
        } else if let value = try? container.decode([String: JSONValue].self) {
            self = .object(value)
        } else if let value = try? container.decode([JSONValue].self) {
            self = .array(value)
        } else {
            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Value is not valid JSON"
            )
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case let .string(value): try container.encode(value)
        case let .number(value): try container.encode(value)
        case let .bool(value): try container.encode(value)
        case let .object(value): try container.encode(value)
        case let .array(value): try container.encode(value)
        case .null: try container.encodeNil()
        }
    }
}

enum ProductLocale: String, Codable, Equatable, Sendable, CaseIterable {
    case en
    case ja
}

struct APNsDeviceReceipt: Codable, Equatable, Sendable {
    let deviceID: String
    let token: String
    let environment: APNsEnvironment
    let locale: ProductLocale
    let timezone: String
    let lastSeenAt: Date

    enum CodingKeys: String, CodingKey {
        case deviceID = "deviceId"
        case token
        case environment
        case locale
        case timezone
        case lastSeenAt
    }
}

struct DeviceDeletionReceipt: Codable, Equatable, Sendable {
    let deleted: Bool
}

struct SessionRevokedReceipt: Codable, Equatable, Sendable {
    let revoked: Bool
}

struct QuestionReplyReceipt: Codable, Equatable, Sendable {
    let status: String
    let questionID: String
    let analysis: AnalysisResult?

    enum CodingKeys: String, CodingKey {
        case status
        case questionID = "questionId"
        case analysis
    }
}

struct MobileErrorFixture: Codable, Equatable, Sendable {
    let error: MobileErrorDetails
}

struct MobileErrorDetails: Codable, Equatable, Sendable {
    let code: String
    let message: String
    let retryable: Bool
    let requestID: String

    enum CodingKeys: String, CodingKey {
        case code
        case message
        case retryable
        case requestID = "requestId"
    }
}

struct MobileContractManifest: Codable, Equatable, Sendable {
    let version: String
    let locale: ProductLocale
    let demo: MobileContractDemo
    let fixtures: [String]
    let session: MobileContractSessionRules
    let analysis: MobileContractAnalysisRules
    let semanticMessageKeys: [String]
    let headers: [String: String]
    let endpoints: [MobileContractEndpoint]
    let forbiddenSurfaces: [String]
}

struct MobileContractDemo: Codable, Equatable, Sendable {
    let calendarConnection: String
    let oauthUI: Bool
    let softPaywall: Bool

    enum CodingKeys: String, CodingKey {
        case calendarConnection
        case oauthUI = "oauthUi"
        case softPaywall
    }
}

struct MobileContractSessionRules: Codable, Equatable, Sendable {
    let uidSource: String
    let clientAuthorityFields: [String]
    let refreshRotation: String
    let replayRevokesFamily: Bool
}

struct MobileContractAnalysisRules: Codable, Equatable, Sendable {
    let manualRefreshPath: String
    let foregroundDetectionMaxSeconds: Int
    let originSource: String
    let destinationSource: String
    let calendarTravelBlock: String
}

struct MobileContractEndpoint: Codable, Equatable, Sendable {
    let method: String
    let path: String
    let requiresBearer: Bool
    let mutation: Bool
    let idempotencyKey: Bool
}
