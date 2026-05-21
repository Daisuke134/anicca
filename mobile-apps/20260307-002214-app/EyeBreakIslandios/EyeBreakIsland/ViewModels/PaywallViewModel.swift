import SwiftUI
import RevenueCat

@MainActor
final class PaywallViewModel: ObservableObject {
    @Published var packages: [Package] = []
    @Published var selectedPackage: Package?
    @Published var isPurchasing = false
    @Published var isLoading = false
    @Published var purchaseCompleted = false
    @Published var errorMessage: String?

    private let subscriptionService: SubscriptionServiceProtocol

    init(subscriptionService: SubscriptionServiceProtocol) {
        self.subscriptionService = subscriptionService
    }

    func loadOfferings() async {
        isLoading = true
        do {
            let loaded = try await subscriptionService.loadOfferings()
            packages = loaded
            errorMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func purchase() async {
        guard let package = selectedPackage else { return }
        isPurchasing = true
        errorMessage = nil
        do {
            let success = try await subscriptionService.purchase(package: package)
            if success {
                purchaseCompleted = true
            }
        } catch {
            errorMessage = error.localizedDescription
        }
        isPurchasing = false
    }

    func restore() async {
        isPurchasing = true
        errorMessage = nil
        do {
            let status = try await subscriptionService.restorePurchases()
            if status == .pro {
                purchaseCompleted = true
            }
        } catch {
            errorMessage = error.localizedDescription
        }
        isPurchasing = false
    }
}
