// File: Views/Settings/SettingsView.swift
// SCR-009: Settings with notifications toggle + Upgrade → PaywallView navigation
// UX_SPEC §7: toggle_notifications, input_age_settings, btn_upgrade

import SwiftUI
import SwiftData

struct SettingsView: View {
    @Environment(\.modelContext) private var modelContext
    @Query private var profiles: [UserProfile]
    @Environment(SubscriptionService.self) private var subscriptionService
    @AppStorage("notificationsEnabled") private var notificationsEnabled = false
    @State private var showPaywall = false

    var body: some View {
        NavigationStack {
            Form {
                if let profile = profiles.first {
                    Section("Profile") {
                        Stepper("Age: \(profile.age)", value: Bindable(profile).age, in: 10...80)
                            .accessibilityIdentifier("input_age_settings")
                        Stepper("Weekly Goal: \(profile.weeklyGoalMinutes) min",
                                value: Bindable(profile).weeklyGoalMinutes, in: 30...600, step: 30)
                            .accessibilityIdentifier("settings_weekly_goal_stepper")
                    }
                }
                Section("Notifications") {
                    Toggle("Daily Reminders", isOn: $notificationsEnabled)
                        .tint(.brandPrimary)
                        .accessibilityIdentifier("toggle_notifications")
                        .onChange(of: notificationsEnabled) { _, enabled in
                            Task {
                                if enabled {
                                    let granted = await NotificationService.shared.requestPermission()
                                    if granted {
                                        await NotificationService.shared.scheduleDailyReminder()
                                    } else {
                                        notificationsEnabled = false
                                    }
                                } else {
                                    NotificationService.shared.cancelDailyReminder()
                                }
                            }
                        }
                }
                if !subscriptionService.isPremium {
                    Section {
                        Button("Upgrade to Premium") { showPaywall = true }
                            .accessibilityIdentifier("btn_upgrade")
                    }
                }
                Section {
                    if let privacyURL = URL(string: "https://aniccaai.com/privacy") {
                        Link("Privacy Policy", destination: privacyURL)
                            .foregroundStyle(Color.brandPrimary)
                    }
                    if let termsURL = URL(string: "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/") {
                        Link("Terms of Use", destination: termsURL)
                            .foregroundStyle(Color.brandPrimary)
                    }
                }
            }
            .navigationTitle("Settings")
            .sheet(isPresented: $showPaywall) {
                PaywallView(subscriptionService: subscriptionService)
            }
        }
        .accessibilityIdentifier("screen_settings")
    }
}
