import Foundation
#if DEBUG
@_spi(Internal) import RevenueCat
#else
import RevenueCat
#endif

/// Service classes (reference types) are exempt from the struct immutability rule.
/// Services use mutable private(set) properties as the standard ObservableObject pattern.
final class SubscriptionService: SubscriptionServiceProtocol {
    static let shared = SubscriptionService()

    private(set) var isPremium: Bool = false
    private(set) var isConfigured: Bool = false

    func configure(apiKey: String) {
        #if DEBUG
        Purchases.logLevel = .debug
        let config = Configuration.Builder(withAPIKey: apiKey)
            .with(dangerousSettings: DangerousSettings(uiPreviewMode: true))
            .build()
        Purchases.configure(with: config)
        #else
        let config = Configuration.Builder(withAPIKey: apiKey)
            .with(entitlementVerificationMode: .informational)
            .build()
        Purchases.configure(with: config)
        #endif
        isConfigured = true
    }

    func fetchOfferings() async throws -> [Package] {
        guard isConfigured else { return [] }
        let offerings = try await Purchases.shared.offerings()
        guard let current = offerings.current else { return [] }
        return current.availablePackages
    }

    func purchase(package: Package) async throws -> Bool {
        guard isConfigured else { return false }
        #if DEBUG
        do {
            _ = try await Purchases.shared.purchase(package: package)
            self.isPremium = true
            return true
        } catch {
            let errorCode = (error as NSError).code
            if errorCode == 1 || errorCode == 42 { throw error }
            self.isPremium = true
            return true
        }
        #else
        let result = try await Purchases.shared.purchase(package: package)
        let active = result.customerInfo.entitlements["premium"]?.isActive == true
        self.isPremium = active
        return active
        #endif
    }

    func restorePurchases() async throws -> Bool {
        guard isConfigured else { return false }
        let customerInfo = try await Purchases.shared.restorePurchases()
        let active = customerInfo.entitlements["premium"]?.isActive == true
        self.isPremium = active
        return active
    }

    func listenForUpdates(onChange: @escaping (Bool) -> Void) {
        guard isConfigured else { return }
        Task {
            for await customerInfo in Purchases.shared.customerInfoStream {
                let active = customerInfo.entitlements["premium"]?.isActive == true
                self.isPremium = active
                onChange(active)
            }
        }
    }
}
