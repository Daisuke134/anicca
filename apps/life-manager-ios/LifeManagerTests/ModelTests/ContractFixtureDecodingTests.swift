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

        XCTAssertEqual(bootstrap.user.productLocale, .en)
        XCTAssertEqual(bootstrap.user.timezone, "America/Los_Angeles")
        XCTAssertEqual(bootstrap.user.id, "user:v1:server-derived-8f3a")
        XCTAssertNil(bootstrap.user.name)
        XCTAssertEqual(bootstrap.user.home.status, .missing)
        XCTAssertNil(bootstrap.user.home.display)
        XCTAssertEqual(bootstrap.calendar.status, .connected)
        XCTAssertEqual(bootstrap.analysis.status, .idle)
    }

    func testEveryFrozenCanonicalFixtureIsPackagedInThisCheckout() throws {
        let names = [
            "account-deletion.json",
            "analysis-failed.json",
            "analysis-needs_information.json",
            "analysis-no_upcoming_event.json",
            "analysis-route_ready.json",
            "analysis-route_unavailable.json",
            "apns-device.json",
            "bootstrap.json",
            "call.json",
            "chat-page.json",
            "contract.json",
            "device-deleted.json",
            "error.json",
            "profile-patch.json",
            "question-reply.json",
            "route.json",
            "semantic-outbox.json",
            "session-revoked.json",
            "session-start.json",
            "session.json"
        ]

        for name in names {
            let data = try ContractFixtureLoader.data(named: name)
            XCTAssertFalse(data.isEmpty, name)
        }
    }

    func testCanonicalChatPageIncludesAnalysisAndCallStatusKinds() throws {
        let chat = try decoder.decode(
            ChatPage.self,
            from: ContractFixtureLoader.data(named: "chat-page.json")
        )

        XCTAssertEqual(chat.messages.count, 2)
        XCTAssertEqual(chat.messages.map(\.type), [.system, .route])
        XCTAssertEqual(chat.messages[1].route?.origin.userContent, "Shipathon Roppongi")
    }

    func testEveryNonAnalysisCanonicalFixtureDecodesIntoItsTypedModel() throws {
        let device = try decoder.decode(
            APNsDeviceReceipt.self,
            from: ContractFixtureLoader.data(named: "apns-device.json")
        )
        XCTAssertEqual(device.deviceID, "device:v1:opaque-8f3a")
        XCTAssertEqual(device.environment, .production)

        let call = try decoder.decode(
            CallReceipt.self,
            from: ContractFixtureLoader.data(named: "call.json")
        )
        XCTAssertEqual(call.status, .placed)
        XCTAssertEqual(call.attemptID, "call:v1:opaque-8f3a")
        XCTAssertEqual(call.callLanguage, .en)
        XCTAssertEqual(call.providerReceipt?.ccid, "call-provider-receipt-8f3a")

        let deletion = try decoder.decode(
            AccountDeletionReceipt.self,
            from: ContractFixtureLoader.data(named: "account-deletion.json")
        )
        XCTAssertEqual(deletion.operationID, "deletion:v1:opaque-8f3a")
        XCTAssertEqual(deletion.status, .completed)
        XCTAssertEqual(deletion.providerCleanup.first?.provider, "calendar")

        let manifest = try decoder.decode(
            MobileContractManifest.self,
            from: ContractFixtureLoader.data(named: "contract.json")
        )
        XCTAssertEqual(manifest.version, "mobile-v1")
        XCTAssertEqual(manifest.endpoints.count, 13)

        let deleted = try decoder.decode(
            DeviceDeletionReceipt.self,
            from: ContractFixtureLoader.data(named: "device-deleted.json")
        )
        XCTAssertTrue(deleted.deleted)

        let error = try decoder.decode(
            MobileErrorFixture.self,
            from: ContractFixtureLoader.data(named: "error.json")
        )
        XCTAssertEqual(error.error.code, "analysis_failed")

        let profilePatch = try decoder.decode(
            ProfileDraft.self,
            from: ContractFixtureLoader.data(named: "profile-patch.json")
        )
        XCTAssertEqual(profilePatch.home, "100 Market Street, San Francisco")

        let reply = try decoder.decode(
            QuestionReplyReceipt.self,
            from: ContractFixtureLoader.data(named: "question-reply.json")
        )
        XCTAssertEqual(reply.status, "answered")
        XCTAssertNil(reply.analysis)

        let outbox = try decoder.decode(
            SemanticOutboxRecord.self,
            from: ContractFixtureLoader.data(named: "semantic-outbox.json")
        )
        XCTAssertEqual(outbox.sequence, 42)

        let revoked = try decoder.decode(
            SessionRevokedReceipt.self,
            from: ContractFixtureLoader.data(named: "session-revoked.json")
        )
        XCTAssertTrue(revoked.revoked)
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
