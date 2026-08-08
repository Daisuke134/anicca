import Foundation
import XCTest

final class LocalizationConsistencyTests: XCTestCase {
    func testEnglishCatalogContainsRequiredProductKeysWithoutJapaneseScript() throws {
        let data = try LocalizationTestResource.data()
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        let strings = try XCTUnwrap(object["strings"] as? [String: Any])
        XCTAssertTrue(Self.requiredKeys.isSubset(of: Set(strings.keys)))
        for key in Self.requiredKeys {
            let entry = try XCTUnwrap(strings[key] as? [String: Any], key)
            let localizations = try XCTUnwrap(entry["localizations"] as? [String: Any], key)
            let english = try XCTUnwrap(localizations["en"] as? [String: Any], key)
            let stringUnit = try XCTUnwrap(english["stringUnit"] as? [String: Any], key)
            let value = try XCTUnwrap(stringUnit["value"] as? String, key)
            XCTAssertNil(value.range(of: "[\\u3040-\\u30ff\\u3400-\\u9fff]", options: .regularExpression), key)
        }
    }

    func testJapaneseCatalogContainsEveryProductKeyAndTranslatesSystemCopy() throws {
        let data = try LocalizationTestResource.data()
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        let strings = try XCTUnwrap(object["strings"] as? [String: Any])
        let englishOnlyKeys: Set<String> = ["app.name"]

        for key in Self.requiredKeys {
            let entry = try XCTUnwrap(strings[key] as? [String: Any], key)
            let localizations = try XCTUnwrap(entry["localizations"] as? [String: Any], key)
            let englishValue = try XCTUnwrap(
                ((localizations["en"] as? [String: Any])?["stringUnit"] as? [String: Any])?["value"] as? String,
                key
            )
            let japanese = try XCTUnwrap(localizations["ja"] as? [String: Any], key)
            let japaneseValue = try XCTUnwrap(
                (japanese["stringUnit"] as? [String: Any])?["value"] as? String,
                key
            )

            if !englishOnlyKeys.contains(key) {
                XCTAssertNotEqual(japaneseValue, englishValue, key)
                XCTAssertNotNil(
                    japaneseValue.range(of: "[\\u3040-\\u30ff\\u3400-\\u9fff]", options: .regularExpression),
                    key
                )
            }
        }
    }

    private static let requiredKeys: Set<String> = [
        "app.name", "welcome.promise", "welcome.connectCalendar", "onboarding.restoring",
        "onboarding.connectingCalendar", "onboarding.analyzing", "profile.title", "profile.name",
        "profile.home", "profile.continue", "phone.prompt", "phone.number", "phone.add", "phone.skip", "analysis.checking",
        "chat.settings", "chat.refresh", "chat.loading", "chat.send", "chat.answerOpenQuestion",
        "chat.staleReply", "chat.staleReplyAccessibility", "chat.tryAgain", "route.showFull",
        "route.close", "route.arrive", "route.details", "route.minutes", "route.minutesBuffer",
        "route.minutesEarly", "paywall.title", "paywall.subtitle", "paywall.upgrade",
        "paywall.restore", "paywall.continueFree", "paywall.notNow", "settings.title",
        "settings.calendar", "settings.profile", "settings.calls", "settings.subscription",
        "settings.account", "settings.productLanguage", "settings.english", "settings.japanese",
        "settings.save", "settings.phone", "settings.enableCalls", "settings.callLanguage",
        "settings.callNow", "settings.cancel", "settings.deleteAccount", "settings.restore",
        "settings.freePath", "settings.logout", "settings.deletionReceipt", "settings.cooldown",
        "settings.callsRemaining", "settings.calendarConnected", "settings.calendarActionRequired",
        "settings.calendarError", "settings.calendarDisconnected", "settings.callAccepted",
        "settings.callCooldown", "settings.callDailyLimit", "error.server",
        "error.sessionExpired", "error.generic", "error.network", "paywall.purchaseFailed",
        "paywall.restoreFailed", "settings.phoneInvalid", "settings.phoneRequired", "settings.callsDisabled"
    ]
}

private enum LocalizationTestResource {
    static func data() throws -> Data {
        let fileManager = FileManager.default
        let current = URL(fileURLWithPath: #filePath)
        let candidates = [
            current
                .deletingLastPathComponent()
                .deletingLastPathComponent()
                .deletingLastPathComponent()
                .appendingPathComponent("LifeManager/Resources/Localizable.xcstrings"),
            URL(fileURLWithPath: "apps/life-manager-ios/LifeManager/Resources/Localizable.xcstrings", relativeTo: URL(fileURLWithPath: fileManager.currentDirectoryPath))
        ]
        for candidate in candidates where fileManager.fileExists(atPath: candidate.path) {
            return try Data(contentsOf: candidate)
        }
        throw NSError(domain: "LocalizationTestResource", code: 1)
    }
}
