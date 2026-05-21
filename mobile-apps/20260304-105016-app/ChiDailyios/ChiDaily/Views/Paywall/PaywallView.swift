import SwiftUI
import RevenueCat

struct PaywallView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(SubscriptionService.self) private var subscriptionService
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: Spacing.lg) {
                    headerSection
                    featuresSection
                    Spacer(minLength: Spacing.lg)
                    purchaseSection
                }
                .padding(.horizontal, Spacing.lg)
                .padding(.top, Spacing.xl)
            }
            .navigationTitle(NSLocalizedString("Start Your Free Trial", comment: ""))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(NSLocalizedString("Maybe Later", comment: "")) {
                        dismiss()
                    }
                    .accessibilityIdentifier("paywall_skip")
                }
            }
        }
        .task {
            await subscriptionService.fetchOfferings()
        }
    }

    private var headerSection: some View {
        VStack(spacing: Spacing.md) {
            Image(systemName: "leaf.circle.fill")
                .font(.system(size: 64))
                .foregroundStyle(Color.chiAccent)
            Text(NSLocalizedString("Unlock Chi Daily Premium", comment: ""))
                .font(.largeTitle).bold()
                .multilineTextAlignment(.center)
            Text(NSLocalizedString("Start a 7-day free trial. Cancel anytime.", comment: ""))
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
    }

    private var featuresSection: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            FeatureRow(icon: "checkmark.circle.fill", text: NSLocalizedString("Unlimited daily check-ins", comment: ""))
            FeatureRow(icon: "checkmark.circle.fill", text: NSLocalizedString("On-device AI guidance", comment: ""))
            FeatureRow(icon: "checkmark.circle.fill", text: NSLocalizedString("HealthKit integration", comment: ""))
            FeatureRow(icon: "checkmark.circle.fill", text: NSLocalizedString("English + Japanese", comment: ""))
        }
    }

    private var purchaseSection: some View {
        VStack(spacing: Spacing.md) {
            if let offering = subscriptionService.currentOffering {
                if let monthly = offering.monthly {
                    PrimaryButton(
                        title: String(format: NSLocalizedString("Start 7-Day Trial · %@/month", comment: ""), monthly.storeProduct.localizedPriceString)
                    ) {
                        Task { await purchasePackage(monthly) }
                    }
                    .accessibilityIdentifier("paywall_cta")
                    .accessibilityElement(children: .combine)
                } else {
                    PrimaryButton(title: NSLocalizedString("Start 7-Day Free Trial", comment: "")) {
                        if let pkg = offering.availablePackages.first {
                            Task { await purchasePackage(pkg) }
                        }
                    }
                    .accessibilityIdentifier("paywall_cta")
                }

                if let annual = offering.annual {
                    SecondaryOutlineButton(
                        title: String(format: NSLocalizedString("%@/year (save 42%%)", comment: ""), annual.storeProduct.localizedPriceString)
                    ) {
                        Task { await purchasePackage(annual) }
                    }
                    .accessibilityIdentifier("paywall_plan_yearly")
                }
            } else {
                ProgressView()
                    .padding()
            }

            Button(NSLocalizedString("Restore Purchases", comment: "")) {
                Task { await restore() }
            }
            .font(.caption)
            .foregroundStyle(Color.secondary)
            .accessibilityIdentifier("paywall_restore")

            if let errorMessage = errorMessage {
                Text(errorMessage)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .multilineTextAlignment(.center)
            }
        }
        .padding(.bottom, Spacing.xl)
    }

    private func purchasePackage(_ package: Package) async {
        isLoading = true
        errorMessage = nil
        do {
            try await subscriptionService.purchase(package: package)
            dismiss()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    private func restore() async {
        do {
            try await subscriptionService.restorePurchases()
            if subscriptionService.isProUser { dismiss() }
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
