import Foundation
import XCTest
@testable import LifeManager

final class KeychainSessionStoreTests: XCTestCase {
    func testSaveAndLoadRoundTripUsesKeychainAdapter() async throws {
        let adapter = InMemoryKeychainAdapter()
        let store = KeychainSessionStore(adapter: adapter, service: "ai.anicca.life-manager.tests")
        let expected = TestSessionFactory.make()

        try await store.save(expected)
        let loaded = try await store.load()

        XCTAssertEqual(loaded, expected)
        XCTAssertEqual(adapter.lastWriteAccessibility, .afterFirstUnlockThisDeviceOnly)
    }

    func testSavingAgainUpdatesTheExistingKeychainItem() async throws {
        let adapter = InMemoryKeychainAdapter()
        let store = KeychainSessionStore(adapter: adapter, service: "ai.anicca.life-manager.tests")

        try await store.save(TestSessionFactory.make(accessToken: "first"))
        try await store.save(TestSessionFactory.make(accessToken: "rotated"))

        let loaded = try await store.load()
        XCTAssertEqual(loaded?.accessToken, "rotated")
        XCTAssertEqual(adapter.writeOperations, [.add, .update])
    }

    func testClearRemovesTheSessionAndIsIdempotent() async throws {
        let adapter = InMemoryKeychainAdapter()
        let store = KeychainSessionStore(adapter: adapter, service: "ai.anicca.life-manager.tests")

        try await store.save(TestSessionFactory.make())
        try await store.clear()
        try await store.clear()

        let loaded = try await store.load()
        XCTAssertNil(loaded)
        XCTAssertEqual(adapter.deleteCount, 2)
    }
}

private enum TestSessionFactory {
    static func make(accessToken: String = "access-token") -> Session {
        Session(
            accessToken: accessToken,
            refreshToken: "refresh-token",
            tokenType: "Bearer",
            expiresAt: Date.iso8601("2026-08-10T08:20:00.000Z"),
            refreshExpiresAt: Date.iso8601("2026-09-09T08:05:00.000Z")
        )
    }
}

private final class InMemoryKeychainAdapter: KeychainSecurityAdapter, @unchecked Sendable {
    enum Operation: Equatable {
        case add
        case update
    }

    private var storage: Data?
    private(set) var writeOperations: [Operation] = []
    private(set) var lastWriteAccessibility: KeychainAccessibility?
    private(set) var deleteCount = 0

    func read(_ query: KeychainQuery) throws -> Data? {
        storage
    }

    func add(_ data: Data, query: KeychainQuery, accessibility: KeychainAccessibility) throws {
        storage = data
        writeOperations.append(.add)
        lastWriteAccessibility = accessibility
    }

    func update(_ data: Data, query: KeychainQuery, accessibility: KeychainAccessibility) throws {
        storage = data
        writeOperations.append(.update)
        lastWriteAccessibility = accessibility
    }

    func delete(_ query: KeychainQuery) throws {
        storage = nil
        deleteCount += 1
    }
}
