import Foundation
import RevenueCat

final class SubscriptionService {
    static let shared = SubscriptionService()

    func configure(apiKey: String) {
        Purchases.configure(withAPIKey: apiKey)
    }

    func checkPremiumStatus() async -> Bool {
        do {
            let customerInfo = try await Purchases.shared.customerInfo()
            return customerInfo.entitlements["premium"]?.isActive == true
        } catch {
            return false
        }
    }

    func getOfferings() async -> Offerings? {
        try? await Purchases.shared.offerings()
    }

    func purchase(package: Package) async throws -> Bool {
        let result = try await Purchases.shared.purchase(package: package)
        return result.customerInfo.entitlements["premium"]?.isActive == true
    }

    func restorePurchases() async throws -> Bool {
        let customerInfo = try await Purchases.shared.restorePurchases()
        return customerInfo.entitlements["premium"]?.isActive == true
    }
}
