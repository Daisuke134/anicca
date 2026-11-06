import Foundation

/// Client purchase observations are idempotent; settled revenue stays with Apple/RevenueCat.
final class PurchaseObservationLedger {
    private let defaults: UserDefaults
    private let key = "anicca.analytics.observed-transactions"

    init(defaults: UserDefaults = .standard) { self.defaults = defaults }

    func record(_ transactionID: String?) -> Bool {
        guard let id = transactionID?.trimmingCharacters(in: .whitespacesAndNewlines), !id.isEmpty else { return false }
        var seen = Set(defaults.stringArray(forKey: key) ?? [])
        guard seen.insert(id).inserted else { return false }
        defaults.set(Array(seen), forKey: key)
        return true
    }
}
