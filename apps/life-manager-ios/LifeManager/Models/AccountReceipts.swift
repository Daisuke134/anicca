import Foundation

enum CallReceiptStatus: String, Codable, Equatable, Sendable {
    case placed
    case accepted
    case cooldown
    case dailyLimit = "daily_limit"
    case disabled
}

struct CallProviderReceipt: Codable, Equatable, Sendable {
    let ccid: String
}

struct CallReceipt: Codable, Equatable, Sendable {
    let requestID: String
    let status: CallReceiptStatus
    let cooldownSeconds: Int?
    let dailyRemaining: Int?
    let message: String?
    let attemptID: String?
    let callLanguage: ProductLocale?
    let providerReceipt: CallProviderReceipt?

    init(
        requestID: String,
        status: CallReceiptStatus,
        cooldownSeconds: Int?,
        dailyRemaining: Int?,
        message: String?,
        attemptID: String? = nil,
        callLanguage: ProductLocale? = nil,
        providerReceipt: CallProviderReceipt? = nil
    ) {
        self.requestID = requestID
        self.status = status
        self.cooldownSeconds = cooldownSeconds
        self.dailyRemaining = dailyRemaining
        self.message = message
        self.attemptID = attemptID
        self.callLanguage = callLanguage
        self.providerReceipt = providerReceipt
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let attemptID = try container.decodeIfPresent(String.self, forKey: .attemptID)
        self.init(
            requestID: try container.decodeIfPresent(String.self, forKey: .requestID) ?? attemptID ?? "",
            status: try container.decode(CallReceiptStatus.self, forKey: .status),
            cooldownSeconds: try container.decodeIfPresent(Int.self, forKey: .cooldownSeconds),
            dailyRemaining: try container.decodeIfPresent(Int.self, forKey: .dailyRemaining),
            message: try container.decodeIfPresent(String.self, forKey: .message),
            attemptID: attemptID,
            callLanguage: try container.decodeIfPresent(ProductLocale.self, forKey: .callLanguage),
            providerReceipt: try container.decodeIfPresent(CallProviderReceipt.self, forKey: .providerReceipt)
        )
    }

    enum CodingKeys: String, CodingKey {
        case requestID = "requestId"
        case status
        case cooldownSeconds
        case dailyRemaining
        case message
        case attemptID = "attemptId"
        case callLanguage
        case providerReceipt
    }
}

enum AccountDeletionStatus: String, Codable, Equatable, Sendable {
    case completed
}

struct ProviderCleanupReceipt: Codable, Equatable, Sendable {
    let provider: String
    let status: String
}

struct AccountDeletionReceipt: Codable, Equatable, Sendable {
    let receiptID: String
    let deletedAt: Date
    let sessionsRevoked: Bool
    let providerConnectionsRevoked: Bool
    let operationID: String
    let status: AccountDeletionStatus
    let completedAt: Date
    let providerCleanup: [ProviderCleanupReceipt]

    init(
        receiptID: String,
        deletedAt: Date,
        sessionsRevoked: Bool,
        providerConnectionsRevoked: Bool
    ) {
        self.receiptID = receiptID
        self.deletedAt = deletedAt
        self.sessionsRevoked = sessionsRevoked
        self.providerConnectionsRevoked = providerConnectionsRevoked
        self.operationID = receiptID
        self.status = .completed
        self.completedAt = deletedAt
        self.providerCleanup = providerConnectionsRevoked
            ? [ProviderCleanupReceipt(provider: "calendar", status: "disconnected")]
            : []
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let operationID = try container.decodeIfPresent(String.self, forKey: .operationID)
            ?? container.decode(String.self, forKey: .receiptID)
        let completedAt = try container.decodeIfPresent(Date.self, forKey: .completedAt)
            ?? container.decode(Date.self, forKey: .deletedAt)
        let cleanup = try container.decodeIfPresent([ProviderCleanupReceipt].self, forKey: .providerCleanup)
            ?? (container.decodeIfPresent(Bool.self, forKey: .providerConnectionsRevoked) == true
                ? [ProviderCleanupReceipt(provider: "calendar", status: "disconnected")]
                : [])
        self.receiptID = operationID
        self.deletedAt = completedAt
        self.sessionsRevoked = true
        self.providerConnectionsRevoked = !cleanup.isEmpty
        self.operationID = operationID
        self.status = try container.decodeIfPresent(AccountDeletionStatus.self, forKey: .status) ?? .completed
        self.completedAt = completedAt
        self.providerCleanup = cleanup
    }

    enum CodingKeys: String, CodingKey {
        case receiptID = "receiptId"
        case deletedAt
        case sessionsRevoked
        case providerConnectionsRevoked
        case operationID = "operationId"
        case status
        case completedAt
        case providerCleanup
    }
}
