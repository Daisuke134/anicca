import SwiftUI
import RevenueCat
import Mixpanel
import AppTrackingTransparency

@main
struct CalmCortisolApp: App {
    @StateObject private var subscriptionManager = SubscriptionManager.shared
    @AppStorage("onboarding_completed") private var onboardingCompleted = false

    init() {
        setupRevenueCat()
        setupMixpanel()
        setupNotifications()
    }

    var body: some Scene {
        WindowGroup {
            if onboardingCompleted {
                MainTabView()
                    .environmentObject(subscriptionManager)
            } else {
                OnboardingWelcomeView()
                    .environmentObject(subscriptionManager)
            }
        }
    }

    private func setupRevenueCat() {
        Purchases.configure(withAPIKey: "appl_pcZedDwIwXVSSdEugQZPMBormtl")
        Purchases.logLevel = .error
    }

    private func setupMixpanel() {
        Mixpanel.initialize(token: "96835bddc4fd0f2613e805d98c5915cd", trackAutomaticEvents: true)
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            ATTrackingManager.requestTrackingAuthorization { _ in }
        }
    }

    private func setupNotifications() {
        UNUserNotificationCenter.current().delegate = NotificationDelegate.shared
    }
}
