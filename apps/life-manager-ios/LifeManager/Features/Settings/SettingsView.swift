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
                    Text(LocalizedStringKey(failure.localizedMessageKey))
                        .foregroundStyle(.secondary)
                        .accessibilityIdentifier("settings.failure")
                }
            }
            .navigationTitle("settings.title")
            .task {
                await viewModel.load()
            }
            .confirmationDialog(
                "settings.callNow",
                isPresented: $showingCallConfirmation,
                titleVisibility: .visible
            ) {
                Button("settings.callNow") {
                    Task { await viewModel.callMeNow() }
                }
                .accessibilityIdentifier("settings.callConfirm")
                Button("settings.cancel", role: .cancel) {}
            }
            .confirmationDialog(
                "settings.deleteAccount",
                isPresented: $showingDeleteConfirmation,
                titleVisibility: .visible
            ) {
                Button("settings.deleteAccount", role: .destructive) {
                    Task { await viewModel.deleteAccount() }
                }
                .accessibilityIdentifier("settings.deletionConfirm")
                Button("settings.cancel", role: .cancel) {}
            }
        }
    }

    private var calendarSection: some View {
        Section("settings.calendar") {
            Text(calendarStatusKey)
                .accessibilityIdentifier("settings.calendar")
        }
    }

    private var profileSection: some View {
        Section("settings.profile") {
            TextField("profile.name", text: $viewModel.name)
                .accessibilityIdentifier("settings.name")
            TextField("settings.home", text: $viewModel.home)
                .accessibilityIdentifier("settings.home")
            Picker("settings.productLanguage", selection: $viewModel.productLocale) {
                Text("settings.english").tag(ProductLocale.en)
                Text("settings.japanese").tag(ProductLocale.ja)
            }
            .accessibilityIdentifier("settings.productLocale")
            Button("settings.save") {
                Task { await viewModel.saveProfile() }
            }
            .accessibilityIdentifier("settings.saveProfile")
        }
    }

    private var phoneSection: some View {
        Section("settings.calls") {
            TextField("settings.phone", text: $viewModel.phone)
                .keyboardType(.phonePad)
                .accessibilityIdentifier("settings.phone")
            if let phoneValidationError = viewModel.phoneValidationError {
                Text(LocalizedStringKey(phoneValidationError))
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("settings.phoneError")
            }
            Toggle("settings.enableCalls", isOn: Binding(
                get: { viewModel.callsEnabled },
                set: { value in Task { await viewModel.setCallsEnabled(value) } }
            ))
            .accessibilityIdentifier("settings.callsEnabled")
            if viewModel.callLanguageVisible {
                Picker("settings.callLanguage", selection: $viewModel.callLanguage) {
                    Text("settings.english").tag(ProductLocale.en)
                    Text("settings.japanese").tag(ProductLocale.ja)
                }
                .accessibilityIdentifier("settings.callLanguage")
                Button("settings.callNow") {
                    showingCallConfirmation = true
                }
                .accessibilityIdentifier("settings.callMeNow")
                if let receipt = viewModel.callReceipt {
                    VStack(alignment: .leading) {
                        if let message = receipt.message {
                            Text(message)
                        } else {
                            Text(callStatusKey(for: receipt.status))
                        }
                        if let cooldownSeconds = receipt.cooldownSeconds {
                            HStack(spacing: 4) {
                                Text("settings.cooldown")
                                Text("\(cooldownSeconds)s")
                            }
                        }
                        if let dailyRemaining = receipt.dailyRemaining {
                            HStack(spacing: 4) {
                                Text("settings.callsRemaining")
                                Text("\(dailyRemaining)")
                            }
                        }
                    }
                    .accessibilityIdentifier("settings.callReceipt")
                }
            }
        }
    }

    private var subscriptionSection: some View {
        Section("settings.subscription") {
            Button("settings.restore") {
                Task { await paywallViewModel?.restorePurchases() }
            }
            .accessibilityIdentifier("settings.restore")
            Text("settings.freePath")
                .font(.footnote)
        }
    }

    private var accountSection: some View {
        Section("settings.account") {
            Button("settings.logout") {
                Task { await viewModel.signOut() }
            }
            .accessibilityIdentifier("settings.logout")
            Button("settings.deleteAccount", role: .destructive) {
                showingDeleteConfirmation = true
            }
            .accessibilityIdentifier("settings.deleteAccount")
            if let receipt = viewModel.deletionReceipt {
                HStack(spacing: 4) {
                    Text("settings.deletionReceipt")
                    Text(receipt.receiptID)
                }
                    .accessibilityIdentifier("settings.deletionReceipt")
            }
        }
    }

    private var calendarStatusKey: LocalizedStringKey {
        switch viewModel.calendarStatus {
        case .connected: return "settings.calendarConnected"
        case .actionRequired: return "settings.calendarActionRequired"
        case .error: return "settings.calendarError"
        case .disconnected: return "settings.calendarDisconnected"
        }
    }

    private func callStatusKey(for status: CallReceiptStatus) -> LocalizedStringKey {
        switch status {
        case .placed: return "settings.callPlaced"
        case .accepted: return "settings.callAccepted"
        case .cooldown: return "settings.callCooldown"
        case .dailyLimit: return "settings.callDailyLimit"
        case .disabled: return "settings.callsDisabled"
        }
    }
}
