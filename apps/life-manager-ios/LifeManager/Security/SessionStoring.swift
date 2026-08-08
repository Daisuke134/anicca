import Foundation

protocol SessionStoring: Sendable {
    func load() async throws -> Session?
    func save(_ session: Session) async throws
    func clear() async throws
}

protocol SessionPropagating: Sendable {
    func setSession(_ session: Session?) async
}

final class SessionPropagationRelay: @unchecked Sendable {
    private let lock = NSLock()
    private var targets: [any SessionPropagating] = []

    func attach(_ target: any SessionPropagating) {
        lock.lock()
        targets.append(target)
        lock.unlock()
    }

    func propagate(_ session: Session?) async {
        for target in targetSnapshot() {
            await target.setSession(session)
        }
    }

    private func targetSnapshot() -> [any SessionPropagating] {
        lock.lock()
        defer { lock.unlock() }
        return targets
    }
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
