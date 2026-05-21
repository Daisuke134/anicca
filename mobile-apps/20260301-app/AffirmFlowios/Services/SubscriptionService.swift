import Foundation

// MARK: - Mock Types (Replace with RevenueCat when SPM is configured)

struct MockPackage: Identifiable, Equatable {
    let id: String
    let identifier: String
    let localizedTitle: String
    let localizedDescription: String
    let localizedPriceString: String

    static let monthly = MockPackage(
        id: "monthly",
        identifier: "$rc_monthly",
        localizedTitle: "Monthly",
        localizedDescription: "Billed monthly",
        localizedPriceString: "$4.99/month"
    )

    static let annual = MockPackage(
        id: "annual",
        identifier: "$rc_annual",
        localizedTitle: "Annual",
        localizedDescription: "Best value - Save 50%",
        localizedPriceString: "$29.99/year"
    )
}

struct MockOffering {
    let identifier: String
    let availablePackages: [MockPackage]

    static let `default` = MockOffering(
        identifier: "default",
        availablePackages: [.annual, .monthly]
    )
}

struct MockOfferings {
    let current: MockOffering?

    static let `default` = MockOfferings(current: .default)
}

// MARK: - Subscription Service

@Observable
class SubscriptionService {
    private(set) var isPremium: Bool = false
    private(set) var offerings: MockOfferings?

    static let shared = SubscriptionService()

    private init() {
        // Check stored premium status
        isPremium = UserDefaults.standard
            .bool(forKey: "isPremium")
    }

    func configure() {
        // TODO: Configure RevenueCat when SPM is added
        // Purchases.configure(withAPIKey: "YOUR_REVENUECAT_API_KEY")
        Task { await checkSubscriptionStatus() }
    }

    func checkSubscriptionStatus() async {
        // TODO: Check with RevenueCat when configured
        // For now, use stored value
        isPremium = UserDefaults.standard
            .bool(forKey: "isPremium")
    }

    func fetchOfferings() async {
        // TODO: Fetch from RevenueCat when configured
        // Simulate network delay
        try? await Task.sleep(nanoseconds: 300_000_000)
        offerings = .default
    }

    func purchase(package: MockPackage) async throws {
        // TODO: Purchase via RevenueCat when configured
        // Simulate purchase flow
        try? await Task.sleep(nanoseconds: 500_000_000)

        // For demo, always succeed
        isPremium = true
        UserDefaults.standard
            .set(isPremium, forKey: "isPremium")
    }

    func restorePurchases() async throws {
        // TODO: Restore via RevenueCat when configured
        try? await Task.sleep(nanoseconds: 300_000_000)

        // Check stored status
        isPremium = UserDefaults.standard
            .bool(forKey: "isPremium")
    }
}
