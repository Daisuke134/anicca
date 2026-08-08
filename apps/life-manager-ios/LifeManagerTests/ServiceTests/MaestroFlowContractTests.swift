import Foundation
import XCTest

final class MaestroFlowContractTests: XCTestCase {
    func testRealStagingFlowsUseStableIDsAndNoStaticWaitOrBearerSecrets() throws {
        let english = try Self.flow(named: "english-onboarding-route.yaml")
        let japanese = try Self.flow(named: "japanese-onboarding-route.yaml")
        let preauthorized = try Self.flow(named: "preauthorized-bootstrap-chat.yaml")
        let failure = try Self.flow(named: "preauthorized-travel-failure.yaml")
        let push = try Self.flow(named: "push-deep-link.yaml")
        let cleanup = try Self.resource(named: "staging-seed-and-cleanup.sh", in: "maestro")

        XCTAssertTrue(english.contains("STAGING_CALLBACK_URL"))
        XCTAssertTrue(japanese.contains("STAGING_CALLBACK_URL"))
        XCTAssertTrue(preauthorized.contains("TRAVEL_RECEIPT_MESSAGE_ID"))
        XCTAssertTrue(preauthorized.contains("calendar.travelBlock.confirmed.${TRAVEL_RECEIPT_MESSAGE_ID}"))
        XCTAssertTrue(failure.contains("TRAVEL_FAILURE_MESSAGE_ID"))
        XCTAssertTrue(failure.contains("calendar.travelBlock.notAdded.${TRAVEL_FAILURE_MESSAGE_ID}"))
        XCTAssertTrue(push.contains("PUSH_MESSAGE_ID"))
        for (name, flow) in [("english", english), ("japanese", japanese), ("preauthorized", preauthorized), ("failure", failure), ("push", push)] {
            XCTAssertTrue(flow.contains("appId: ai.anicca.life-manager"), name)
            XCTAssertFalse(flow.range(of: "\\n- wait:", options: .regularExpression) != nil, name)
            XCTAssertFalse(flow.localizedCaseInsensitiveContains("accessToken"), name)
            XCTAssertFalse(flow.localizedCaseInsensitiveContains("refreshToken"), name)
            XCTAssertFalse(flow.localizedCaseInsensitiveContains("authorization: bearer"), name)
        }
        XCTAssertTrue(cleanup.contains("LM_TRAVEL_PROVIDER_EVENT_ID"))
        XCTAssertTrue(cleanup.contains("provider_proxy_request DELETE"))
        XCTAssertTrue(cleanup.contains(".status == 404"))
        XCTAssertFalse(cleanup.contains("/account"))
    }

    func testOnboardingFlowsCoverRealJourneyLeafIDsAndCleanState() throws {
        let english = try Self.flow(named: "english-onboarding-route.yaml")
        let japanese = try Self.flow(named: "japanese-onboarding-route.yaml")
        let requiredOnboardingIDs = [
            "welcome.connectCalendar", "profile.name", "profile.home", "profile.continue",
            "phone.skip", "analysis.phase", "route.showDetails", "route.detail.close",
            "chat.upgrade", "paywall.continueFree", "chat.settings"
        ]

        for (name, flow) in [("english", english), ("japanese", japanese)] {
            XCTAssertTrue(flow.contains("clearState: true"), name)
            XCTAssertTrue(flow.contains("clearKeychain: true"), name)
            for identifier in requiredOnboardingIDs {
                XCTAssertTrue(flow.contains("id: \"\(identifier)\""), "\(name): \(identifier)")
            }
        }
        XCTAssertTrue(english.contains("profile.locale.en"))
        XCTAssertTrue(japanese.contains("profile.locale.ja"))
    }

    func testJapaneseFlowOpensProductLocalePickerBeforeChoosingJapanese() throws {
        let japanese = try Self.flow(named: "japanese-onboarding-route.yaml")

        let picker = try XCTUnwrap(japanese.range(of: "profile.productLocale"))
        let japaneseChoice = try XCTUnwrap(japanese.range(of: "profile.locale.ja"))
        XCTAssertLessThan(picker.lowerBound, japaneseChoice.lowerBound)
    }

    func testWelcomeDeletionReceiptUsesLocalizedEvidenceAndStableAccessibilityID() throws {
        let root = try Self.resource(named: "RootView.swift", in: "LifeManager/App")

        for key in ["account.deletionReceipt", "account.deletionReceiptID", "account.deletionCompletedAt"] {
            XCTAssertTrue(root.contains(key), "welcome receipt must use localized key \(key)")
        }
        XCTAssertTrue(root.contains("receipt.receiptID"))
        XCTAssertTrue(root.contains("receipt.completedAt"))
        XCTAssertTrue(root.contains(".accessibilityIdentifier(\"account.deletionReceipt\")"))
        XCTAssertTrue(root.contains("terminalDeletionReceipt"))
    }

    func testCleanFastlaneLaneBuildsAndPackagesCheckoutFixtures() throws {
        let fastfile = try Self.resource(named: "Fastfile", in: "fastlane")
        let project = try Self.resource(named: "project.yml")
        let loader = try Self.resource(named: "ContractFixtureLoader.swift", in: "LifeManagerTests/Support")
        let receiptTests = try Self.resource(named: "ChatReceiptPresentationTests.swift", in: "LifeManagerTests/StateTests")
        let testLane = try XCTUnwrap(fastfile.range(of: "lane :test"))
        let buildLane = try XCTUnwrap(fastfile.range(of: "lane :build_for_simulator"))
        let laneBody = String(fastfile[testLane.upperBound..<buildLane.lowerBound])

        XCTAssertTrue(laneBody.contains("clean: true"))
        XCTAssertTrue(laneBody.contains("skip_build: false"))
        XCTAssertTrue(project.contains("- LifeManagerTests/TestFixtures/mobile-v1"))
        XCTAssertTrue(project.contains("- LifeManagerTests/StateTests"))
        XCTAssertTrue(loader.contains("checkoutFixtures"))
        XCTAssertTrue(receiptTests.contains("testTravelReceiptAccessibilityIDsUseSemanticKeyAndStableMessageID"))
        XCTAssertTrue(fastfile.contains("def regenerate_xcode_project"))
        XCTAssertTrue(fastfile.contains("xcodegen generate --spec project.yml"))

        let lanes = [
            ("lane :test", "run_tests("),
            ("lane :build_for_simulator", "build_app("),
            ("lane :build_for_testflight", "build_app(")
        ]

        for (laneName, buildInvocation) in lanes {
            let laneStart = try XCTUnwrap(fastfile.range(of: laneName))
            let lane = String(fastfile[laneStart.lowerBound...])
            let regenerate = try XCTUnwrap(lane.range(of: "regenerate_xcode_project"), laneName)
            let build = try XCTUnwrap(lane.range(of: buildInvocation), laneName)
            XCTAssertLessThan(regenerate.lowerBound, build.lowerBound, laneName)
        }
    }

    private static func flow(named name: String) throws -> String {
        try resource(named: name, in: "maestro")
    }

    private static func resource(named name: String, in directory: String? = nil) throws -> String {
        let current = URL(fileURLWithPath: #filePath)
        let root = current
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let path = directory.map { root.appendingPathComponent($0) }?.appendingPathComponent(name)
            ?? root.appendingPathComponent(name)
        return try String(contentsOf: path, encoding: .utf8)
    }
}
