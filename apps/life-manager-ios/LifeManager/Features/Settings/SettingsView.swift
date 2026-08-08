import SwiftUI

struct SettingsView: View {
    @State private var viewModel: SettingsViewModel
    private let paywallViewModel: SoftPaywallViewModel?
    @State private var showingCallConfirmation = false
    @State private var showingDeleteConfirmation = false

    init(viewModel: SettingsViewModel, paywallViewModel: SoftPaywallViewModel? = nil) {
        _viewModel = State(initialValue: viewModel)
        self.paywallViewModel = paywallViewModel
    }

    var body: some View {
        NavigationStack {
            Form {
                calendarSection
                profileSection
                phoneSection
                subscriptionSection
                accountSection

                if let failure = viewModel.failure {
                    Text(failure.localizedMessageKey)
                        .foregroundStyle(.secondary)
                        .accessibilityIdentifier("settings.failure")
                }
            }
            .navigationTitle("Settings")
            .task {
                await viewModel.load()
            }
            .confirmationDialog(
                "Call your configured number now?",
                isPresented: $showingCallConfirmation,
                titleVisibility: .visible
            ) {
                Button("Call me now") {
                    Task { await viewModel.callMeNow() }
                }
                .accessibilityIdentifier("settings.callConfirm")
                Button("Cancel", role: .cancel) {}
            }
            .confirmationDialog(
                "Delete your Life Manager account?",
                isPresented: $showingDeleteConfirmation,
                titleVisibility: .visible
            ) {
                Button("Delete account", role: .destructive) {
                    Task { await viewModel.deleteAccount() }
                }
                .accessibilityIdentifier("settings.deletionConfirm")
                Button("Cancel", role: .cancel) {}
            }
        }
    }

    private var calendarSection: some View {
        Section("Calendar") {
            Text(calendarStatusText)
                .accessibilityIdentifier("settings.calendar")
        }
    }

    private var profileSection: some View {
        Section("Profile") {
            TextField("Name", text: $viewModel.name)
                .accessibilityIdentifier("settings.name")
            TextField("Home or usual starting point", text: $viewModel.home)
                .accessibilityIdentifier("settings.home")
            Picker("Product language", selection: $viewModel.productLocale) {
                Text("English").tag(ProductLocale.en)
                Text("日本語").tag(ProductLocale.ja)
            }
            .accessibilityIdentifier("settings.productLocale")
            Button("Save profile") {
                Task { await viewModel.saveProfile() }
            }
            .accessibilityIdentifier("settings.saveProfile")
        }
    }

    private var phoneSection: some View {
        Section("Calls") {
            TextField("Phone number (+country code)", text: $viewModel.phone)
                .keyboardType(.phonePad)
                .accessibilityIdentifier("settings.phone")
            if let phoneValidationError = viewModel.phoneValidationError {
                Text(phoneValidationError)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("settings.phoneError")
            }
            Toggle("Enable calls", isOn: Binding(
                get: { viewModel.callsEnabled },
                set: { value in Task { await viewModel.setCallsEnabled(value) } }
            ))
            .accessibilityIdentifier("settings.callsEnabled")
            if viewModel.callLanguageVisible {
                Picker("Call language", selection: $viewModel.callLanguage) {
                    Text("English").tag(ProductLocale.en)
                    Text("日本語").tag(ProductLocale.ja)
                }
                .accessibilityIdentifier("settings.callLanguage")
                Button("Call me now") {
                    showingCallConfirmation = true
                }
                .accessibilityIdentifier("settings.callMeNow")
                if let receipt = viewModel.callReceipt {
                    VStack(alignment: .leading) {
                        Text(receipt.message ?? receipt.status.rawValue)
                        if let cooldownSeconds = receipt.cooldownSeconds {
                            Text("Cooldown: \(cooldownSeconds)s")
                        }
                        if let dailyRemaining = receipt.dailyRemaining {
                            Text("Calls remaining today: \(dailyRemaining)")
                        }
                    }
                    .accessibilityIdentifier("settings.callReceipt")
                }
            }
        }
    }

    private var subscriptionSection: some View {
        Section("Subscription") {
            Button("Restore purchases") {
                Task { await paywallViewModel?.restorePurchases() }
            }
            .accessibilityIdentifier("settings.restore")
            Text("Route and chat remain available on the free path.")
                .font(.footnote)
        }
    }

    private var accountSection: some View {
        Section("Account") {
            Button("Log out") {
                Task { await viewModel.signOut() }
            }
            .accessibilityIdentifier("settings.logout")
            Button("Delete account", role: .destructive) {
                showingDeleteConfirmation = true
            }
            .accessibilityIdentifier("settings.deleteAccount")
            if let receipt = viewModel.deletionReceipt {
                Text("Deletion receipt: \(receipt.receiptID)")
                    .accessibilityIdentifier("settings.deletionReceipt")
            }
        }
    }

    private var calendarStatusText: String {
        switch viewModel.calendarStatus {
        case .connected: return "Connected"
        case .actionRequired: return "Action required"
        case .error: return "Calendar error"
        case .disconnected: return "Disconnected"
        }
    }
}
