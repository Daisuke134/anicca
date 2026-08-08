import Foundation
import Observation

protocol PaywallPurchasing: Sendable {
    func purchase() async throws
    func restore() async throws
}

@MainActor
@Observable
final class SoftPaywallViewModel {
    private let purchasing: PaywallPurchasing?

    private(set) var isProcessing = false
    private(set) var failure: AppErrorState?
    private(set) var didPurchase = false
    private(set) var didRestore = false

    init(purchasing: PaywallPurchasing?) {
        self.purchasing = purchasing
    }

    func upgrade() async {
        await run(action: "purchase") {
            guard let purchasing else {
                throw APIError.transport("purchase is not configured")
            }
            try await purchasing.purchase()
            didPurchase = true
        }
    }

    func restorePurchases() async {
        await run(action: "restore") {
            guard let purchasing else {
                throw APIError.transport("restore is not configured")
            }
            try await purchasing.restore()
            didRestore = true
        }
    }

    private func run(action: String, operation: () async throws -> Void) async {
        guard !isProcessing else { return }
        isProcessing = true
        failure = nil
        do {
            try await operation()
        } catch {
            failure = AppErrorState(
                backendErrorCode: "paywall_\(action)_failed",
                localizedMessageKey: "paywall.\(action)Failed",
                retryAllowed: true
            )
        }
        isProcessing = false
    }
}
