import Foundation
import XCTest

final class SigningConfigurationTests: XCTestCase {
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
