import SwiftUI
import RevenueCat

struct SettingsView: View {
    @Bindable var viewModel: AppViewModel
    @State private var notificationService = NotificationService()
    @State private var showPaywall: Bool = false

    private var language: AppLanguage { viewModel.language }

    var body: some View {
        NavigationStack {
            Form {
                Section(L10n.notifications(language)) {
                    DatePicker(
                        L10n.morningReminder(language),
                        selection: $notificationService.morningTime,
                        displayedComponents: .hourAndMinute
                    )

                    DatePicker(
                        L10n.eveningReminder(language),
                        selection: $notificationService.eveningTime,
                        displayedComponents: .hourAndMinute
                    )
                }

                Section(L10n.subscriptionSection(language)) {
                    Button {
                        showPaywall = true
                    } label: {
                        HStack {
                            Text(L10n.manageSubscription(language))
                            Spacer()
                            if viewModel.isPro {
                                Text("PRO")
                                    .font(.caption.bold())
                                    .foregroundStyle(.white)
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 3)
                                    .background(Color(red: 0.49, green: 0.71, blue: 0.62))
                                    .clipShape(.rect(cornerRadius: 6))
                            }
                        }
                    }

                    Button(L10n.restorePurchase(language)) {
                        Task { await restorePurchases() }
                    }
                }

                Section(L10n.about(language)) {
                    HStack {
                        Text(L10n.appVersion(language))
                        Spacer()
                        Text("1.0.0")
                            .foregroundStyle(.secondary)
                    }
                    Link(L10n.privacyPolicy(language), destination: URL(string: "https://aniccaai.com/privacy")!)
                    Link(L10n.termsOfUse(language), destination: URL(string: "https://aniccaai.com/terms")!)
                }
            }
            .navigationTitle(L10n.settingsTab(language))
            .navigationBarTitleDisplayMode(.large)
            .onChange(of: notificationService.morningTime) { _, _ in
                scheduleNotifications()
            }
            .onChange(of: notificationService.eveningTime) { _, _ in
                scheduleNotifications()
            }
            .task {
                await notificationService.requestPermission()
            }
            .fullScreenCover(isPresented: $showPaywall) {
                PaywallView(language: language, onDismiss: { showPaywall = false }, onPurchaseSuccess: {
                    viewModel.isPro = true
                    showPaywall = false
                })
            }
        }
    }

    private func scheduleNotifications() {
        notificationService.scheduleNotifications(language: language)
    }

    private func restorePurchases() async {
        guard RevenueCat.Purchases.isConfigured else { return }
        do {
            let info = try await RevenueCat.Purchases.shared.restorePurchases()
            if info.entitlements["pro"]?.isActive == true {
                viewModel.isPro = true
            }
        } catch {
            // Silently fail
        }
    }
}
