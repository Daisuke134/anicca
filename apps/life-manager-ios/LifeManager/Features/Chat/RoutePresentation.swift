import Foundation

struct RouteCardPresentation: Equatable, Sendable {
    let eventTitle: String?
    let origin: String
    let destination: String
    let leaveAt: Date
    let arriveAt: Date
    let timezone: String
    let computedAt: Date
    let provider: String
    let durationSeconds: Int
    let bufferSeconds: Int?
    let fare: RouteFare?
    let legSummary: [String]
    let providerAttribution: String

    var isUnofficialSource: Bool {
        provider.caseInsensitiveCompare("transit") == .orderedSame
    }
}

struct RouteStepPresentation: Equatable, Sendable, Identifiable {
    let id: Int
    let instruction: String
    let from: String?
    let to: String?
    let service: String?
    let headsign: String?
    let platform: String?
    let departAt: Date?
    let arriveAt: Date?
    let durationSeconds: Int
}

struct RouteDetailPresentation: Equatable, Sendable {
    let eventTitle: String?
    let origin: String
    let destination: String
    let leaveAt: Date
    let arriveAt: Date
    let timezone: String
    let computedAt: Date
    let provider: String
    let bufferSeconds: Int?
    let providerAttribution: String
    let steps: [RouteStepPresentation]

    var isUnofficialSource: Bool {
        provider.caseInsensitiveCompare("transit") == .orderedSame
    }
}

enum RoutePresentation {
    static func card(for message: ChatMessage) -> RouteCardPresentation? {
        guard message.type == .route, let route = message.route, route.status == .routeReady else {
            return nil
        }

        return RouteCardPresentation(
            eventTitle: message.userContent.eventTitle,
            origin: route.origin.displayName,
            destination: route.destination.displayName,
            leaveAt: route.leaveAt,
            arriveAt: route.arriveAt,
            timezone: route.timezone,
            computedAt: route.computedAt,
            provider: route.provider,
            durationSeconds: route.durationSeconds,
            bufferSeconds: route.bufferSeconds,
            fare: route.fare,
            legSummary: route.steps.sorted { $0.sequence < $1.sequence }.map(\.instruction),
            providerAttribution: route.providerAttribution
        )
    }

    static func detail(for message: ChatMessage) -> RouteDetailPresentation? {
        guard let card = card(for: message), let route = message.route else {
            return nil
        }

        let steps = route.steps.sorted { $0.sequence < $1.sequence }.map { step in
            RouteStepPresentation(
                id: step.sequence,
                instruction: step.instruction,
                from: step.from,
                to: step.to,
                service: step.service,
                headsign: step.headsign,
                platform: step.platform,
                departAt: step.departAt,
                arriveAt: step.arriveAt,
                durationSeconds: step.durationSeconds
            )
        }

        return RouteDetailPresentation(
            eventTitle: card.eventTitle,
            origin: card.origin,
            destination: card.destination,
            leaveAt: card.leaveAt,
            arriveAt: card.arriveAt,
            timezone: route.timezone,
            computedAt: card.computedAt,
            provider: card.provider,
            bufferSeconds: card.bufferSeconds,
            providerAttribution: card.providerAttribution,
            steps: steps
        )
    }
}
