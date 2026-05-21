import SwiftUI

struct SettingsView: View {
    @StateObject private var viewModel: SettingsViewModel
    @Environment(\.dismiss) private var dismiss

    init(subscriptionService: SubscriptionServiceProtocol) {
        _viewModel = StateObject(wrappedValue: SettingsViewModel(
            subscriptionService: subscriptionService
        ))
    }

    init(viewModel: SettingsViewModel) {
        _viewModel = StateObject(wrappedValue: viewModel)
    }

    var body: some View {
        NavigationView {
            List {
                timerSection
                notificationsSection
                accountSection
                aboutSection
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") {
                        dismiss()
                    }
                    .accessibilityIdentifier(AccessibilityID.settingsDoneButton)
                }
            }
            .sheet(isPresented: $viewModel.showPaywall) {
                PaywallView(
                    subscriptionService: viewModel.subscriptionService,
                    onDismiss: { viewModel.showPaywall = false },
                    onPurchaseCompleted: {
                        viewModel.showPaywall = false
                        Task { await viewModel.checkSubscriptionStatus() }
                    }
                )
            }
            .task {
                await viewModel.checkSubscriptionStatus()
            }
        }
        .accessibilityIdentifier(AccessibilityID.settingsView)
    }

    private var timerSection: some View {
        Section("Timer") {
            HStack {
                Label("Interval", systemImage: "clock.fill")
                Spacer()
                Text("\(viewModel.timerIntervalMinutes)m")
                    .foregroundStyle(AppColors.textSecondary)
                if !viewModel.isPro {
                    Image(systemName: "lock.fill")
                        .foregroundStyle(AppColors.textTertiary)
                        .font(.caption)
                }
            }
            .accessibilityIdentifier(AccessibilityID.settingsIntervalRow)

            HStack {
                Label("Schedule", systemImage: "calendar")
                Spacer()
                Text(viewModel.scheduleEnabled ? "On" : "Off")
                    .foregroundStyle(AppColors.textSecondary)
                if !viewModel.isPro {
                    Image(systemName: "lock.fill")
                        .foregroundStyle(AppColors.textTertiary)
                        .font(.caption)
                }
            }
            .accessibilityIdentifier(AccessibilityID.settingsScheduleRow)
        }
    }

    private var notificationsSection: some View {
        Section("Notifications") {
            Toggle(isOn: $viewModel.notificationsEnabled) {
                Label("Enabled", systemImage: "bell.fill")
            }
            .accessibilityIdentifier(AccessibilityID.settingsNotificationsToggle)
        }
    }

    private var accountSection: some View {
        Section("Account") {
            Button {
                viewModel.openPaywall()
            } label: {
                HStack {
                    Label("Upgrade to Pro", systemImage: "crown.fill")
                        .foregroundStyle(AppColors.brandPrimary)
                    Spacer()
                    Image(systemName: "chevron.right")
                        .foregroundStyle(AppColors.textTertiary)
                }
            }
            .accessibilityIdentifier(AccessibilityID.settingsUpgradeButton)

            Button {
                Task {
                    await viewModel.restorePurchases()
                }
            } label: {
                HStack {
                    Label("Restore Purchases", systemImage: "arrow.clockwise")
                    if viewModel.isRestoring {
                        Spacer()
                        ProgressView()
                    }
                }
            }
            .disabled(viewModel.isRestoring)
            .accessibilityIdentifier(AccessibilityID.settingsRestoreButton)
        }
    }

    private var aboutSection: some View {
        Section("About") {
            if let url = viewModel.privacyPolicyURL {
                Link(destination: url) {
                    HStack {
                        Label("Privacy Policy", systemImage: "hand.raised.fill")
                        Spacer()
                        Image(systemName: "arrow.up.right.square")
                            .foregroundStyle(AppColors.textTertiary)
                    }
                }
                .accessibilityIdentifier(AccessibilityID.settingsPrivacyLink)
            }

            HStack {
                Text("Version")
                Spacer()
                Text(Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0")
                    .foregroundStyle(AppColors.textSecondary)
            }
        }
    }
}
