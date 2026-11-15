import XCTest
@testable import aniccaios

@MainActor
final class AppleAuthenticationTests: XCTestCase {
    func testRepeatAuthorizationPreservesFirstGrant() {
        let first = AuthCoordinator.FirstGrant(userId: "apple-a", displayName: "Alice", email: "a@example.com")
        let next = AuthCoordinator.FirstGrant(userId: "apple-a", displayName: "", email: nil, previous: first)
        XCTAssertEqual(next.displayName, "Alice")
        XCTAssertEqual(next.email, "a@example.com")
    }

    func testDifferentAppleAccountDoesNotInheritFirstGrant() {
        let first = AuthCoordinator.FirstGrant(userId: "apple-a", displayName: "Alice", email: "a@example.com")
        let next = AuthCoordinator.FirstGrant(userId: "apple-b", displayName: "", email: nil, previous: first)
        XCTAssertEqual(next.displayName, "")
        XCTAssertNil(next.email)
    }

    func testFreshGrantUpdatesOnlyProvidedFields() {
        let first = AuthCoordinator.FirstGrant(userId: "apple-a", displayName: "Alice", email: "a@example.com")
        let next = AuthCoordinator.FirstGrant(userId: "apple-a", displayName: "New name", email: nil, previous: first)
        XCTAssertEqual(next.displayName, "New name")
        XCTAssertEqual(next.email, "a@example.com")
    }

    func testLegacyCredentialsDecodeWithoutInventingAnAppleSubject() throws {
        let data = Data(#"{"userId":"backend-id","displayName":"Alice","email":"a@example.com"}"#.utf8)
        let credentials = try JSONDecoder().decode(UserCredentials.self, from: data)
        XCTAssertNil(credentials.appleUserId)
        XCTAssertEqual(credentials.displayName, "Alice")
    }

    func testAppleSubjectSurvivesCredentialRoundTrip() throws {
        var credentials = UserCredentials(userId: "backend-id", displayName: "Alice", email: nil)
        credentials.appleUserId = "apple-subject"
        let restored = try JSONDecoder().decode(UserCredentials.self, from: JSONEncoder().encode(credentials))
        XCTAssertEqual(restored.appleUserId, "apple-subject")
        XCTAssertNotEqual(restored.appleUserId, restored.userId)
    }

    func testKeychainReplacesAndDeletesCredentialData() throws {
        let account = "test.apple-auth." + UUID().uuidString
        defer { KeychainService.delete(account: account) }
        try KeychainService.save(Data("old".utf8), account: account)
        XCTAssertEqual(KeychainService.load(account: account), Data("old".utf8))
        try KeychainService.save(Data("new".utf8), account: account)
        XCTAssertEqual(KeychainService.load(account: account), Data("new".utf8))
        KeychainService.delete(account: account)
        XCTAssertNil(KeychainService.load(account: account))
    }
}
