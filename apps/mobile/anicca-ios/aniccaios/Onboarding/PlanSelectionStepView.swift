import SwiftUI
import RevenueCat

/// Phase 5: CONVERT — Step 3: Custom paywall with RevenueCat packages.
struct PlanSelectionStepView: View {
    let onPurchaseSuccess: (CustomerInfo) -> Void
    let onDismiss: () -> Void
    let variant: String

    @EnvironmentObject private var appState: AppState
    @State private var selectedPackage: Package?
    @State private var isPurchasing = false
    @State private var errorMessage: String?
    @State private var hasTracked = false
    @State private var hasShownRetention = false
    @State private var showRetention = false

    private var offering: Offering? {
        appState.cachedOffering
    }

    private var packages: [Package] {
        offering?.availablePackages ?? []
    }

    private var yearlyPackage: Package? {
        packages.first { $0.packageType == .annual }
    }

    private var monthlyPackage: Package? {
        packages.first { $0.packageType == .monthly }
    }

    /// This legacy screen keeps its former fallback behavior until experiments are configured.
    private var isHardPaywall: Bool {
        false
    }

    /// The active soft-paywall close button is owned by PaywallFlowContainer.
    private var showXButton: Bool {
        false
    }

    /// F6: Dynamic save percentage
    private var savePct: Int? {
        guard let yearly = yearlyPackage, let monthly = monthlyPackage else { return nil }
        let yearlyPrice = (yearly.storeProduct.price as NSDecimalNumber).doubleValue
        let monthlyPrice = (monthly.storeProduct.price as NSDecimalNumber).doubleValue
        guard monthlyPrice > 0 else { return nil }
        return Int((1.0 - yearlyPrice / (monthlyPrice * 12.0)) * 100)
    }

