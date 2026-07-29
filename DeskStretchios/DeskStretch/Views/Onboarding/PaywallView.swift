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

/// Explicit paywall states. There is deliberately no state in which the view
/// shows a spinner forever: every load either resolves to `.ready` or `.unavailable`.
enum PaywallLoadState {
    case loading
    case ready([Package])
    case unavailable(String)
}

struct PaywallView: View {
    @Environment(AppState.self) private var appState
    @State private var loadState: PaywallLoadState = .loading
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

            planSection

            if let errorMessage {
                Text(errorMessage)
                    .font(.caption)
                    .foregroundColor(.red)
                    .multilineTextAlignment(.center)
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
        .disabled(isPurchasing)
        .task { await loadPackages() }
    }

    @ViewBuilder
    private var planSection: some View {
        switch loadState {
        case .loading:
            ProgressView()
                .accessibilityIdentifier("paywall_loading")

        case .ready(let packages):
            VStack(spacing: 12) {
                ForEach(packages, id: \.identifier) { package in
                    planButton(for: package)
                }
            }

        case .unavailable(let message):
            VStack(spacing: 12) {
                Text(message)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                PrimaryButton(title: String(localized: "Try Again")) {
                    Task { await loadPackages() }
                }
                .accessibilityIdentifier("paywall_retry")
            }
            .accessibilityIdentifier("paywall_unavailable")
        }
    }

    @ViewBuilder
    private func planButton(for package: Package) -> some View {
        let price = package.storeProduct.localizedPriceString

        if package.packageType == .monthly {
            SecondaryButton(title: String(localized: "Monthly \(price)/mo")) {
                Task { await purchase(package) }
            }
            .accessibilityIdentifier("paywall_plan_monthly")
        } else {
            PrimaryButton(title: String(localized: "Annual \(price)/yr")) {
                Task { await purchase(package) }
            }
            .accessibilityIdentifier("paywall_plan_yearly")
        }
    }

    private func loadPackages() async {
        loadState = .loading
        errorMessage = nil
        do {
            let packages = try await SubscriptionService.shared.loadAvailablePackages()
            loadState = .ready(packages)
        } catch {
            loadState = .unavailable(error.localizedDescription)
        }
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
            } else {
                errorMessage = String(localized: "No previous purchases found.")
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
