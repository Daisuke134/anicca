import Foundation
import RevenueCat

@Observable
final class PaywallViewModel {
    var packages: [Package] = []
    var selectedPlanIndex: Int = 2
    var isLoading = false
    var isPurchased = false
    var errorMessage: String?

    private let subscriptionService: SubscriptionServiceProtocol

    init(subscriptionService: SubscriptionServiceProtocol = SubscriptionService.shared) {
        self.subscriptionService = subscriptionService
    }

    @MainActor
    func loadOfferings() async {
        isLoading = true
        errorMessage = nil
        do {
            packages = try await subscriptionService.fetchOfferings()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    @MainActor
    func purchase() async {
        guard selectedPlanIndex < packages.count else {
            errorMessage = "Please select a plan"
            return
        }
        isLoading = true
        errorMessage = nil
        do {
            let success = try await subscriptionService.purchase(package: packages[selectedPlanIndex])
            isPurchased = success
        } catch {
            errorMessage = error.localizedDescription
            isPurchased = false
        }
        isLoading = false
    }

    @MainActor
    func restore() async {
        isLoading = true
        errorMessage = nil
        do {
            let active = try await subscriptionService.restorePurchases()
            isPurchased = active
            if !active {
                errorMessage = "No active subscription found"
            }
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func selectPlan(at index: Int) {
        selectedPlanIndex = index
    }
}
