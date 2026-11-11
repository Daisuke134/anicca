import SwiftUI
import RevenueCat

@main
struct BenYinFanYiAIApp: App {
    @State private var aiService = AIService()
    @State private var subscriptionService = SubscriptionService()
    @State private var historyService = HistoryService()
    @State private var hasCompletedOnboarding = UserDefaults.standard.bool(forKey: "hasCompletedOnboarding")

    init() {
        #if DEBUG
        Purchases.logLevel = .debug
        Purchases.configure(withAPIKey: Config.EXPO_PUBLIC_REVENUECAT_TEST_API_KEY)
        #else
        Purchases.configure(withAPIKey: Config.EXPO_PUBLIC_REVENUECAT_IOS_API_KEY)
        #endif

        // Mixpanel (shared spec: kpi-churn-event-spec-2026-11-11 §3.2/§3.3).
        AnalyticsManager.shared.configure(token: Config.MIXPANEL_TOKEN)
        // Link client events with RevenueCat's server-side rc_* events.
        if let distinctId = AnalyticsManager.shared.distinctId {
            Purchases.shared.setAttributes(["$mixpanel_distinct_id": distinctId])
        }
        AnalyticsManager.shared.trackAppOpened()
    }

    var body: some Scene {
        WindowGroup {
            if hasCompletedOnboarding {
                ContentView()
                    .environment(aiService)
                    .environment(subscriptionService)
                    .environment(historyService)
                    .task {
                        await subscriptionService.checkSubscriptionStatus()
                    }
            } else {
                OnboardingView {
                    UserDefaults.standard.set(true, forKey: "hasCompletedOnboarding")
                    hasCompletedOnboarding = true
                }
                .environment(subscriptionService)
                .task {
                    await subscriptionService.checkSubscriptionStatus()
                }
            }
        }
    }
}
