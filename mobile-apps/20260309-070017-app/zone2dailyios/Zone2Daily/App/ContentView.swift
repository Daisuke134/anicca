// File: App/ContentView.swift
// Root view — routes between onboarding and main content

import SwiftUI
import SwiftData

struct ContentView: View {
    @AppStorage("hasCompletedOnboarding") private var hasCompletedOnboarding = false
    @Environment(SubscriptionService.self) private var subscriptionService
    @Query private var profiles: [UserProfile]

    var body: some View {
        Group {
            if hasCompletedOnboarding {
                MainTabView()
            } else {
                OnboardingContainerView()
            }
        }
    }
}
