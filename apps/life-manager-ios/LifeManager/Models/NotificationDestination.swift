import Foundation

enum NotificationDestinationType: String, Codable, Equatable, Sendable {
    case chatMessage = "chat_message"
}

enum NotificationPayloadError: Error, Equatable, Sendable {
    case invalidObject
    case unsupportedKeys
    case unsupportedType
    case missingMessageID
    case emptyCursor
}

struct NotificationDestination: Codable, Equatable, Sendable {
    let type: NotificationDestinationType
    let messageID: String
    let cursor: String?

    init(
        type: NotificationDestinationType,
        messageID: String,
        cursor: String?
    ) throws {
        guard !messageID.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            throw NotificationPayloadError.missingMessageID
        }
        if cursor?.isEmpty == true {
            throw NotificationPayloadError.emptyCursor
        }
        self.type = type
        self.messageID = messageID
        self.cursor = cursor
    }

    init(data: Data) throws {
        guard
            let object = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        else {
            throw NotificationPayloadError.invalidObject
        }
        let allowedKeys: Set<String> = ["type", "messageId", "cursor"]
        guard Set(object.keys).isSubset(of: allowedKeys) else {
            throw NotificationPayloadError.unsupportedKeys
        }
        let decoded = try JSONDecoder.lifeManager.decode(Self.self, from: data)
        self = try Self(type: decoded.type, messageID: decoded.messageID, cursor: decoded.cursor)
    }

    init?(userInfo: [AnyHashable: Any]) {
        var payload: [String: Any] = [:]
        for (key, value) in userInfo {
            guard let key = key as? String else { return nil }
            if key != "aps" {
                payload[key] = value
            }
        }
        guard JSONSerialization.isValidJSONObject(payload), let data = try? JSONSerialization.data(withJSONObject: payload) else {
            return nil
        }
        guard let destination = try? Self(data: data) else { return nil }
        self = destination
    }

    private enum CodingKeys: String, CodingKey {
        case type
        case messageID = "messageId"
        case cursor
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let type = try container.decode(NotificationDestinationType.self, forKey: .type)
        let messageID = try container.decode(String.self, forKey: .messageID)
        let cursor = try container.decodeIfPresent(String.self, forKey: .cursor)
        try self.init(type: type, messageID: messageID, cursor: cursor)
    }
}
