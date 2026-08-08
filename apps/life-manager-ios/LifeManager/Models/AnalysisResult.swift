import Foundation

enum AnalysisStatus: String, Codable, Equatable, Sendable, CaseIterable {
    case routeReady = "route_ready"
    case needsInformation = "needs_information"
    case noUpcomingEvent = "no_upcoming_event"
    case routeUnavailable = "route_unavailable"
    case failed
}

struct AnalysisResult: Codable, Equatable, Sendable {
    let status: AnalysisStatus
    let analysisID: String
    let nextCursor: String
    let message: ChatMessage

    enum CodingKeys: String, CodingKey {
        case status
        case analysisID = "analysisId"
        case nextCursor
        case message
    }
}
