import SwiftUI
import RevenueCat

struct PaywallView: View {
    @StateObject private var viewModel: PaywallViewModel
    let onDismiss: () -> Void
    let onPurchaseCompleted: () -> Void

    init(subscriptionService: SubscriptionServiceProtocol, onDismiss: @escaping () -> Void, onPurchaseCompleted: @escaping () -> Void) {
        _viewModel = StateObject(wrappedValue: PaywallViewModel(subscriptionService: subscriptionService))
        self.onDismiss = onDismiss
        self.onPurchaseCompleted = onPurchaseCompleted
    }

    var body: some View {
        ScrollView {
            VStack(spacing: AppSpacing.lg) {
                headerSection
                packagesSection
                purchaseButton
                legalSection
                maybeLaterButton
                restoreButton
                errorSection
            }
            .padding(AppSpacing.lg)
        }
        .accessibilityIdentifier(AccessibilityID.paywallContainer)
        .task { await viewModel.loadOfferings() }
        .onChange(of: viewModel.purchaseCompleted) { completed in
            if completed { onPurchaseCompleted() }
        }
    }

    // MARK: - Sections

    private var headerSection: some View {
        VStack(spacing: AppSpacing.sm) {
            Image(systemName: "crown.fill")
                .font(.system(size: 48))
                .foregroundStyle(AppColors.brandPrimary)

            Text("paywall.title")
                .font(AppTypography.headline1)
                .multilineTextAlignment(.center)

            Text("paywall.subtitle")
                .font(AppTypography.body)
                .foregroundStyle(AppColors.textSecondary)
                .multilineTextAlignment(.center)
        }
    }

    private var packagesSection: some View {
        VStack(spacing: AppSpacing.sm) {
            if viewModel.isLoading {
                ProgressView()
                    .frame(height: 120)
            } else if viewModel.packages.isEmpty {
                emptyPackagesView
            } else {
                ForEach(viewModel.packages, id: \.identifier) { package in
                    PackageCardView(
                        package: package,
                        isSelected: viewModel.selectedPackage?.identifier == package.identifier
                    )
                    .onTapGesture {
                        withAnimation(AppAnimations.cardSelect) {
                            viewModel.selectedPackage = package
                        }
                    }
                }
            }
        }
    }

    private var emptyPackagesView: some View {
        VStack(spacing: AppSpacing.xs) {
            Text("Unable to load subscription options")
                .font(AppTypography.subheadline)
                .foregroundStyle(AppColors.textSecondary)
            Button("Retry") {
                Task { await viewModel.loadOfferings() }
            }
            .font(AppTypography.subheadline)
        }
        .frame(height: 120)
    }

    private var purchaseButton: some View {
        PrimaryButton(
            title: NSLocalizedString("paywall.subscribe", comment: ""),
            action: { Task { await viewModel.purchase() } },
            isLoading: viewModel.isPurchasing,
            isDisabled: viewModel.selectedPackage == nil
        )
        .accessibilityIdentifier(AccessibilityID.paywallSubscribeButton)
    }

    private var maybeLaterButton: some View {
        SecondaryButton(title: NSLocalizedString("paywall.maybe_later", comment: "")) {
            onDismiss()
        }
        .accessibilityIdentifier(AccessibilityID.paywallMaybeLater)
    }

    private var legalSection: some View {
        VStack(spacing: AppSpacing.xxs) {
            Text("paywall.legal.auto_renew")
                .font(AppTypography.caption2)
                .foregroundStyle(AppColors.textTertiary)
                .multilineTextAlignment(.center)

            HStack(spacing: AppSpacing.sm) {
                Link("paywall.legal.terms", destination: URL(string: "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/")!)
                    .font(AppTypography.caption2)

                Text("·")
                    .foregroundStyle(AppColors.textTertiary)

                Link("paywall.legal.privacy", destination: URL(string: "https://aniccaai.com/privacy")!)
                    .font(AppTypography.caption2)
            }
        }
    }

    private var restoreButton: some View {
        Button {
            Task { await viewModel.restore() }
        } label: {
            Text("paywall.restore")
                .font(AppTypography.caption2)
                .foregroundStyle(AppColors.textTertiary)
        }
        .accessibilityIdentifier(AccessibilityID.paywallRestore)
    }

    private var errorSection: some View {
        Group {
            if let error = viewModel.errorMessage {
                Text(error)
                    .font(AppTypography.caption1)
                    .foregroundStyle(AppColors.brandDanger)
                    .multilineTextAlignment(.center)
            }
        }
    }
}

// MARK: - PackageCardView

struct PackageCardView: View {
    let package: Package
    let isSelected: Bool

    private var isAnnual: Bool {
        package.packageType == .annual
    }

    private var packageAccessibilityID: String {
        switch package.packageType {
        case .annual: return AccessibilityID.paywallPackageAnnual
        case .monthly: return AccessibilityID.paywallPackageMonthly
        case .weekly: return AccessibilityID.paywallPackageWeekly
        default: return "paywall_package_\(package.identifier)"
        }
    }

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: AppSpacing.xxs) {
                HStack {
                    Text(package.storeProduct.localizedTitle)
                        .font(AppTypography.headline3)
                    if isAnnual {
                        Text("BEST VALUE")
                            .font(AppTypography.caption2.bold())
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(AppColors.brandSecondary)
                            .foregroundStyle(.white)
                            .clipShape(RoundedRectangle(cornerRadius: 4))
                    }
                }
                Text(package.localizedPriceString)
                    .font(AppTypography.subheadline)
                    .foregroundStyle(AppColors.textSecondary)
                if let intro = package.storeProduct.introductoryDiscount {
                    Text("\(intro.subscriptionPeriod.value)-day free trial")
                        .font(AppTypography.caption1)
                        .foregroundStyle(AppColors.textSecondary)
                }
            }
            Spacer()
            Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                .font(.title2)
                .foregroundStyle(isSelected ? AppColors.brandPrimary : AppColors.textSecondary)
        }
        .padding(AppSpacing.md)
        .background(
            RoundedRectangle(cornerRadius: AppCornerRadius.lg)
                .stroke(isSelected ? AppColors.brandPrimary : AppColors.textTertiary, lineWidth: isSelected ? 2 : 1)
        )
        .scaleEffect(isSelected ? 1.02 : 1.0)
        .animation(AppAnimations.cardSelect, value: isSelected)
        .accessibilityIdentifier(packageAccessibilityID)
    }
}
