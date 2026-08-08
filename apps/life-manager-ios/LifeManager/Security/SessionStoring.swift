import Foundation

protocol SessionStoring: Sendable {
    func load() async throws -> Session?
    func save(_ session: Session) async throws
    func clear() async throws
}

struct KeychainQuery: Equatable, Sendable {
    let service: String
    let account: String
}

enum KeychainAccessibility: String, Equatable, Sendable {
    case afterFirstUnlockThisDeviceOnly
}

protocol KeychainSecurityAdapter: Sendable {
    func read(_ query: KeychainQuery) throws -> Data?
    func add(_ data: Data, query: KeychainQuery, accessibility: KeychainAccessibility) throws
    func update(_ data: Data, query: KeychainQuery, accessibility: KeychainAccessibility) throws
    func delete(_ query: KeychainQuery) throws
}

enum KeychainSessionStoreError: Error, Equatable, Sendable {
    case encodingFailed
    case decodingFailed
}
