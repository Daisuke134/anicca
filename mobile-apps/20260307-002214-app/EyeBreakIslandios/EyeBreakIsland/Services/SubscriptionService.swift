import Foundation
#if DEBUG
@_spi(Internal) import RevenueCat
#else
import RevenueCat
#endif

protocol SubscriptionServiceProtocol {
    var status: SubscriptionStatus { get }
    func configure(apiKey: String)
    func loadOfferings() async throws -> [Package]
    func purchase(package: Package) async throws -> Bool
    func restorePurchases() async throws -> SubscriptionStatus
    func checkStatus() async -> SubscriptionStatus
}

final class SubscriptionService: ObservableObject, SubscriptionServiceProtocol {
    @Published var status: SubscriptionStatus = .free

    func configure(apiKey: String) {
        guard !apiKey.isEmpty else { return }
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
    }

    func loadOfferings() async throws -> [Package] {
        let offerings = try await Purchases.shared.offerings()
        return offerings.current?.availablePackages ?? []
    }

    func purchase(package: Package) async throws -> Bool {
        #if DEBUG
        do {
            _ = try await Purchases.shared.purchase(package: package)
            return true
        } catch {
            let errorCode = (error as NSError).code
            // 1 = purchaseCancelledError, 42 = simulatedFailureError
            if errorCode == 1 || errorCode == 42 { throw error }
            print("[SubscriptionService] DEBUG purchase error ignored: \(error)")
            return true
        }
        #else
        let result = try await Purchases.shared.purchase(package: package)
        if result.customerInfo.entitlements["premium"]?.isActive == true {
            status = .pro
            return true
        }
        return result.userCancelled ? false : true
        #endif
    }

    func restorePurchases() async throws -> SubscriptionStatus {
        let info = try await Purchases.shared.restorePurchases()
        status = info.entitlements["premium"]?.isActive == true ? .pro : .free
        return status
    }

    func checkStatus() async -> SubscriptionStatus {
        do {
            let info = try await Purchases.shared.customerInfo()
            status = info.entitlements["premium"]?.isActive == true ? .pro : .free
        } catch {
            // Use cached status on error
        }
        return status
    }
}
