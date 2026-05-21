import SwiftUI

struct SettingsView: View {
    @State private var viewModel = SettingsViewModel()

    var body: some View {
        NavigationStack {
            List {
                preferencesSection
                subscriptionSection
                aboutSection
            }
            .navigationTitle("Settings")
            .sheet(isPresented: $viewModel.showPaywall) {
                PaywallView(isOnboarding: false, onDismiss: {
                    viewModel.showPaywall = false
                })
            }
        }
        .accessibilityIdentifier(AccessibilityID.settingsView)
    }

    // MARK: - Preferences

    private var preferencesSection: some View {
        Section("Preferences") {
            Picker("Temperature Unit", selection: Binding(
                get: { viewModel.temperatureUnit },
                set: { viewModel.setTemperatureUnit($0) }
            )) {
                Text("\u{00B0}C").tag(TemperatureUnit.celsius)
                Text("\u{00B0}F").tag(TemperatureUnit.fahrenheit)
            }
            .pickerStyle(.segmented)
            .accessibilityIdentifier(AccessibilityID.settingsTempUnit)

            Toggle("Notifications", isOn: $viewModel.notificationsEnabled)
                .tint(Theme.Colors.accent)
                .accessibilityIdentifier(AccessibilityID.settingsNotifications)
        }
    }

    // MARK: - Subscription

    private var subscriptionSection: some View {
        Section("Subscription") {
            Button {
                viewModel.tapUpgrade()
            } label: {
                HStack {
                    Image(systemName: "crown.fill")
                        .foregroundStyle(Theme.Colors.warning)
                    Text("Upgrade to Premium")
                    Spacer()
                    Image(systemName: "chevron.right")
                        .foregroundStyle(Theme.Colors.secondaryLabel)
                }
            }
            .accessibilityIdentifier(AccessibilityID.settingsUpgrade)

            Button("Restore Purchases") {
                Task {
                    _ = try? await SubscriptionService.shared.restorePurchases()
                }
            }
            .accessibilityIdentifier(AccessibilityID.settingsRestore)
        }
    }

    // MARK: - About

    private var aboutSection: some View {
        Section("About") {
            if let url = URL(string: "https://aniccaai.com/privacy") {
                Link(destination: url) {
                    HStack {
                        Text("Privacy Policy")
                        Spacer()
                        Image(systemName: "arrow.up.right")
                            .foregroundStyle(Theme.Colors.secondaryLabel)
                    }
                }
                .accessibilityIdentifier(AccessibilityID.settingsPrivacy)
            }

            HStack {
                Text("Version")
                Spacer()
                Text(viewModel.appVersion)
                    .foregroundStyle(Theme.Colors.secondaryLabel)
            }
        }
    }
}
