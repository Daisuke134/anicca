import SwiftUI
import RevenueCat

struct PaywallView: View {
    var isOnboarding: Bool
    var onDismiss: () -> Void

    @State private var viewModel = PaywallViewModel()

    var body: some View {
        ScrollView {
            VStack(spacing: Theme.Spacing.lg) {
                // Close button (Maybe Later)
                if !isOnboarding {
                    HStack {
                        Spacer()
                        Button(action: onDismiss) {
                            Image(systemName: "xmark.circle.fill")
                                .font(.title2)
                                .foregroundStyle(Theme.Colors.secondaryLabel)
                        }
                        .accessibilityIdentifier(AccessibilityID.paywallMaybeLater)
                    }
                    .padding(.horizontal, Theme.Spacing.lg)
                    .padding(.top, Theme.Spacing.sm)
                }

                // Value Headline
                VStack(spacing: Theme.Spacing.xs) {
                    Image(systemName: "snowflake")
                        .font(.system(size: 48))
                        .foregroundStyle(Theme.Colors.accent)

                    Text("Unlock Your Full Cold Potential")
                        .font(Theme.Typography.title2)
                        .multilineTextAlignment(.center)
                        .foregroundStyle(Theme.Colors.label)
                        .accessibilityIdentifier(AccessibilityID.paywallHeadline)
                }
                .padding(.top, isOnboarding ? Theme.Spacing.xxl : Theme.Spacing.sm)

                // Benefit bullets
                VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
                    benefitRow(icon: "heart.fill", text: "Live heart rate monitoring", color: Theme.Colors.hot)
                    benefitRow(icon: "chart.bar.fill", text: "Unlimited session history", color: Theme.Colors.accent)
                    benefitRow(icon: "figure.strengthtraining.traditional", text: "Custom plunge protocols", color: Theme.Colors.success)
                    benefitRow(icon: "flame.fill", text: "Streak tracking & freeze", color: Theme.Colors.warning)
                    benefitRow(icon: "thermometer.snowflake", text: "Contrast therapy timer", color: Theme.Colors.cold)
                }
                .padding(.horizontal, Theme.Spacing.xl)

                // Social proof
                VStack(spacing: Theme.Spacing.xxs) {
                    HStack(spacing: 2) {
                        ForEach(0..<5, id: \.self) { _ in
                            Image(systemName: "star.fill")
                                .foregroundStyle(Theme.Colors.warning)
                                .font(.caption)
                        }
                    }
                    Text("Join 1,000+ cold plungers")
                        .font(Theme.Typography.caption)
                        .foregroundStyle(Theme.Colors.secondaryLabel)
                }

                // Pricing grid (3 plans)
                if viewModel.packages.isEmpty && !viewModel.isLoading {
                    staticPricingGrid()
                } else {
                    dynamicPricingGrid()
                }

                // Error message
                if let error = viewModel.errorMessage {
                    Text(error)
                        .font(Theme.Typography.caption)
                        .foregroundStyle(Theme.Colors.destructive)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, Theme.Spacing.lg)
                }

                // CTA button
                Button(action: {
                    Task { await viewModel.purchase() }
                }) {
                    if viewModel.isLoading {
                        ProgressView()
                            .tint(.white)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, Theme.Spacing.md)
                    } else {
                        Text("Start My Cold Journey")
                            .font(Theme.Typography.headline)
                            .foregroundStyle(.white)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, Theme.Spacing.md)
                    }
                }
                .background(Theme.Colors.primary)
                .clipShape(RoundedRectangle(cornerRadius: Theme.CornerRadius.medium))
                .disabled(viewModel.isLoading)
                .accessibilityIdentifier(AccessibilityID.paywallCta)
                .padding(.horizontal, Theme.Spacing.lg)
                .animation(Theme.Animation.spring, value: viewModel.isLoading)

                // Maybe Later (onboarding only)
                if isOnboarding {
                    Button(action: onDismiss) {
                        Text("Maybe Later")
                            .font(Theme.Typography.subheadline)
                            .foregroundStyle(Theme.Colors.secondaryLabel)
                    }
                    .accessibilityIdentifier(AccessibilityID.paywallMaybeLater)
                }

                // FAQ section
                VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
                    faqItem(q: "Can I cancel anytime?", a: "Yes. Cancel through your Apple ID settings. No penalties.")
                    faqItem(q: "Will I be charged immediately?", a: "Your subscription begins after confirmation. You can cancel before the first billing cycle.")
                    faqItem(q: "What's included in Premium?", a: "Heart rate tracking, unlimited history, custom protocols, streak tracking, and contrast therapy timer.")
                }
                .padding(.horizontal, Theme.Spacing.lg)

                // Legal + Restore
                VStack(spacing: Theme.Spacing.xs) {
                    Button(action: {
                        Task { await viewModel.restore() }
                    }) {
                        Text("Restore Purchases")
                            .font(Theme.Typography.footnote)
                            .foregroundStyle(Theme.Colors.secondaryLabel)
                    }
                    .accessibilityIdentifier(AccessibilityID.paywallRestore)

                    HStack(spacing: Theme.Spacing.xs) {
                        if let privacyURL = URL(string: "https://aniccaai.com/privacy") {
                            Link("Privacy Policy", destination: privacyURL)
                                .font(Theme.Typography.footnote)
                                .foregroundStyle(Theme.Colors.secondaryLabel)
                        }
                        Text("·")
                            .foregroundStyle(Theme.Colors.secondaryLabel)
                        if let termsURL = URL(string: "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/") {
                            Link("Terms of Use", destination: termsURL)
                                .font(Theme.Typography.footnote)
                                .foregroundStyle(Theme.Colors.secondaryLabel)
                        }
                    }
                }
                .padding(.bottom, Theme.Spacing.xl)
            }
        }
        .accessibilityIdentifier(AccessibilityID.paywallView)
        .task { await viewModel.loadOfferings() }
        .onChange(of: viewModel.isPurchased) { _, purchased in
            if purchased { onDismiss() }
        }
    }

    // MARK: - Static Pricing (fallback when packages not loaded)

    private func staticPricingGrid() -> some View {
        HStack(spacing: Theme.Spacing.sm) {
            pricingCard(
                title: "Weekly",
                price: "$1.99",
                period: "/week",
                badge: nil,
                isSelected: viewModel.selectedPlanIndex == 0,
                id: AccessibilityID.paywallPlanWeekly
            ) { viewModel.selectPlan(at: 0) }

            pricingCard(
                title: "Monthly",
                price: "$6.99",
                period: "/month",
                badge: nil,
                isSelected: viewModel.selectedPlanIndex == 1,
                id: AccessibilityID.paywallPlanMonthly
            ) { viewModel.selectPlan(at: 1) }

            pricingCard(
                title: "Annual",
                price: "$29.99",
                period: "/year",
                badge: "Save 64%",
                isSelected: viewModel.selectedPlanIndex == 2,
                id: AccessibilityID.paywallPlanAnnual
            ) { viewModel.selectPlan(at: 2) }
        }
        .padding(.horizontal, Theme.Spacing.lg)
    }

    // MARK: - Dynamic Pricing (from RevenueCat)

    private func dynamicPricingGrid() -> some View {
        HStack(spacing: Theme.Spacing.sm) {
            ForEach(Array(viewModel.packages.enumerated()), id: \.offset) { index, pkg in
                let isAnnual = pkg.packageType == .annual
                pricingCard(
                    title: pkg.packageType.displayName,
                    price: pkg.localizedPriceString,
                    period: pkg.packageType.periodSuffix,
                    badge: isAnnual ? "Best Value" : nil,
                    isSelected: viewModel.selectedPlanIndex == index,
                    id: accessibilityIdForPlan(index)
                ) { viewModel.selectPlan(at: index) }
            }
        }
        .padding(.horizontal, Theme.Spacing.lg)
    }

    // MARK: - Components

    private func pricingCard(title: String, price: String, period: String, badge: String?, isSelected: Bool, id: String, onTap: @escaping () -> Void) -> some View {
        Button(action: onTap) {
            VStack(spacing: Theme.Spacing.xs) {
                if let badge {
                    Text(badge)
                        .font(Theme.Typography.caption)
                        .foregroundStyle(.white)
                        .padding(.horizontal, Theme.Spacing.xs)
                        .padding(.vertical, Theme.Spacing.xxs)
                        .background(Theme.Colors.hot)
                        .clipShape(RoundedRectangle(cornerRadius: Theme.CornerRadius.small))
                } else {
                    Text(" ")
                        .font(Theme.Typography.caption)
                        .padding(.vertical, Theme.Spacing.xxs)
                }

                Text(title)
                    .font(Theme.Typography.subheadline)
                    .foregroundStyle(Theme.Colors.label)

                Text(price)
                    .font(Theme.Typography.title3)
                    .foregroundStyle(Theme.Colors.label)

                Text(period)
                    .font(Theme.Typography.caption)
                    .foregroundStyle(Theme.Colors.secondaryLabel)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, Theme.Spacing.md)
            .background(
                RoundedRectangle(cornerRadius: Theme.CornerRadius.medium)
                    .stroke(isSelected ? Theme.Colors.accent : Theme.Colors.secondaryLabel.opacity(0.3), lineWidth: isSelected ? 2 : 1)
            )
            .background(
                RoundedRectangle(cornerRadius: Theme.CornerRadius.medium)
                    .fill(isSelected ? Theme.Colors.accent.opacity(0.08) : Color.clear)
            )
        }
        .accessibilityIdentifier(id)
    }

    private func benefitRow(icon: String, text: String, color: Color) -> some View {
        HStack(spacing: Theme.Spacing.sm) {
            Image(systemName: icon)
                .foregroundStyle(color)
                .frame(width: 24)
            Text(text)
                .font(Theme.Typography.body)
                .foregroundStyle(Theme.Colors.label)
        }
    }

    private func faqItem(q: String, a: String) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.xxs) {
            Text(q)
                .font(Theme.Typography.subheadline)
                .fontWeight(.semibold)
                .foregroundStyle(Theme.Colors.label)
            Text(a)
                .font(Theme.Typography.caption)
                .foregroundStyle(Theme.Colors.secondaryLabel)
        }
    }

    private func accessibilityIdForPlan(_ index: Int) -> String {
        switch index {
        case 0: return AccessibilityID.paywallPlanWeekly
        case 1: return AccessibilityID.paywallPlanMonthly
        default: return AccessibilityID.paywallPlanAnnual
        }
    }
}

// MARK: - PackageType Extensions

private extension PackageType {
    var displayName: String {
        switch self {
        case .weekly: return "Weekly"
        case .monthly: return "Monthly"
        case .annual: return "Annual"
        default: return "Plan"
        }
    }

    var periodSuffix: String {
        switch self {
        case .weekly: return "/week"
        case .monthly: return "/month"
        case .annual: return "/year"
        default: return ""
        }
    }
}
