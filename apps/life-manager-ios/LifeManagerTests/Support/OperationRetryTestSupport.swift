import Foundation
@testable import LifeManager

actor TestOperationRetryStore: OperationRetryStoring {
    private var values: [RetryOperation: PendingOperation] = [:]

    func pending(for operation: RetryOperation) async -> PendingOperation? {
        values[operation]
    }

    func save(_ operation: RetryOperation, value: PendingOperation) async {
        values[operation] = value
    }

    func clear(_ operation: RetryOperation) async {
        values.removeValue(forKey: operation)
    }
}
