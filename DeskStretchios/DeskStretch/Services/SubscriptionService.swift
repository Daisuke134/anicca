import Foundation
import RevenueCat

enum SubscriptionError: LocalizedError {
    case timedOut
    case noProducts

    var errorDescription: String? {
        switch self {
        case .timedOut:
            return String(localized: "The App Store took too long to respond. Please check your connection and try again.")
        case .noProducts:
            return String(localized: "Subscriptions are not available right now. Please try again later.")
        }
    }
}

final class SubscriptionService {
    static let shared = SubscriptionService()

    /// Hard ceiling for any App Store round trip, so the UI can never hang forever.
    private let requestTimeout: Duration = .seconds(15)

    func configure(apiKey: String) {
        Purchases.configure(withAPIKey: apiKey)
    }

    func checkPremiumStatus() async -> Bool {
        do {
            let customerInfo = try await withTimeout(requestTimeout) {
                try await Purchases.shared.customerInfo()
            }
            return customerInfo.entitlements["premium"]?.isActive == true
        } catch {
            return false
        }
    }

    /// Returns the packages that can actually be purchased right now.
    /// Throws instead of silently returning nil so the paywall can show a real error + retry.
    func loadAvailablePackages() async throws -> [Package] {
        let offerings = try await withTimeout(requestTimeout) {
            try await Purchases.shared.offerings()
        }
        guard let current = offerings.current else { throw SubscriptionError.noProducts }
        let packages = current.availablePackages
        guard !packages.isEmpty else { throw SubscriptionError.noProducts }
        // Highest price first: annual above monthly.
        return packages.sorted { $0.storeProduct.price > $1.storeProduct.price }
    }

    func purchase(package: Package) async throws -> Bool {
        let result = try await Purchases.shared.purchase(package: package)
        return result.customerInfo.entitlements["premium"]?.isActive == true
    }

    func restorePurchases() async throws -> Bool {
        let customerInfo = try await withTimeout(requestTimeout) {
            try await Purchases.shared.restorePurchases()
        }
        return customerInfo.entitlements["premium"]?.isActive == true
    }

    private func withTimeout<T: Sendable>(
        _ duration: Duration,
        operation: @escaping @Sendable () async throws -> T
    ) async throws -> T {
        try await withThrowingTaskGroup(of: T.self) { group in
            group.addTask { try await operation() }
            group.addTask {
                try await Task.sleep(for: duration)
                throw SubscriptionError.timedOut
            }
            guard let result = try await group.next() else { throw SubscriptionError.timedOut }
            group.cancelAll()
            return result
        }
    }
}
