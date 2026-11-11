import Foundation
import RevenueCat

@Observable
@MainActor
class SubscriptionService {
    var isPremium = false
    var offerings: Offerings?
    var isLoading = false
    var errorMessage: String?
    var freeUsesRemaining: Int = 3

    private let freeUsesKey = "free_translation_uses"
    private let lastResetKey = "free_uses_last_reset"
    private let maxFreeUses = 3

    init() {
        loadFreeUses()
    }

    func checkSubscriptionStatus() async {
        do {
            let customerInfo = try await Purchases.shared.customerInfo()
            isPremium = customerInfo.entitlements["premium"]?.isActive == true
        } catch {
            isPremium = false
        }
    }

    func fetchOfferings() async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }
        do {
            offerings = try await Purchases.shared.offerings()
        } catch {
            errorMessage = "プランの取得に失敗しました"
        }
    }

    func purchase(package: Package) async -> Bool {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        let product = package.storeProduct
        AnalyticsManager.shared.trackPurchaseStarted(
            productId: product.productIdentifier,
            price: NSDecimalNumber(decimal: product.price).doubleValue,
            currency: product.currencyCode ?? "unknown",
            period: Self.periodName(for: package),
            trialEligible: product.introductoryDiscount != nil
        )
        do {
            let result = try await Purchases.shared.purchase(package: package)
            if result.userCancelled {
                AnalyticsManager.shared.trackPurchaseCancelled(productId: product.productIdentifier)
                return false
            }
            let entitlement = result.customerInfo.entitlements["premium"]
            isPremium = entitlement?.isActive == true
            if isPremium {
                // Auxiliary client record; ground truth is RC's rc_* events (spec §3.5).
                AnalyticsManager.shared.trackPurchaseCompleted(productId: product.productIdentifier)
                if entitlement?.periodType == .trial {
                    AnalyticsManager.shared.trackTrialStarted(
                        productId: product.productIdentifier,
                        trialDays: Self.trialDays(for: product)
                    )
                }
            }
            return isPremium
        } catch {
            if let purchaseError = error as? RevenueCat.ErrorCode, purchaseError == .purchaseCancelledError {
                AnalyticsManager.shared.trackPurchaseCancelled(productId: product.productIdentifier)
                return false
            }
            AnalyticsManager.shared.trackPurchaseFailed(
                productId: product.productIdentifier,
                errorCode: "\((error as NSError).code)"
            )
            errorMessage = "購入に失敗しました。もう一度お試しください。"
            return false
        }
    }

    private static func periodName(for package: Package) -> String {
        switch package.packageType {
        case .weekly: return "week"
        case .monthly: return "month"
        case .annual: return "year"
        case .lifetime: return "lifetime"
        default: return "custom"
        }
    }

    private static func trialDays(for product: StoreProduct) -> Int {
        guard let period = product.introductoryDiscount?.subscriptionPeriod else { return 0 }
        switch period.unit {
        case .day: return period.value
        case .week: return period.value * 7
        case .month: return period.value * 30
        case .year: return period.value * 365
        @unknown default: return period.value
        }
    }

    func restorePurchases() async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }
        do {
            let customerInfo = try await Purchases.shared.restorePurchases()
            isPremium = customerInfo.entitlements["premium"]?.isActive == true
            if !isPremium {
                errorMessage = "復元できる購入が見つかりませんでした"
            }
        } catch {
            errorMessage = "復元に失敗しました"
        }
    }

    func canUseTranslation() -> Bool {
        if isPremium { return true }
        resetFreeUsesIfNeeded()
        return freeUsesRemaining > 0
    }

    func consumeFreeUse() {
        guard !isPremium else { return }
        freeUsesRemaining = max(0, freeUsesRemaining - 1)
        UserDefaults.standard.set(maxFreeUses - freeUsesRemaining, forKey: freeUsesKey)
    }

    private func loadFreeUses() {
        resetFreeUsesIfNeeded()
        let usedCount = UserDefaults.standard.integer(forKey: freeUsesKey)
        freeUsesRemaining = max(0, maxFreeUses - usedCount)
    }

    private func resetFreeUsesIfNeeded() {
        let lastReset = UserDefaults.standard.object(forKey: lastResetKey) as? Date ?? .distantPast
        if !Calendar.current.isDateInToday(lastReset) {
            UserDefaults.standard.set(0, forKey: freeUsesKey)
            UserDefaults.standard.set(Date(), forKey: lastResetKey)
            freeUsesRemaining = maxFreeUses
        }
    }
}
