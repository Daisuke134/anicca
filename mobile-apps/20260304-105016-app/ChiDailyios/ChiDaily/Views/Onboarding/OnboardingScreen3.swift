import SwiftUI
import RevenueCat

struct OnboardingScreen3: View {
    let onComplete: () -> Void
    let onSkip: () -> Void

    @Environment(SubscriptionService.self) private var subscriptionService
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        VStack(spacing: Spacing.lg) {
            Spacer()

            Text(NSLocalizedString("Start Your Free Trial", comment: ""))
                .font(.largeTitle).bold()
                .multilineTextAlignment(.center)

            VStack(alignment: .leading, spacing: Spacing.sm) {
                FeatureRow(icon: "checkmark.circle.fill", text: NSLocalizedString("Unlimited daily check-ins", comment: ""))
                FeatureRow(icon: "checkmark.circle.fill", text: NSLocalizedString("On-device AI guidance", comment: ""))
                FeatureRow(icon: "checkmark.circle.fill", text: NSLocalizedString("HealthKit integration", comment: ""))
                FeatureRow(icon: "checkmark.circle.fill", text: NSLocalizedString("English + Japanese", comment: ""))
            }
            .padding(.horizontal, Spacing.lg)

            Spacer()

            VStack(spacing: Spacing.md) {
                if let offering = subscriptionService.currentOffering {
                    if let monthly = offering.monthly {
                        PrimaryButton(
                            title: String(format: NSLocalizedString("Start 7-Day Trial · %@/month", comment: ""), monthly.storeProduct.localizedPriceString)
                        ) {
                            Task { await purchaseMonthly(package: monthly) }
                        }
                        .accessibilityIdentifier("paywall_plan_monthly")
                    }
                    if let annual = offering.annual {
                        SecondaryOutlineButton(
                            title: String(format: NSLocalizedString("%@/year (save 42%%)", comment: ""), annual.storeProduct.localizedPriceString)
                        ) {
                            Task { await purchaseAnnual(package: annual) }
                        }
                        .accessibilityIdentifier("paywall_plan_yearly")
                    }
                } else {
                    PrimaryButton(title: NSLocalizedString("Start 7-Day Free Trial", comment: "")) {
                        onSkip()
                    }
                    .accessibilityIdentifier("paywall_cta")
                }

                Button(NSLocalizedString("Maybe Later", comment: "")) {
                    onSkip()
                }
                .font(.subheadline)
                .foregroundStyle(Color.secondary)
                .accessibilityIdentifier("paywall_skip")

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
                }
            }
            .padding(.horizontal, Spacing.lg)
            .padding(.bottom, Spacing.xl)
        }
        .task {
            await subscriptionService.fetchOfferings()
        }
    }

    private func purchaseMonthly(package: Package) async {
        isLoading = true
        do {
            try await subscriptionService.purchase(package: package)
            onComplete()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    private func purchaseAnnual(package: Package) async {
        isLoading = true
        do {
            try await subscriptionService.purchase(package: package)
            onComplete()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    private func restore() async {
        do {
            try await subscriptionService.restorePurchases()
            if subscriptionService.isProUser { onComplete() }
        } catch {}
    }
}
