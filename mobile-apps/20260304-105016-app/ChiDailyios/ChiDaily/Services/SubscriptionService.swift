import RevenueCat
import SwiftUI

@Observable
final class SubscriptionService {
    var isProUser: Bool = false
    var freeCheckInsUsed: Int = 0
    var currentOffering: Offering?

    private let freeLimit = 3
    private let rcPublicKey = "appl_uJcOuZaxwYaOemHEHuSHNG"

    func configure() {
        Purchases.configure(withAPIKey: rcPublicKey)
        Task { await refreshStatus() }
    }

    func refreshStatus() async {
        do {
            let customerInfo = try await Purchases.shared.customerInfo()
            isProUser = customerInfo.entitlements["premium"]?.isActive == true
        } catch {
            // Non-fatal: default to free tier
        }
        freeCheckInsUsed = UserDefaults.standard.integer(forKey: "freeCheckInsUsed")
    }

    func fetchOfferings() async {
        do {
            let offerings = try await Purchases.shared.offerings()
            currentOffering = offerings.current
        } catch {
            // Non-fatal: paywall shows without offering if RC unreachable
        }
    }

    func purchase(package: Package) async throws {
        let result = try await Purchases.shared.purchase(package: package)
        isProUser = result.customerInfo.entitlements["premium"]?.isActive == true
    }

    func restorePurchases() async throws {
        let customerInfo = try await Purchases.shared.restorePurchases()
        isProUser = customerInfo.entitlements["premium"]?.isActive == true
    }

    func canStartCheckIn() -> Bool {
        isProUser || freeCheckInsUsed < freeLimit
    }

    func recordFreeCheckIn() {
        freeCheckInsUsed += 1
        UserDefaults.standard.set(freeCheckInsUsed, forKey: "freeCheckInsUsed")
    }
}
