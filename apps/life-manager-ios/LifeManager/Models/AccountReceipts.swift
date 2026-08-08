import Foundation

enum CallReceiptStatus: String, Codable, Equatable, Sendable {
    case accepted
    case cooldown
    case dailyLimit = "daily_limit"
    case disabled
}

struct CallReceipt: Codable, Equatable, Sendable {
    let requestID: String
    let status: CallReceiptStatus
    let cooldownSeconds: Int?
    let dailyRemaining: Int?
    let message: String?

    init(
        requestID: String,
        status: CallReceiptStatus,
        cooldownSeconds: Int?,
        dailyRemaining: Int?,
        message: String?
    ) {
        self.requestID = requestID
        self.status = status
        self.cooldownSeconds = cooldownSeconds
        self.dailyRemaining = dailyRemaining
        self.message = message
    }

    enum CodingKeys: String, CodingKey {
        case requestID = "requestId"
        case status
        case cooldownSeconds
        case dailyRemaining
        case message
    }
}

struct AccountDeletionReceipt: Codable, Equatable, Sendable {
    let receiptID: String
    let deletedAt: Date
    let sessionsRevoked: Bool
    let providerConnectionsRevoked: Bool

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
    }

    enum CodingKeys: String, CodingKey {
        case receiptID = "receiptId"
        case deletedAt
        case sessionsRevoked
        case providerConnectionsRevoked
    }
}
