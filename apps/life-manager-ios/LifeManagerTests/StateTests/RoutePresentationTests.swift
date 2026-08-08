import Foundation
import XCTest
@testable import LifeManager

final class RoutePresentationTests: XCTestCase {
    func testCollapsedRouteCardProjectsActionableFieldsAndOrderedLegSummary() {
        let message = RouteFixtures.message(route: RouteFixtures.route(fare: RouteFare(currency: "JPY", amount: 220, medium: "IC")))

        let presentation = RoutePresentation.card(for: message)

        XCTAssertEqual(presentation?.eventTitle, "Tokyo Tower visit")
        XCTAssertEqual(presentation?.origin, "Shipathon Roppongi")
        XCTAssertEqual(presentation?.destination, "Tokyo Tower")
        XCTAssertEqual(presentation?.leaveAt, Date.iso8601("2026-08-10T08:35:00.000Z"))
        XCTAssertEqual(presentation?.arriveAt, Date.iso8601("2026-08-10T09:02:00.000Z"))
        XCTAssertEqual(presentation?.computedAt, Date.iso8601("2026-08-10T08:10:00.000Z"))
        XCTAssertEqual(presentation?.provider, "transit")
        XCTAssertTrue(presentation?.isUnofficialSource == true)
        XCTAssertEqual(presentation?.durationSeconds, 1620)
        XCTAssertEqual(presentation?.bufferSeconds, 180)
        XCTAssertEqual(presentation?.fare, RouteFare(currency: "JPY", amount: 220, medium: "IC"))
        XCTAssertEqual(
            presentation?.legSummary,
            ["Walk to Roppongi Station", "Take the Toei Oedo Line toward Daimon", "Walk to Tokyo Tower"]
        )
    }

    func testMissingFarePlatformAndGeometryRemainAbsentWithoutReplacementClaims() {
        let route = RouteFixtures.route(fare: nil, platform: nil, geometry: nil)
        let message = RouteFixtures.message(route: route)

        let card = RoutePresentation.card(for: message)
        let detail = RoutePresentation.detail(for: message)
        let renderedText = ([card?.legSummary.joined(separator: " "), detail?.steps.map(\.instruction).joined(separator: " ")]
            .compactMap { $0 }
            .joined(separator: " "))
            .lowercased()

        XCTAssertNil(card?.fare)
        XCTAssertNil(detail?.steps.first?.platform)
        XCTAssertFalse(renderedText.contains("fare unavailable"))
        XCTAssertFalse(renderedText.contains("platform unknown"))
        XCTAssertFalse(renderedText.contains("entrance"))
        XCTAssertFalse(renderedText.contains("exit"))
        XCTAssertFalse(renderedText.contains("best car"))
        XCTAssertFalse(renderedText.contains("crowding"))
    }

    func testRoutePresentationRequiresRouteMessageAndDoesNotInventRouteForStatusOnlyMessage() {
        let message = RouteFixtures.message(route: nil, type: .routeUnavailable)

        XCTAssertNil(RoutePresentation.card(for: message))
        XCTAssertNil(RoutePresentation.detail(for: message))
    }

    func testRouteViewsExposeSemanticTimingSourceFreshnessAndHonestyLabels() throws {
        let card = try Self.source(named: "RouteCardView.swift")
        let detail = try Self.source(named: "RouteDetailSheet.swift")

        for key in ["route.leave", "route.arrive", "route.bufferReason", "route.updated", "route.source", "route.unofficialWarning"] {
            XCTAssertTrue(card.contains(key), "card must render \(key)")
        }
        for key in ["route.leave", "route.arrive", "route.bufferReason", "route.updated", "route.source", "route.liveLocationOff", "route.unsupportedFieldsOmitted"] {
            XCTAssertTrue(detail.contains(key), "detail must render \(key)")
        }
    }

    private static func source(named name: String) throws -> String {
        let current = URL(fileURLWithPath: #filePath)
        let root = current
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        return try String(
            contentsOf: root.appendingPathComponent("LifeManager/Features/Chat").appendingPathComponent(name),
            encoding: .utf8
        )
    }
}

private enum RouteFixtures {
    static func message(
        route: Route?,
        type: ChatMessageType = .route
    ) -> ChatMessage {
        ChatMessage(
            id: "message-route",
            cursor: "cursor-route",
            createdAt: Date.iso8601("2026-08-10T08:10:00.000Z"),
            locale: .en,
            type: type,
            text: "Your next event is Tokyo Tower visit.",
            userContent: CalendarUserContent(eventTitle: "Tokyo Tower visit", eventLocation: "Tokyo Tower"),
            question: nil,
            route: route,
            actions: []
        )
    }

    static func route(
        fare: RouteFare? = RouteFare(currency: "JPY", amount: 220, medium: "IC"),
        platform: String? = "Platform 2",
        geometry: JSONValue? = nil
    ) -> Route {
        Route(
            status: .routeReady,
            provider: "transit",
            providerAttribution: "Transit API",
            computedAt: Date.iso8601("2026-08-10T08:10:00.000Z"),
            timezone: "America/Los_Angeles",
            eventID: "calendar-event-1",
            origin: RoutePlace(displayName: "Shipathon Roppongi", userContent: "Shipathon Roppongi"),
            destination: RoutePlace(displayName: "Tokyo Tower", userContent: "Tokyo Tower"),
            leaveAt: Date.iso8601("2026-08-10T08:35:00.000Z"),
            arriveAt: Date.iso8601("2026-08-10T09:02:00.000Z"),
            durationSeconds: 1620,
            bufferSeconds: 180,
            transferCount: 1,
            fare: fare,
            geometry: geometry,
            steps: [
                RouteStep(
                    sequence: 1,
                    mode: "walk",
                    instruction: "Walk to Roppongi Station",
                    from: "Shipathon Roppongi",
                    to: "Roppongi Station",
                    service: nil,
                    headsign: nil,
                    platform: nil,
                    departAt: Date.iso8601("2026-08-10T08:35:00.000Z"),
                    arriveAt: Date.iso8601("2026-08-10T08:42:00.000Z"),
                    durationSeconds: 420
                ),
                RouteStep(
                    sequence: 2,
                    mode: "train",
                    instruction: "Take the Toei Oedo Line toward Daimon",
                    from: "Roppongi Station",
                    to: "Akabanebashi Station",
                    service: "Toei Oedo Line",
                    headsign: "toward Daimon",
                    platform: platform,
                    departAt: Date.iso8601("2026-08-10T08:45:00.000Z"),
                    arriveAt: Date.iso8601("2026-08-10T08:56:00.000Z"),
                    durationSeconds: 660
                ),
                RouteStep(
                    sequence: 3,
                    mode: "walk",
                    instruction: "Walk to Tokyo Tower",
                    from: "Akabanebashi Station",
                    to: "Tokyo Tower",
                    service: nil,
                    headsign: nil,
                    platform: nil,
                    departAt: Date.iso8601("2026-08-10T08:56:00.000Z"),
                    arriveAt: Date.iso8601("2026-08-10T09:02:00.000Z"),
                    durationSeconds: 360
                )
            ]
        )
    }
}
