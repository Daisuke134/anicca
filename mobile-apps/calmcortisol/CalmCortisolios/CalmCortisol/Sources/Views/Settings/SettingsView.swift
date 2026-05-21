import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var subscriptionManager: SubscriptionManager
    @State private var showPaywall = false

    private let privacyURLEN = "https://aniccaai.com/calmcortisol/privacy/en"
    private let privacyURLJA = "https://aniccaai.com/calmcortisol/privacy/ja"
    private let termsURL = "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/"

    private var privacyURL: String {
        L10n.isJapaneseLang ? privacyURLJA : privacyURLEN
    }

    var body: some View {
        NavigationView {
            ZStack {
                Color(hex: "#0f0f1a").ignoresSafeArea()

                Form {
                    Section {
                        if !subscriptionManager.isPro {
                            Button {
                                showPaywall = true
                            } label: {
                                HStack {
                                    Image(systemName: "star.fill")
                                        .foregroundColor(Color(hex: "#2dd4bf"))
                                    Text(L10n.isJapaneseLang ? "Proにアップグレード" : "Upgrade to Pro")
                                        .foregroundColor(Color(hex: "#2dd4bf"))
                                }
                            }
                        }

                        Button {
                            subscriptionManager.restore()
                        } label: {
                            HStack {
                                Image(systemName: "arrow.clockwise")
                                Text(L10n.settingsRestore)
                            }
                            .foregroundColor(.white)
                        }
                        .accessibilityIdentifier("settings-restore")
                    }

                    Section {
                        if let url = URL(string: privacyURL) {
                            Link(destination: url) {
                                HStack {
                                    Image(systemName: "hand.raised.fill")
                                    Text(L10n.settingsPrivacyPolicy)
                                }
                                .foregroundColor(.white)
                            }
                            .accessibilityIdentifier("settings-privacy")
                        }

                        if let url = URL(string: termsURL) {
                            Link(destination: url) {
                                HStack {
                                    Image(systemName: "doc.text.fill")
                                    Text(L10n.settingsTerms)
                                }
                                .foregroundColor(.white)
                            }
                            .accessibilityIdentifier("settings-terms")
                        }
                    }

                    Section {
                        HStack {
                            Text(L10n.settingsVersion)
                                .foregroundColor(Color(hex: "#9ca3af"))
                            Spacer()
                            Text(Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0.0")
                                .foregroundColor(Color(hex: "#6b7280"))
                        }
                    }
                }
            }
            .navigationTitle(L10n.settingsTitle)
            .sheet(isPresented: $showPaywall) {
                PaywallView(isOnboarding: false)
                    .environmentObject(subscriptionManager)
            }
        }
    }
}
