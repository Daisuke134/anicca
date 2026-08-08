import Foundation

enum RetryOperation: String, Codable, CaseIterable, Hashable, Sendable {
    case profile
    case reply
    case call
    case deletion
}

struct PendingOperation: Codable, Equatable, Sendable {
    let idempotencyKey: UUID
    let input: Data?

    init(idempotencyKey: UUID, input: Data? = nil) {
        self.idempotencyKey = idempotencyKey
        self.input = input
    }
}

protocol OperationRetryStoring: Sendable {
    func pending(for operation: RetryOperation) async -> PendingOperation?
    func save(_ operation: RetryOperation, value: PendingOperation) async
    func clear(_ operation: RetryOperation) async
}

actor UserDefaultsOperationRetryStore: OperationRetryStoring {
    private let defaults: UserDefaults
    private let namespace: String

    init(
        defaults: UserDefaults = .standard,
        namespace: String = "ai.anicca.life-manager.retry"
    ) {
        self.defaults = defaults
        self.namespace = namespace
    }

    func pending(for operation: RetryOperation) async -> PendingOperation? {
        guard let data = defaults.data(forKey: key(for: operation)) else { return nil }
        return try? JSONDecoder.lifeManager.decode(PendingOperation.self, from: data)
    }

    func save(_ operation: RetryOperation, value: PendingOperation) async {
        guard let data = try? JSONEncoder.lifeManager.encode(value) else { return }
        defaults.set(data, forKey: key(for: operation))
    }

    func clear(_ operation: RetryOperation) async {
        defaults.removeObject(forKey: key(for: operation))
    }

    private func key(for operation: RetryOperation) -> String {
        "\(namespace).\(operation.rawValue)"
    }
}

enum MutationRetryPolicy {
    static func shouldRetain(after error: Error) -> Bool {
        guard case let APIError.server(statusCode) = error else {
            return true
        }
        switch statusCode {
        case 400, 401, 403, 404, 422:
            return false
        default:
            return true
        }
    }
}
