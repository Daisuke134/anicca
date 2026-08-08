import Foundation
import Security

actor KeychainSessionStore: SessionStoring {
    private let adapter: KeychainSecurityAdapter
    private let query: KeychainQuery

    init(
        adapter: KeychainSecurityAdapter = SystemKeychainSecurityAdapter(),
        service: String = "ai.anicca.life-manager",
        account: String = "mobile-session"
    ) {
        self.adapter = adapter
        query = KeychainQuery(service: service, account: account)
    }

    func load() async throws -> Session? {
        guard let data = try adapter.read(query) else { return nil }
        do {
            return try JSONDecoder.lifeManager.decode(Session.self, from: data)
        } catch {
            throw KeychainSessionStoreError.decodingFailed
        }
    }

    func save(_ session: Session) async throws {
        let data: Data
        do {
            data = try JSONEncoder.lifeManager.encode(session)
        } catch {
            throw KeychainSessionStoreError.encodingFailed
        }

        if try adapter.read(query) == nil {
            try adapter.add(
                data,
                query: query,
                accessibility: .afterFirstUnlockThisDeviceOnly
            )
        } else {
            try adapter.update(
                data,
                query: query,
                accessibility: .afterFirstUnlockThisDeviceOnly
            )
        }
    }

    func clear() async throws {
        try adapter.delete(query)
    }
}

final class SystemKeychainSecurityAdapter: KeychainSecurityAdapter, @unchecked Sendable {
    func read(_ query: KeychainQuery) throws -> Data? {
        var attributes = baseQuery(query)
        attributes[kSecReturnData as String] = true
        attributes[kSecMatchLimit as String] = kSecMatchLimitOne

        var result: CFTypeRef?
        let status = SecItemCopyMatching(attributes as CFDictionary, &result)
        switch status {
        case errSecSuccess:
            return result as? Data
        case errSecItemNotFound:
            return nil
        default:
            throw KeychainSecurityError(status: status)
        }
    }

    func add(_ data: Data, query: KeychainQuery, accessibility: KeychainAccessibility) throws {
        var attributes = baseQuery(query)
        attributes[kSecValueData as String] = data
        attributes[kSecAttrAccessible as String] = accessibility.secAttrValue
        let status = SecItemAdd(attributes as CFDictionary, nil)
        guard status == errSecSuccess else {
            throw KeychainSecurityError(status: status)
        }
    }

    func update(_ data: Data, query: KeychainQuery, accessibility: KeychainAccessibility) throws {
        let values: [String: Any] = [
            kSecValueData as String: data,
            kSecAttrAccessible as String: accessibility.secAttrValue
        ]
        let status = SecItemUpdate(baseQuery(query) as CFDictionary, values as CFDictionary)
        guard status == errSecSuccess else {
            throw KeychainSecurityError(status: status)
        }
    }

    func delete(_ query: KeychainQuery) throws {
        let status = SecItemDelete(baseQuery(query) as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw KeychainSecurityError(status: status)
        }
    }

    private func baseQuery(_ query: KeychainQuery) -> [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: query.service,
            kSecAttrAccount as String: query.account
        ]
    }
}

private extension KeychainAccessibility {
    var secAttrValue: CFString {
        switch self {
        case .afterFirstUnlockThisDeviceOnly:
            return kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        }
    }
}

struct KeychainSecurityError: Error, Equatable, Sendable {
    let status: OSStatus
}
