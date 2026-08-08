import Foundation

enum ChatMessageType: String, Codable, Equatable, Sendable {
    case system
    case analysis
    case route
    case question
    case routeUnavailable = "route_unavailable"
    case callStatus = "call_status"
}

struct ChatPage: Codable, Equatable, Sendable {
    let messages: [ChatMessage]
    let nextCursor: String?
    let hasMore: Bool
}

struct ChatMessage: Codable, Equatable, Sendable, Identifiable {
    let id: String
    let cursor: String
    let createdAt: Date
    let locale: ProductLocale
    let type: ChatMessageType
    let text: String
    let userContent: CalendarUserContent
    let question: ChatQuestion?
    let route: Route?
    let actions: [ChatAction]
}

struct CalendarUserContent: Codable, Equatable, Sendable {
    let eventTitle: String?
    let eventLocation: String?
}

struct ChatQuestion: Codable, Equatable, Sendable, Identifiable {
    let id: String
    let prompt: String
}

struct ChatAction: Codable, Equatable, Sendable, Identifiable {
    let id: String
    let label: String
}

struct SemanticOutboxRecord: Codable, Equatable, Sendable, Identifiable {
    let sequence: Int
    let id: String
    let key: String
    let args: [String: JSONValue]
    let userContent: CalendarUserContent
}
