import SwiftUI
import RevenueCat

struct BenefitRow: View {
    let text: String

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: "checkmark.circle.fill")
                .foregroundColor(.green)
            Text(text)
                .font(.body)
        }
    }
}

struct PaywallView: View {
    @Environment(AppState.self) private var appState
    @State private var offerings: Offerings?
    @State private var isPurchasing = false
    @State private var errorMessage: String?
    let onDismiss: () -> Void

    var body: some View {
        VStack(spacing: 24) {
            Text(String(localized: "Unlock Your Full Stretch Routine"))
                .font(.title)
                .bold()
                .multilineTextAlignment(.center)

            VStack(alignment: .leading, spacing: 12) {
                BenefitRow(text: String(localized: "Unlimited stretches"))
                BenefitRow(text: String(localized: "AI-personalized routines"))
                BenefitRow(text: String(localized: "All pain areas"))
                BenefitRow(text: String(localized: "Custom schedules"))
                BenefitRow(text: String(localized: "Progress tracking"))
            }

            Spacer()

            if let offering = offerings?.current {
                if let annual = offering.annual {
                    PrimaryButton(title: String(localized: "Annual \(annual.localizedPriceString)/yr")) {
                        Task { await purchase(annual) }
                    }
                    .accessibilityIdentifier("paywall_plan_yearly")
                }
                if let monthly = offering.monthly {
                    SecondaryButton(title: String(localized: "Monthly \(monthly.localizedPriceString)/mo")) {
                        Task { await purchase(monthly) }
                    }
                    .accessibilityIdentifier("paywall_plan_monthly")
                }
            } else {
                ProgressView()
            }

            if let errorMessage {
                Text(errorMessage)
                    .font(.caption)
                    .foregroundColor(.red)
            }

            Text(String(localized: "7-day free trial"))
                .font(.footnote)
                .foregroundColor(.secondary)
                .accessibilityIdentifier("paywall_cta")

            HStack {
                Button(String(localized: "Maybe Later")) { onDismiss() }
                    .font(.subheadline)
                    .accessibilityIdentifier("paywall_skip")

                Spacer()

                Button(String(localized: "Restore")) {
                    Task { await restore() }
                }
                .font(.subheadline)
                .accessibilityIdentifier("paywall_restore")
            }

            HStack {
                Link(String(localized: "Terms"), destination: URL(string: "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/")!)
                Text("·")
                Link(String(localized: "Privacy"), destination: URL(string: "https://aniccaai.com/privacy")!)
            }
            .font(.caption)
            .foregroundColor(.secondary)
        }
        .padding(.horizontal, 24)
        .padding(.vertical, 32)
        .task { await loadOfferings() }
    }

    private func loadOfferings() async {
        offerings = await SubscriptionService.shared.getOfferings()
    }

    private func purchase(_ package: Package) async {
        isPurchasing = true
        errorMessage = nil
        defer { isPurchasing = false }
        do {
            let success = try await SubscriptionService.shared.purchase(package: package)
            if success {
                appState.isPremium = true
                onDismiss()
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func restore() async {
        errorMessage = nil
        do {
            let success = try await SubscriptionService.shared.restorePurchases()
            if success {
                appState.isPremium = true
                onDismiss()
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