    var body: some View {
        VStack(spacing: 16) {
            if showXButton {
                HStack {
                    Spacer()
                    Button {
                        onDismiss()
                    } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 16, weight: .medium))
                            .foregroundStyle(.secondary)
                            .frame(width: 32, height: 32)
                    }
                    .accessibilityIdentifier("paywall-dismiss")
                    .padding(.trailing, 16)
                    .padding(.top, 8)
                }
            }

            // F4: Fixed outcome-focused title
            Text(paywallText("title", fallback: "paywall_plan_title"))
                .font(.system(size: 28, weight: .bold))
                .foregroundStyle(AppTheme.Colors.label)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 24)

            // F7: Subtitle + feature list
            Text(paywallText("subtitle", fallback: "paywall_plan_subtitle"))
                .font(.system(size: 16))
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 24)

            VStack(alignment: .leading, spacing: 8) {
                featureRow(icon: "checkmark.circle.fill", text: paywallText("feature1", fallback: "paywall_plan_feature_access"))
                featureRow(icon: "bell.badge.fill", text: paywallText("feature2", fallback: "paywall_plan_feature_nudges"))
                featureRow(icon: "xmark.circle", text: paywallText("feature3", fallback: "paywall_plan_feature_cancel"))
            }
            .padding(.horizontal, 32)

            if packages.isEmpty {
                ProgressView()
                    .padding(.top, 40)
                Spacer()
            } else {
                ScrollView {
                    VStack(spacing: 12) {
                        if let yearly = yearlyPackage {
                            let priceStr = String(format: NSLocalizedString("paywall_plan_price_yearly", comment: ""), yearly.localizedPriceString)
                            let saveStr: String? = savePct.map { String(format: NSLocalizedString("paywall_plan_save_dynamic", comment: ""), $0) }
                            planCard(
                                package: yearly,
                                title: yearly.storeProduct.localizedTitle,
                                priceLabel: priceStr,
                                badge: String(localized: "paywall_plan_yearly_badge"),
                                saveLabel: saveStr
                            )
                        }

                        if let monthly = monthlyPackage {
                            let priceStr = String(format: NSLocalizedString("paywall_plan_price_monthly", comment: ""), monthly.localizedPriceString)
                            planCard(
                                package: monthly,
                                title: monthly.storeProduct.localizedTitle,
                                priceLabel: priceStr,
                                badge: nil,
                                saveLabel: nil
                            )
                        }
                    }
                    .padding(.horizontal, 24)
                    .padding(.top, 16)
                }

                if let errorMessage {
                    Text(errorMessage)
                        .font(.caption)
                        .foregroundStyle(.red)
                        .padding(.horizontal, 24)
                }

                VStack(spacing: 12) {
                    Button {
                        purchase()
                    } label: {
                        Group {
                            if isPurchasing {
                                ProgressView()
                                    .tint(.white)
                            } else {
                                let hasTrialEligibility = selectedPackage?.storeProduct.introductoryDiscount != nil
                                Text(paywallText("cta", fallback: hasTrialEligibility ? "paywall_plan_cta_trial" : "paywall_plan_cta_no_trial"))
                            }
                        }
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .frame(height: 56)
                        .background(selectedPackage != nil ? AppTheme.Colors.accent : AppTheme.Colors.accent.opacity(0.5))
                        .clipShape(RoundedRectangle(cornerRadius: 28))
                    }
                    .disabled(selectedPackage == nil || isPurchasing)
                    .accessibilityIdentifier("paywall-plan-cta")
                    .padding(.horizontal, 24)

                    Text(paywallText("trust", fallback: "paywall_plan_trust"))
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)

                    Text(paywallText("review", fallback: "paywall_plan_review"))
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(.secondary)
                        .italic()
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 24)

                    HStack(spacing: 24) {
                        if !isHardPaywall {
                            Button(String(localized: "paywall_plan_maybe_later")) {
                                onDismiss()
                            }
                            .font(.system(size: 14, weight: .medium))
                            .foregroundStyle(.secondary)
                            .accessibilityIdentifier("paywall-maybe-later")
                        }

                        Button(String(localized: "paywall_plan_restore")) {
                            restorePurchases()
                        }
                        .font(.system(size: 14, weight: .medium))
                        .foregroundStyle(.secondary)
                        .accessibilityIdentifier("paywall-restore")
                    }

                    HStack(spacing: 8) {
                        Link(String(localized: "paywall_plan_terms"), destination: AppConfig.termsURL)
                        Text("·").foregroundStyle(.secondary)
                        Link(String(localized: "paywall_plan_privacy"), destination: AppConfig.privacyURL)
                    }
                    .font(.system(size: 12))
                    .foregroundStyle(.secondary)
                }
                .padding(.bottom, 32)
            }
        }
        .background(AppBackground())
        .analyticsScreen(.paywall, flowID: "legacy_paywall")
        .onAppear {
            if !hasTracked {
                hasTracked = true
                AnalyticsManager.shared.track(.paywallPlanSelectionViewed, properties: ["presentation_variant": variant])
            }
            // Default to yearly
            if selectedPackage == nil {
                selectedPackage = yearlyPackage ?? monthlyPackage
            }
        }
        .sheet(isPresented: $showRetention) {
            RetentionOfferSheet(flowID: "legacy_paywall") { customerInfo in
                showRetention = false
                onPurchaseSuccess(customerInfo)
            }
        }
    }

    @ViewBuilder
    private func featureRow(icon: String, text: String) -> some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 16))
                .foregroundStyle(AppTheme.Colors.accent)
                .frame(width: 24)
            Text(text)
                .font(.system(size: 14, weight: .medium))
                .foregroundStyle(AppTheme.Colors.label)
        }
    }

    @ViewBuilder
    private func planCard(
        package: Package,
        title: String,
        priceLabel: String,
        badge: String?,
        saveLabel: String?
    ) -> some View {
        let isSelected = selectedPackage?.identifier == package.identifier

        Button {
            selectedPackage = package
            AnalyticsManager.shared.track(.productSelected, properties: [
                "product_id": package.storeProduct.productIdentifier,
                "offering_id": offering?.identifier ?? "unknown",
                "source": "legacy_paywall",
            ])
        } label: {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 8) {
                        Text(title)
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(AppTheme.Colors.label)

                        if let badge {
                            Text(badge)
                                .font(.system(size: 10, weight: .bold))
                                .foregroundStyle(.white)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 3)
                                .background(AppTheme.Colors.accent)
                                .clipShape(Capsule())
                        }
                    }

                    HStack(spacing: 8) {
                        Text(priceLabel)
                            .font(.system(size: 14))
                            .foregroundStyle(.secondary)

                        if let saveLabel {
                            Text(saveLabel)
                                .font(.system(size: 12, weight: .semibold))
                                .foregroundStyle(AppTheme.Colors.accent)
                        }
                    }
                }

                Spacer()

                Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                    .font(.system(size: 24))
                    .foregroundStyle(isSelected ? AppTheme.Colors.accent : .secondary)
            }
            .padding(16)
            .background(isSelected ? AppTheme.Colors.accent.opacity(0.1) : AppTheme.Colors.buttonUnselected)
            .clipShape(RoundedRectangle(cornerRadius: 16))
            .overlay(
                RoundedRectangle(cornerRadius: 16)
                    .stroke(isSelected ? AppTheme.Colors.accent : Color.clear, lineWidth: 2)
            )
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("paywall-plan-\(package.packageType.rawValue)")
    }

    private func paywallText(_ key: String, fallback: String) -> String {
        return String(localized: String.LocalizationValue(fallback))
    }

    private func purchase() {
        guard let package = selectedPackage else { return }
        isPurchasing = true
        errorMessage = nil

        Task {
            do {
                AnalyticsManager.shared.trackPurchaseStarted(productID: package.storeProduct.productIdentifier, flowID: "legacy_paywall")
                let result = try await Purchases.shared.purchase(package: package)
                if !result.userCancelled {
                    AnalyticsManager.shared.observePurchase(package: package, transaction: result.transaction, customerInfo: result.customerInfo, flowID: "legacy_paywall")
                    await MainActor.run {
                        isPurchasing = false
                        onPurchaseSuccess(result.customerInfo)
                    }
                } else {
                    AnalyticsManager.shared.trackPurchaseResult("cancelled", productID: package.storeProduct.productIdentifier, flowID: "legacy_paywall")
                    await MainActor.run {
                        isPurchasing = false
                        if !hasShownRetention {
                            hasShownRetention = true
                            showRetention = true
                        }
                    }
                }
            } catch {
                await MainActor.run {
                    isPurchasing = false
                    if let rcError = error as? RevenueCat.ErrorCode,
                       rcError == .purchaseCancelledError {
                        AnalyticsManager.shared.trackPurchaseResult("cancelled", productID: package.storeProduct.productIdentifier, flowID: "legacy_paywall")
                        if !hasShownRetention {
                            hasShownRetention = true
                            showRetention = true
                        }
                    } else {
                        AnalyticsManager.shared.trackPurchaseResult(
                            "failed",
                            productID: package.storeProduct.productIdentifier,
                            flowID: "legacy_paywall",
                            errorCode: String((error as NSError).code)
                        )
                        errorMessage = error.localizedDescription
                    }
                }
            }
        }
    }

    private func restorePurchases() {
        isPurchasing = true
        errorMessage = nil
        AnalyticsManager.shared.trackRestoreStarted(source: "legacy_paywall", flowID: "legacy_paywall")

        Task {
            do {
                let customerInfo = try await Purchases.shared.restorePurchases()
                await MainActor.run {
                    isPurchasing = false
                    let restored = customerInfo.entitlements[AppConfig.revenueCatEntitlementId]?.isActive == true
                    AnalyticsManager.shared.trackRestoreResult(restored ? "restored" : "no_entitlement", source: "legacy_paywall", flowID: "legacy_paywall")
                    if restored {
                        onPurchaseSuccess(customerInfo)
                    }
                }
            } catch {
                await MainActor.run {
                    isPurchasing = false
                    AnalyticsManager.shared.trackRestoreResult(
                        "failed",
                        source: "legacy_paywall",
                        flowID: "legacy_paywall",
                        errorCode: String((error as NSError).code)
                    )
                    errorMessage = error.localizedDescription
                }
            }
        }
    }
}
