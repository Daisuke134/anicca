// File: App/Zone2DailyApp.swift
// App entry point — RevenueCat configure + SwiftData ModelContainer
// Source: RevenueCat iOS Quickstart — https://docs.revenuecat.com/docs/ios
// "Configure Purchases.shared in App entry point."
// Rule 20: RevenueCat SDK only — RevenueCatUI forbidden
// Rule 17: No analytics/tracking SDK
// Rule 23: No AI API

import SwiftUI
import SwiftData
import RevenueCat

@main
struct Zone2DailyApp: App {
    @State private var subscriptionService = SubscriptionService()

    init() {
        let apiKey = Bundle.main.infoDictionary?["RC_API_KEY"] as? String ?? ""
        subscriptionService.configure(apiKey: apiKey)
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(subscriptionService)
        }
        .modelContainer(for: [WorkoutSession.self, UserProfile.self])
    }
}
