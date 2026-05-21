import Foundation
import RevenueCat

protocol SubscriptionServiceProtocol {
    var isPremium: Bool { get }
    func configure(apiKey: String)
    func fetchOfferings() async throws -> [Package]
    func purchase(package: Package) async throws -> Bool
    func restorePurchases() async throws -> Bool
    func listenForUpdates(onChange: @escaping (Bool) -> Void)
}
