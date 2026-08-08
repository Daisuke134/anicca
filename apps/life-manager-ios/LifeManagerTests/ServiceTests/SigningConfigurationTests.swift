import Foundation
import XCTest

final class SigningConfigurationTests: XCTestCase {
    func testDebugAndReleaseUseTheRealMobileEnvironmentURLs() throws {
        let debug = try Self.resourceText(named: "Debug.xcconfig", in: "LifeManager/Config")
        let release = try Self.resourceText(named: "Release.xcconfig", in: "LifeManager/Config")

        XCTAssertTrue(
            debug.contains("LIFEMANAGER_API_BASE_URL = https:/$()/life-call-staging-staging.up.railway.app/api/mobile/v1"),
            "Debug must point at the real staging mobile API with an xcconfig-safe URL value"
        )
        XCTAssertTrue(
            release.contains("LIFEMANAGER_API_BASE_URL = https:/$()/life-call-production.up.railway.app/api/mobile/v1"),
            "Release must point at the real production mobile API with an xcconfig-safe URL value"
        )
    }

    func testBuiltDebugInfoPlistResolvesMobileAPIAndCallbackConfiguration() throws {
        let appBundle = try XCTUnwrap(Bundle(identifier: "ai.anicca.life-manager"))
        let info = try XCTUnwrap(appBundle.infoDictionary)

        XCTAssertEqual(
            info["LIFEMANAGER_API_BASE_URL"] as? String,
            "https://life-call-staging-staging.up.railway.app/api/mobile/v1"
        )
        XCTAssertEqual(info["LIFEMANAGER_CALLBACK_SCHEME"] as? String, "lifemanager")
        let callbackSchemes = try XCTUnwrap(
            (info["CFBundleURLTypes"] as? [[String: Any]])?.first?["CFBundleURLSchemes"] as? [String]
        )
        XCTAssertEqual(callbackSchemes, ["lifemanager"])
    }

    func testAPNsEntitlementsAreDevelopmentOnlyForDebugAndProductionForRelease() throws {
        let debug = try Self.resourceData(named: "Debug.entitlements", in: "LifeManager/Config")
        let release = try Self.resourceData(named: "Release.entitlements", in: "LifeManager/Config")
        let debugObject = try XCTUnwrap(try PropertyListSerialization.propertyList(from: debug, options: [], format: nil) as? [String: Any])
        let releaseObject = try XCTUnwrap(try PropertyListSerialization.propertyList(from: release, options: [], format: nil) as? [String: Any])

        XCTAssertEqual(debugObject["aps-environment"] as? String, "development")
        XCTAssertEqual(releaseObject["aps-environment"] as? String, "production")
        XCTAssertTrue(try Self.resourceText(named: "Debug.xcconfig", in: "LifeManager/Config").contains("CODE_SIGN_ENTITLEMENTS[sdk=iphoneos*]"))
        XCTAssertTrue(try Self.resourceText(named: "Release.xcconfig", in: "LifeManager/Config").contains("CODE_SIGN_ENTITLEMENTS[sdk=iphoneos*]"))
    }

    func testDebugSignsDeviceBuildsButKeepsSimulatorUnsigned() throws {
        let debug = try Self.resourceText(named: "Debug.xcconfig", in: "LifeManager/Config")

        XCTAssertTrue(debug.contains("CODE_SIGNING_ALLOWED[sdk=iphoneos*] = YES"))
        XCTAssertTrue(debug.contains("CODE_SIGNING_REQUIRED[sdk=iphoneos*] = YES"))
        XCTAssertTrue(debug.contains("CODE_SIGNING_ALLOWED[sdk=iphonesimulator*] = NO"))
        XCTAssertTrue(debug.contains("CODE_SIGNING_REQUIRED[sdk=iphonesimulator*] = NO"))
    }

    func testFastlaneTestFlightLanesRequireExternalCredentialsAndBuildNumber() throws {
        let fastfile = try Self.resourceText(named: "Fastfile", in: "fastlane")

        XCTAssertTrue(fastfile.contains("lane :build_for_testflight"))
        XCTAssertTrue(fastfile.contains("lane :upload_testflight"))
        XCTAssertTrue(fastfile.contains("ENV.fetch(\"LIFEMANAGER_BUILD_NUMBER\")"))
        XCTAssertTrue(fastfile.contains("ENV.fetch(\"ASC_KEY_ID\")"))
        XCTAssertTrue(fastfile.contains("ENV.fetch(\"ASC_ISSUER_ID\")"))
        XCTAssertTrue(fastfile.contains("ENV.fetch(\"ASC_API_KEY_PATH\")"))
        XCTAssertFalse(fastfile.contains("-----BEGIN PRIVATE KEY-----"))
    }

    private static func resourceURL(named name: String, in directory: String? = nil) -> URL {
        let current = URL(fileURLWithPath: #filePath)
        var root = current
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        if let directory {
            root.appendPathComponent(directory)
        }
        return root.appendingPathComponent(name)
    }

    private static func resourceData(named name: String, in directory: String? = nil) throws -> Data {
        try Data(contentsOf: resourceURL(named: name, in: directory))
    }

    private static func resourceText(named name: String, in directory: String? = nil) throws -> String {
        try String(contentsOf: resourceURL(named: name, in: directory), encoding: .utf8)
    }
}
