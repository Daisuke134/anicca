import Foundation
import CryptoKit
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

    func testBundledFixturesMatchFrozenBackendContractHashes() throws {
        for (name, expectedHash) in Self.frozenFixtureHashes {
            let actualHash = SHA256.hash(data: try ContractFixtureLoader.data(named: name))
                .map { String(format: "%02x", $0) }
                .joined()
            XCTAssertEqual(actualHash, expectedHash, name)
        }
    }

    func testFixtureLoaderHasNoStaleSiblingOrEnvironmentFallback() throws {
        let sourceURL = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("Support/ContractFixtureLoader.swift")
        let source = try String(contentsOf: sourceURL, encoding: .utf8)

        XCTAssertTrue(source.contains("Bundle(for: ContractFixtureBundleMarker.self)"))
        XCTAssertFalse(source.contains("LIFEMANAGER_CONTRACT_FIXTURES"))
        XCTAssertFalse(source.contains("siblingWorktrees"))
        XCTAssertFalse(source.contains("life-manager/contracts/mobile-v1"))
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

    func testTravelReceiptSemanticKeysDecodeWithoutChangingStableIDOrCursor() throws {
        let data = Data(#"""
        {
          "messages": [
            {
              "id": "message:v1:travel-confirmed",
              "cursor": "cursor:v1:travel-confirmed",
              "createdAt": "2026-08-10T08:31:00.000Z",
              "locale": "en",
              "type": "system",
              "text": "Travel time was added to your Calendar and verified.",
              "semanticKey": "chat.travel_block_confirmed",
              "userContent": { "eventTitle": "Tokyo Tower visit", "eventLocation": "Tokyo Tower" },
              "question": null,
              "route": null,
              "actions": []
            },
            {
              "id": "message:v1:travel-not-added",
              "cursor": "cursor:v1:travel-not-added",
              "createdAt": "2026-08-10T08:32:00.000Z",
              "locale": "ja",
              "type": "system",
              "text": "移動時間をカレンダーに追加できませんでした。",
              "semanticKey": "chat.travel_block_not_added",
              "userContent": { "eventTitle": "東京タワー", "eventLocation": "東京タワー" },
              "question": null,
              "route": null,
              "actions": []
            }
          ],
          "nextCursor": "cursor:v1:travel-not-added",
          "hasMore": false
        }
        """#.utf8)

        let page = try decoder.decode(ChatPage.self, from: data)

        XCTAssertEqual(page.messages.map(\.id), [
            "message:v1:travel-confirmed",
            "message:v1:travel-not-added"
        ])
        XCTAssertEqual(page.messages.map(\.cursor), [
            "cursor:v1:travel-confirmed",
            "cursor:v1:travel-not-added"
        ])
        XCTAssertEqual(page.messages[0].semanticKey, "chat.travel_block_confirmed")
        XCTAssertEqual(page.messages[1].semanticKey, "chat.travel_block_not_added")
        XCTAssertEqual(page.messages.map(\.locale), [.en, .ja])
        XCTAssertEqual(page.nextCursor, "cursor:v1:travel-not-added")
    }

    func testLegacyChatMessagesDecodeWithNilSemanticKey() throws {
        let chat = try decoder.decode(
            ChatPage.self,
            from: ContractFixtureLoader.data(named: "chat-page.json")
        )

        XCTAssertTrue(chat.messages.allSatisfy { $0.semanticKey == nil })
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

    private static let frozenFixtureHashes: [String: String] = [
        "account-deletion.json": "e18c0e585bad3f42dcc77fbf2b9c90959e8678a2a25436b440aab2a58cb614d6",
        "analysis-failed.json": "efa3e05c0301b6756cf0b83e24cebc272b7c5f62e646fd5ef5813f16489080ef",
        "analysis-needs_information.json": "ba37e43754889d031f6a7f1138507406376d7d515807f9cbb885e084105f5bf6",
        "analysis-no_upcoming_event.json": "54478abcbfcb3414874e2bbb85676a6597ad00181228f1b2cd2f42783478cef1",
        "analysis-route_ready.json": "93abf39f534c9c1e5d4f47e47f7470db28927fe5381ede6557acf7894f7c351b",
        "analysis-route_unavailable.json": "b52c11580b78ec7ee5d957e1e769c62f27819faad15b5cd368b8b40451b5dd70",
        "apns-device.json": "48d6f8546c60d67875bb50320ed6fedcfac0b92129d1e001527d14ddf9fcf428",
        "bootstrap.json": "6d80e0fc53356025453f8d27fd323774cad7647842a5ee36fd080c7156544025",
        "call.json": "804c54effcc908a083a2c0bd7160b4d5142c07e543301fa10e4aac58b2fbfd6f",
        "chat-page.json": "c05036c0c74d94bf219face809d8523e472cdfbc9eb4a8665f860dfc50494984",
        "contract.json": "17bd0a7631e56e07643eadbf3f2cdec7f65500bdf9bb44fa2831cb6987daa83c",
        "device-deleted.json": "abac99a55c31e8a7ee0acdb496014ee9ac7b07b1d5fb4b03605a43565818db89",
        "error.json": "2921fcf2c0b7ee76200bfcb3b3372486887f3542220790d55c33f123ad4e0f0f",
        "profile-patch.json": "4de6ebfd30b43ad7ee9d42b2c11176b2854f4af5a4b14bac187c963ec01e9138",
        "question-reply.json": "b0d74d3d82eeb07cb1ff374eac2a8020d59ad95672046e6f0e6e2ef608cee965",
        "route.json": "eb291b81ef82a3baca4bd29b4d3913151667e61f0bc96eb663e00f5820f33197",
        "semantic-outbox.json": "239e35fc84b4d45163a1c18e0f407d7d4fe851a1f0d14dd0c7d2bf3b6d8c58a1",
        "session-revoked.json": "1ad336ebe2b1d44e3dca20d5d849eb6c72e0cad52081e689d826c1b7f175dc67",
        "session-start.json": "b6c3e1044c5568474b38c1af48d3669e71fc70f885c7d3f9bbee4e55412639d8",
        "session.json": "59590e5f6d715b78e8ea0402280c761e6e0560577d97af144e42395417d750e4"
    ]
}
