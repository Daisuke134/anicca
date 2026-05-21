import SwiftUI

@MainActor
final class SettingsViewModel: ObservableObject {
    @Published var showPaywall = false
    @Published var subscriptionStatus: SubscriptionStatus = .free
    @Published var errorMessage: String?
    @Published var isRestoring = false

    @AppStorage(Constants.timerIntervalMinutesKey)
    var timerIntervalMinutes: Int = Constants.defaultWorkIntervalMinutes

    @AppStorage(Constants.notificationsEnabledKey)
    var notificationsEnabled: Bool = true

    @AppStorage(Constants.scheduleEnabledKey)
    var scheduleEnabled: Bool = false

    @AppStorage(Constants.scheduleStartHourKey)
    var scheduleStartHour: Int = 9

    @AppStorage(Constants.scheduleEndHourKey)
    var scheduleEndHour: Int = 17

    let subscriptionService: SubscriptionServiceProtocol

    let privacyPolicyURL = URL(string: "https://aniccaai.com/privacy")

    init(subscriptionService: SubscriptionServiceProtocol) {
        self.subscriptionService = subscriptionService
    }

    var isPro: Bool {
        subscriptionStatus == .pro
    }

    func openPaywall() {
        showPaywall = true
    }

    func restorePurchases() async {
        isRestoring = true
        errorMessage = nil
        do {
            let status = try await subscriptionService.restorePurchases()
            subscriptionStatus = status
        } catch {
            errorMessage = error.localizedDescription
        }
        isRestoring = false
    }

    func checkSubscriptionStatus() async {
        let status = await subscriptionService.checkStatus()
        subscriptionStatus = status
    }
}
