// File: Views/Onboarding/NotificationPermissionView.swift
// Onboarding Step 3: Request daily reminder notification
// Source: Apple UNUserNotificationCenter docs — requestAuthorization(options:)

import SwiftUI

struct NotificationPermissionView: View {
    @Bindable var viewModel: OnboardingViewModel

    var body: some View {
        VStack(spacing: 32) {
            Spacer()

            Image(systemName: "bell.badge.fill")
                .font(.system(size: 80))
                .foregroundStyle(.brandPrimary)

            Text("Daily Reminders")
                .font(.largeTitle.bold())
                .accessibilityIdentifier("onboarding_notification_title")

            Text("Get a nudge each morning to complete your Zone 2 session. You can customize the time in Settings.")
                .font(.body)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)

            Spacer()

            Button("Enable Reminders") {
                Task {
                    let granted = await NotificationService.shared.requestPermission()
                    if granted {
                        await NotificationService.shared.scheduleDailyReminder()
                    }
                    viewModel.goNext()
                }
            }
            .buttonStyle(.borderedProminent)
            .tint(.brandPrimary)
            .accessibilityIdentifier("btn_enable_notifications")

            Button("Not Now") { viewModel.goNext() }
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("btn_skip_notifications")
        }
        .padding(32)
    }
}
