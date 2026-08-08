import Foundation
import XCTest

final class MaestroFlowContractTests: XCTestCase {
    func testRealStagingFlowsUseStableIDsAndNoStaticWaitOrBearerSecrets() throws {
        let english = try Self.flow(named: "english-onboarding-route.yaml")
        let japanese = try Self.flow(named: "japanese-onboarding-route.yaml")
        let push = try Self.flow(named: "push-deep-link.yaml")

        XCTAssertTrue(english.contains("STAGING_CALLBACK_URL"))
        XCTAssertTrue(japanese.contains("STAGING_CALLBACK_URL"))
        XCTAssertTrue(push.contains("PUSH_MESSAGE_ID"))
        for (name, flow) in [("english", english), ("japanese", japanese), ("push", push)] {
            XCTAssertTrue(flow.contains("appId: ai.anicca.life-manager"), name)
            XCTAssertFalse(flow.range(of: "\\n- wait:", options: .regularExpression) != nil, name)
            XCTAssertFalse(flow.localizedCaseInsensitiveContains("accessToken"), name)
            XCTAssertFalse(flow.localizedCaseInsensitiveContains("refreshToken"), name)
            XCTAssertFalse(flow.localizedCaseInsensitiveContains("authorization: bearer"), name)
        }
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

    private static func flow(named name: String) throws -> String {
        let current = URL(fileURLWithPath: #filePath)
        let root = current
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let path = root.appendingPathComponent("maestro").appendingPathComponent(name)
        return try String(contentsOf: path, encoding: .utf8)
    }
}
