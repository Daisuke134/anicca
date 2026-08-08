import Foundation

enum RouteStatus: String, Codable, Equatable, Sendable {
    case routeReady = "route_ready"
}

struct Route: Codable, Equatable, Sendable {
    let status: RouteStatus
    let provider: String
    let providerAttribution: String
    let computedAt: Date
    let timezone: String
    let eventID: String
    let origin: RoutePlace
    let destination: RoutePlace
    let leaveAt: Date
    let arriveAt: Date
    let durationSeconds: Int
    let bufferSeconds: Int
    let transferCount: Int
    let fare: RouteFare?
    let geometry: JSONValue?
    let steps: [RouteStep]

    enum CodingKeys: String, CodingKey {
        case status
        case provider
        case providerAttribution
        case computedAt
        case timezone
        case eventID = "eventId"
        case origin
        case destination
        case leaveAt
        case arriveAt
        case durationSeconds
        case bufferSeconds
        case transferCount
        case fare
        case geometry
        case steps
    }
}

struct RoutePlace: Codable, Equatable, Sendable {
    let displayName: String
    let userContent: String
}

struct RouteFare: Codable, Equatable, Sendable {
    let currency: String
    let amount: Double
    let medium: String
}

struct RouteStep: Codable, Equatable, Sendable {
    let sequence: Int
    let mode: String
    let instruction: String
    let from: String
    let to: String
    let service: String?
    let headsign: String?
    let platform: String?
    let departAt: Date
    let arriveAt: Date
    let durationSeconds: Int
}
