import Foundation
import XCTest
@testable import LifeManager

final class ContractFixtureDecodingTests: XCTestCase {
    private let decoder = JSONDecoder.lifeManager

    func testBootstrapFixtureDecodesWithoutClientAuthority() throws {
        let bootstrap = try decoder.decode(
            Bootstrap.self,
            from: ContractFixtureLoader.data(named: "bootstrap.json")
        )

        XCTAssertEqual(bootstrap.product.locale, .en)
        XCTAssertEqual(bootstrap.user.id, "user:v1:server-derived-8f3a")
        XCTAssertNil(bootstrap.user.name)
        XCTAssertEqual(bootstrap.user.home.status, .missing)
        XCTAssertNil(bootstrap.user.home.display)
        XCTAssertEqual(bootstrap.calendar.status, .connected)
        XCTAssertEqual(bootstrap.analysis.status, .idle)
    }

    func testEveryTerminalAnalysisFixtureDecodesItsTypedStatus() throws {
        let fixtures: [(String, AnalysisStatus)] = [
            ("analysis-route_ready.json", .routeReady),
            ("analysis-needs_information.json", .needsInformation),
            ("analysis-no_upcoming_event.json", .noUpcomingEvent),
            ("analysis-route_unavailable.json", .routeUnavailable),
            ("analysis-failed.json", .failed)
        ]

        for (name, expectedStatus) in fixtures {
            let result = try decoder.decode(
                AnalysisResult.self,
                from: ContractFixtureLoader.data(named: name)
            )
            XCTAssertEqual(result.status, expectedStatus, name)
            XCTAssertFalse(result.analysisID.isEmpty, name)
            XCTAssertFalse(result.nextCursor.isEmpty, name)
            XCTAssertEqual(result.message.cursor, result.nextCursor, name)
        }
    }

    func testRouteFixturePreservesNullableProviderFactsAndISOFields() throws {
        let route = try decoder.decode(
            Route.self,
            from: ContractFixtureLoader.data(named: "route.json")
        )

        XCTAssertEqual(route.status, .routeReady)
        XCTAssertEqual(route.provider, "transit")
        XCTAssertEqual(route.timezone, "America/Los_Angeles")
        XCTAssertEqual(route.leaveAt, Date.iso8601("2026-08-10T08:35:00.000Z"))
        XCTAssertEqual(route.arriveAt, Date.iso8601("2026-08-10T09:02:00.000Z"))
        XCTAssertNil(route.geometry)
        XCTAssertEqual(route.steps.count, 3)
        XCTAssertNil(route.steps[0].service)
        XCTAssertEqual(route.steps[1].platform, "Platform 2")
    }

    func testSessionFixtureDecodesRotatingTokensAndExpiry() throws {
        let session = try decoder.decode(
            Session.self,
            from: ContractFixtureLoader.data(named: "session.json")
        )

        XCTAssertEqual(session.tokenType, "Bearer")
        XCTAssertEqual(session.expiresAt, Date.iso8601("2026-08-10T08:20:00.000Z"))
        XCTAssertEqual(session.refreshExpiresAt, Date.iso8601("2026-09-09T08:05:00.000Z"))
    }
}
