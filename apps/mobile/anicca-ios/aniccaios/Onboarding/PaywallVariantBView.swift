import SwiftUI
import RevenueCat
import StoreKit
import UIKit

/// Single-offer paywall (Issue #731): the annual plan with its free trial
/// is the only offer on the first screen. Weekly and Lifetime fold behind
/// an always-visible "Other plans" row that expands in place, so nothing
/// is hidden (Issue #9356) and nothing is unreachable.
struct PaywallVariantBView: View {
    let variant: String
    let onPurchaseSuccess: (CustomerInfo) -> Void
    let onDismiss: () -> Void
    var flowID: String = "onboarding"

    @EnvironmentObject private var appState: AppState
    @State private var selectedPackage: Package?
    @State private var isPurchasing = false
    @State private var errorMessage: String?
    @State private var hasShownRetention = false
    @State private var didAcceptRetention = false
    @State private var showRetention = false
    @State private var showReloadAfterTimeout = false
    @State private var showsOtherPlans = false
    @State private var trackedOfferingLoadOutcomes: Set<String> = []
    @State private var eligibility: [String: IntroEligibility] = [:]

    private var offering: Offering? { appState.cachedOffering }
    private var packages: [Package] {
        let available = offering?.availablePackages ?? []
        guard PaywallStorefrontEligibility.includesLifetime(
            countryCode: appState.currentStorefrontCountryCode,
            offeringCountryCode: appState.cachedOfferingStorefrontCountryCode
        ) else {
            return available.filter { $0.packageType != .lifetime }
        }
        return available
    }

    private func freeTrialDiscount(for package: Package?) -> StoreProductDiscount? {
        guard let discount = package?.storeProduct.introductoryDiscount,
              discount.paymentMode == .freeTrial else { return nil }
        return discount
    }

    private var freeTrialDiscount: StoreProductDiscount? {
        freeTrialDiscount(for: selectedPackage)
    }

    private func trialPresentation(for package: Package) -> PaywallTrialPresentation {
        let isEligible: Bool?
        switch eligibility[package.storeProduct.productIdentifier]?.status {
        case .eligible: isEligible = true
        case .ineligible, .noIntroOfferExists: isEligible = false
        default: isEligible = nil
        }
        return PaywallTrialPresentation.resolve(
            hasFreeTrial: freeTrialDiscount(for: package) != nil,
            isEligible: isEligible
        )
    }

    private var hasTrialEligibility: Bool {
        selectedPackage.map { trialPresentation(for: $0) == .eligible } ?? false
    }

    private var trialEndDate: Date? {
        guard hasTrialEligibility, let period = freeTrialDiscount?.subscriptionPeriod else { return nil }
        return Calendar.current.date(byAdding: dateComponents(for: period), to: Date())
    }

    var body: some View {
        ViewThatFits(in: .vertical) {
            paywallContent.fixedSize(horizontal: false, vertical: true)
            ScrollView { paywallContent }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(AppBackground())
        .onAppear {
            synchronizePackageSelection()
        }
        .onChange(of: packages.map { ObjectIdentifier($0) }) { _ in
            synchronizePackageSelection()
        }
        .task(id: packages.map { ObjectIdentifier($0) }) {
            await refreshTrialEligibility()
        }
        .task {
            let storefrontUpdates = AsyncStream<Void> { continuation in
                let updatesTask = Task { @MainActor in
                    for await storefront in Storefront.updates {
                        AppState.shared.recordStorefrontCountryCode(storefront.countryCode)
                        continuation.yield(())
                    }
                    continuation.finish()
                }
                continuation.onTermination = { _ in updatesTask.cancel() }
            }
            var updatesIterator = storefrontUpdates.makeAsyncIterator()
            await Task.yield()
            let initialLoad = await refreshStorefrontEligibility()
            trackOfferingLoadResult(initialLoad)
            while await updatesIterator.next() != nil {
                let updatedLoad = await refreshStorefrontEligibility()
                trackOfferingLoadResult(updatedLoad)
            }
        }
        .sheet(isPresented: $showRetention, onDismiss: {
            if !didAcceptRetention {
                AnalyticsManager.shared.trackScreenViewed(screenID: .paywall, flowID: flowID)
            }
        }) {
            RetentionOfferSheet(flowID: flowID) { customerInfo in
                didAcceptRetention = true
                showRetention = false
                onPurchaseSuccess(customerInfo)
            }
        }
    }

    private var paywallContent: some View {
        VStack(spacing: 12) {
            Text(String(localized: "paywall_b_title"))
                .font(.system(.title2, design: .serif))
                .foregroundStyle(AppTheme.Colors.label)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)
                .accessibilityAddTraits(.isHeader)

            VStack(alignment: .leading, spacing: 6) {
                featureRow(String(localized: "soft_paywall_free_benefit"))
                featureRow(String(localized: "soft_paywall_premium_benefit"))
            }

            if packages.isEmpty {
                loadingContent
            } else if let package = selectedPackage {
                offerSection
                if let end = trialEndDate {
                    trialTimeline(end: end, package: package)
                }
                Text(disclosure(for: package))
                    .font(.footnote)
                    .foregroundStyle(AppTheme.Colors.label)
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
                    .accessibilityIdentifier("paywall-billing-disclosure")
                ctaSection
                trustLine(for: package)
            }
            legalLinks
        }
        .padding(.horizontal, 24)
        .padding(.top, 48)
        .padding(.bottom, 16)
    }

    private var loadingContent: some View {
        VStack(spacing: 12) {
            ProgressView()
            if showReloadAfterTimeout {
                Text(String(localized: "paywall_b_load_failed"))
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
                Button {
                    Task {
                        let loaded = await refreshStorefrontEligibility()
                        trackOfferingLoadResult(loaded)
                    }
                } label: {
                    Text(String(localized: "paywall_b_retry"))
                        .frame(minHeight: 44)
                        .contentShape(Rectangle())
                }
                .buttonStyle(PressScaleButtonStyle())
                .font(.headline)
            }
        }
        .padding(.vertical, 24)
        .onAppear { scheduleReloadTimeout() }
    }

    private var legalLinks: some View {
        ViewThatFits(in: .horizontal) {
            HStack(spacing: 16) {
                restoreButton
                termsLinks
            }
            VStack(spacing: 4) {
                restoreButton
                termsLinks
            }
        }
        .font(.footnote)
        .foregroundStyle(AppTheme.Colors.accent)
    }

    private var restoreButton: some View {
        Button { restorePurchases() } label: {
            Text(String(localized: "paywall_plan_restore"))
                .frame(minHeight: 44)
                .contentShape(Rectangle())
        }
            .buttonStyle(PressScaleButtonStyle())
            .disabled(isPurchasing)
            .accessibilityIdentifier("paywall-restore")
    }

    private var termsLinks: some View {
        HStack(spacing: 8) {
            Link(String(localized: "paywall_plan_terms"), destination: AppConfig.termsURL)
                .frame(minHeight: 44)
            Text("·")
            Link(String(localized: "paywall_plan_privacy"), destination: AppConfig.privacyURL)
                .frame(minHeight: 44)
        }
    }

    private var ctaSection: some View {
        VStack(spacing: 8) {
            if let errorMessage {
                Text(errorMessage)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Button { purchase() } label: {
                Group {
                    if isPurchasing {
                        ProgressView().tint(.white)
                    } else {
                        Text(String(localized: selectedPackage?.packageType == .lifetime
                            ? "paywall_cta_lifetime"
                            : (hasTrialEligibility ? "paywall_b_cta_trial" : "paywall_plan_cta_subscribe")))
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
                .font(.headline)
                .foregroundStyle(.white)
                .frame(maxWidth: .infinity, minHeight: 56)
                .padding(.vertical, 4)
                .background(AppTheme.Colors.accent)
                .clipShape(RoundedRectangle(cornerRadius: 18))
                .contentShape(Rectangle())
            }
            .buttonStyle(PressScaleButtonStyle())
            .disabled(selectedPackage == nil || isPurchasing)
            .accessibilityIdentifier("paywall-plan-cta")
        }
    }

    /// The lead offer: the annual plan and its free trial, plus the folded
    /// "Other plans" row. Nothing else is on the first screen.
    private var offerSection: some View {
        VStack(spacing: 10) {
            if let primary = primaryPackage {
                planCard(primary)
            }
            if !secondaryPackages.isEmpty {
                otherPlansToggle
                if isOtherPlansExpanded {
                    ForEach(secondaryPackages, id: \.identifier) { package in
                        planCard(package)
                    }
                }
            }
        }
        // No identifier on this container: the cards' own identifiers are
        // the E2E contract and nothing may shadow them.
    }

    /// Always visible, expands in place. Issue #9356 rejected the version
    /// that hid the plans behind a sheet with a cut-off Lifetime row.
    /// Locked open while a folded plan is selected, so the user can always
    /// see the plan they are about to buy.
    private var otherPlansToggle: some View {
        Button {
            UISelectionFeedbackGenerator().selectionChanged()
            showsOtherPlans.toggle()
            AnalyticsManager.shared.track(.paywallOtherPlansToggled, properties: [
                "expanded": showsOtherPlans,
                "offering_id": offering?.identifier ?? "unknown",
                "flow_id": flowID,
            ])
        } label: {
            HStack(spacing: 6) {
                Text(String(localized: "paywall_other_plans"))
                    .font(.subheadline.weight(.medium))
                Image(systemName: "chevron.down")
                    .font(.caption.weight(.semibold))
                    .rotationEffect(.degrees(isOtherPlansExpanded ? 180 : 0))
            }
            .foregroundStyle(AppTheme.Colors.accent)
            .frame(maxWidth: .infinity, minHeight: 44)
            .contentShape(Rectangle())
        }
        .buttonStyle(PressScaleButtonStyle())
        .disabled(selectedPackage.map { package in
            !PaywallOfferLayout.isPrimary(planName: Self.planIdentifierName(for: package.packageType))
        } ?? false)
        .accessibilityIdentifier("paywall-other-plans")
        .accessibilityValue(isOtherPlansExpanded ? "expanded" : "collapsed")
    }

    private func planCard(_ package: Package) -> some View {
        Button {
            // Selection feedback while a value changes (Apple HIG, Playing haptics).
            UISelectionFeedbackGenerator().selectionChanged()
            selectedPackage = package
            AnalyticsManager.shared.track(.productSelected, properties: [
                "product_id": package.storeProduct.productIdentifier,
                "offering_id": offering?.identifier ?? "unknown",
                "source": "paywall",
            ])
        } label: {
            offerCard(package: package, isSelected: selectedPackage?.identifier == package.identifier)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .disabled(isPurchasing)
        .accessibilityIdentifier("paywall-plan-\(Self.planIdentifierName(for: package.packageType))")
    }

    /// Stable accessibility-identifier suffix for a plan card.
    /// `PackageType.rawValue` is an Int in RevenueCat (lifetime 0,
    /// annual 1, monthly 5, weekly 6), so interpolating it produced
    /// `paywall-plan-1` etc. and the E2E flows could not address the
    /// cards by name — build-830 E2E runs 43664427417 and 43667965841
    /// both failed on `paywall-plan-annual` while the hierarchy dump
    /// showed all four cards on screen with numeric ids.
    static func planIdentifierName(for packageType: PackageType) -> String {
        switch packageType {
        case .annual: return "annual"
        case .monthly: return "monthly"
        case .weekly: return "weekly"
        case .lifetime: return "lifetime"
        case .sixMonth: return "six-month"
        case .threeMonth: return "three-month"
        case .twoMonth: return "two-month"
        case .custom: return "custom"
        default: return "other"
        }
    }

    /// The three plans the paywall sells, in display order: annual
    /// highlighted first, then weekly, then lifetime. Monthly is filtered
    /// out here — see PaywallPlanDisplay for the primary-source reasoning.
    private var orderedPackages: [Package] {
        let visible = packages.filter {
            PaywallPlanDisplay.isVisible(planName: Self.planIdentifierName(for: $0.packageType))
        }
        return PaywallPlanOrdering.ordered(visible) {
            PaywallPlanDisplay.rank(planName: Self.planIdentifierName(for: $0.packageType))
        }
    }

    /// The single lead offer (Issue #731). Falls back to the first plan on
    /// sale if the offering has no annual package, so the screen is never
    /// empty.
    private var primaryPackage: Package? {
        orderedPackages.first {
            PaywallOfferLayout.isPrimary(planName: Self.planIdentifierName(for: $0.packageType))
        } ?? orderedPackages.first
    }

    /// Plans folded behind the "Other plans" row.
    private var secondaryPackages: [Package] {
        guard let primary = primaryPackage else { return [] }
        return orderedPackages.filter { $0.identifier != primary.identifier }
    }

    private var isOtherPlansExpanded: Bool {
        PaywallOfferLayout.isExpanded(
            manuallyExpanded: showsOtherPlans,
            selectedPlanName: selectedPackage.map { Self.planIdentifierName(for: $0.packageType) }
        )
    }

    /// The one-line trust display (Issue #731): what happens with the
    /// money and how to get out. Prices come from the store, never hard-coded.
    private func trustLine(for package: Package) -> some View {
        Text(trustText(for: package))
            .font(.footnote)
            .foregroundStyle(.secondary)
            .multilineTextAlignment(.center)
            .fixedSize(horizontal: false, vertical: true)
            .accessibilityIdentifier("paywall-trust-line")
    }

    private func trustText(for package: Package) -> String {
        if trialPresentation(for: package) == .eligible,
           freeTrialDiscount(for: package) != nil {
            return String(
                format: NSLocalizedString("paywall_b_trust_trial", comment: ""),
                billedAmount(for: package)
            )
        }
        return String(localized: "paywall_b_trust_no_trial")
    }

    private func offerCard(package: Package, isSelected: Bool) -> some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 6) {
                if package.packageType == .annual {
                    // The one highlighted plan (RevenueCat best practice:
                    // highlight a single plan with its badge).
                    Text(String(localized: "paywall_plan_yearly_badge"))
                        .font(.caption2.weight(.bold))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 3)
                        .background(AppTheme.Colors.accent, in: Capsule())
                        .accessibilityIdentifier("paywall-plan-badge-best-value")
                }
                Text(localizedPlanTitle(for: package))
                    .font(.subheadline)
                Text(billedAmount(for: package))
                    .font(.system(.title2, design: .serif).weight(.semibold))
                    .fixedSize(horizontal: false, vertical: true)
                    .accessibilityIdentifier("paywall-billed-amount")
                if let equivalent = monthlyEquivalent(for: package) {
                    Text(equivalent)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                        .accessibilityIdentifier("paywall-monthly-equivalent")
                }
                if trialPresentation(for: package) == .eligible,
                   let trial = freeTrialDiscount(for: package) {
                    Text(String(format: NSLocalizedString("paywall_trial_duration", comment: ""), periodDescription(trial.subscriptionPeriod)))
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(AppTheme.Colors.accent)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                .foregroundStyle(AppTheme.Colors.accent)
                .accessibilityHidden(true)
        }
        .padding(16)
        .foregroundStyle(AppTheme.Colors.label)
        .selectionCard(isSelected: isSelected)
        .accessibilityAddTraits(isSelected ? .isSelected : [])
    }

    private func featureRow(_ text: String) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "checkmark.circle.fill")
                .foregroundStyle(AppTheme.Colors.accent)
            Text(text)
                .foregroundStyle(AppTheme.Colors.label)
                .fixedSize(horizontal: false, vertical: true)
        }
        .font(.footnote)
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func trialTimeline(end: Date, package: Package) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            trialTimelineRow(date: Date(), detail: String(localized: "paywall_trial_starts_short"))
            trialTimelineRow(date: end, detail: billedAmount(for: package))
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(AppTheme.Colors.cardBackground.opacity(0.8))
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .accessibilityIdentifier("paywall-trial-timeline")
    }

    private func trialTimelineRow(date: Date, detail: String) -> some View {
        ViewThatFits(in: .horizontal) {
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                Text(date, style: .date).fontWeight(.semibold)
                Text(detail)
            }
            VStack(alignment: .leading, spacing: 2) {
                Text(date, style: .date).fontWeight(.semibold)
                Text(detail)
            }
        }
        .font(.caption)
        .foregroundStyle(AppTheme.Colors.label)
        .fixedSize(horizontal: false, vertical: true)
    }

    private func billedAmount(for package: Package) -> String {
        if package.packageType == .lifetime {
            return String(format: NSLocalizedString("paywall_billing_once", comment: ""), package.localizedPriceString)
        }
        guard let period = package.storeProduct.subscriptionPeriod else { return package.localizedPriceString }
        return String(format: NSLocalizedString("paywall_billing_period", comment: ""), package.localizedPriceString, periodDescription(period))
    }

    private func disclosure(for package: Package) -> String {
        guard package.packageType != .lifetime else {
            return String(format: NSLocalizedString("paywall_lifetime_disclosure", comment: ""), package.localizedPriceString)
        }
        if let trial = freeTrialDiscount(for: package) {
            switch trialPresentation(for: package) {
            case .eligible:
                return String(format: NSLocalizedString("paywall_trial_disclosure", comment: ""), periodDescription(trial.subscriptionPeriod), billedAmount(for: package))
            case .conditional:
                return String(format: NSLocalizedString("paywall_conditional_trial_disclosure", comment: ""), periodDescription(trial.subscriptionPeriod), billedAmount(for: package))
            case .none:
                break
            }
        }
        return String(format: NSLocalizedString("paywall_subscription_disclosure", comment: ""), billedAmount(for: package))
    }

    private func monthlyEquivalent(for package: Package) -> String? {
        guard package.packageType == .annual,
              let period = package.storeProduct.subscriptionPeriod,
              period.unit == .year, period.value > 0 else { return nil }
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.locale = Locale.current
        formatter.currencyCode = package.storeProduct.currencyCode
        let monthlyPrice = package.storeProduct.price / Decimal(period.value * 12)
        guard let price = formatter.string(from: monthlyPrice as NSDecimalNumber) else { return nil }
        return String(format: NSLocalizedString("paywall_monthly_equivalent", comment: ""), price)
    }

    private func periodDescription(_ period: RevenueCat.SubscriptionPeriod) -> String {
        let formatter = DateComponentsFormatter()
        formatter.unitsStyle = .full
        formatter.maximumUnitCount = 1
        return formatter.string(from: dateComponents(for: period)) ?? ""
    }

    private func dateComponents(for period: RevenueCat.SubscriptionPeriod) -> DateComponents {
        var components = DateComponents()
        switch period.unit {
        case .day: components.day = period.value
        case .week: components.weekOfMonth = period.value
        case .month: components.month = period.value
        case .year: components.year = period.value
        @unknown default: break
        }
        return components
    }

    private func localizedPlanTitle(for package: Package) -> String {
        switch package.packageType {
        case .annual: return String(localized: "paywall_b_plan_yearly")
        case .monthly: return String(localized: "paywall_b_plan_monthly")
        case .weekly: return String(localized: "paywall_b_plan_weekly")
        case .lifetime: return String(localized: "paywall_b_plan_lifetime")
        default: return package.storeProduct.localizedTitle
        }
    }

    @MainActor
    private func refreshTrialEligibility() async {
        eligibility = [:]
        let productIDs = packages.map { $0.storeProduct.productIdentifier }
        guard !productIDs.isEmpty else { return }
        let result = await Purchases.shared.checkTrialOrIntroDiscountEligibility(productIdentifiers: productIDs)
        guard !Task.isCancelled else { return }
        eligibility = result
    }

    @MainActor
    private func refreshStorefrontEligibility() async -> Bool? {
        while !Task.isCancelled {
            let currentStorefront = await Storefront.current
            let countryCode = currentStorefront?.countryCode
            appState.recordStorefrontCountryCode(countryCode)
            let revision = appState.storefrontRevision

            _ = await SubscriptionManager.shared.refreshOfferings()
            let latestStorefront = await Storefront.current
            appState.recordStorefrontCountryCode(latestStorefront?.countryCode)
            guard PaywallOfferingSelection.isUnchangedStorefrontRevision(
                startingRevision: revision,
                currentRevision: appState.storefrontRevision
            ) else { continue }
            guard latestStorefront?.countryCode.uppercased() == countryCode?.uppercased() else {
                continue
            }
            return !packages.isEmpty
        }
        return nil
    }

    @MainActor
    private func trackOfferingLoadResult(_ loaded: Bool?) {
        guard let loaded else { return }
        let result = loaded ? "loaded" : "unavailable"
        guard trackedOfferingLoadOutcomes.insert(result).inserted else { return }
        AnalyticsManager.shared.track(.onboardingPaywallOfferingLoadResult, properties: ["result": result])
    }

    // MARK: - Actions

    private func synchronizePackageSelection() {
        selectedPackage = PaywallPackageSelection.resolve(
            packages: packages,
            selectedID: selectedPackage?.id,
            isAnnual: { $0.packageType == .annual },
            isMonthly: { $0.packageType == .monthly }
        )
        // Keep the selection inside the plans this single-offer screen
        // renders. Monthly is on sale but not offered here, so a monthly
        // resolution would leave the screen without a visible selection.
        if let selected = selectedPackage,
           !orderedPackages.contains(where: { $0.identifier == selected.identifier }) {
            selectedPackage = primaryPackage
        }
    }

    private func scheduleReloadTimeout() {
        DispatchQueue.main.asyncAfter(deadline: .now() + 5) {
            if packages.isEmpty { showReloadAfterTimeout = true }
            Task {
                let loaded = await refreshStorefrontEligibility()
                trackOfferingLoadResult(loaded)
            }
        }
    }

    private func purchase() {
        guard let package = selectedPackage else { return }
        let isLifetimePackage = package.packageType == .lifetime
        let purchaseStorefrontRevision = appState.storefrontRevision
        isPurchasing = true
        errorMessage = nil

        Task { @MainActor in
            let currentStorefront = isLifetimePackage ? await Storefront.current : nil
            let currentPackages = appState.cachedOffering?.availablePackages ?? []
            let storefrontIsCurrent = !isLifetimePackage || (
                PaywallOfferingSelection.isUnchangedStorefrontRevision(
                    startingRevision: purchaseStorefrontRevision,
                    currentRevision: appState.storefrontRevision
                ) && PaywallStorefrontEligibility.sameStorefront(
                    first: currentStorefront?.countryCode,
                    second: appState.currentStorefrontCountryCode
                )
            )
            let canPurchase = storefrontIsCurrent && PaywallStorefrontEligibility.allowsPurchase(
                packageIsLifetime: isLifetimePackage,
                packageIsCurrent: PaywallPackageSelection.containsCurrentInstance(package, in: currentPackages),
                countryCode: currentStorefront?.countryCode,
                offeringCountryCode: appState.cachedOfferingStorefrontCountryCode
            )
            guard canPurchase else {
                isPurchasing = false
                if isLifetimePackage {
                    appState.recordStorefrontCountryCode(currentStorefront?.countryCode)
                }
                synchronizePackageSelection()
                await refreshStorefrontEligibility()
                return
            }

            do {
                AnalyticsManager.shared.trackPurchaseStarted(package: package, offeringID: offering?.identifier, flowID: flowID)
                let result = try await Purchases.shared.purchase(package: package)
                if !result.userCancelled {
                    AnalyticsManager.shared.observePurchase(package: package, transaction: result.transaction, customerInfo: result.customerInfo, flowID: flowID)
                    isPurchasing = false
                    onPurchaseSuccess(result.customerInfo)
                } else {
                    AnalyticsManager.shared.trackPurchaseResult("cancelled", productID: package.storeProduct.productIdentifier, flowID: flowID)
                    isPurchasing = false
                    if !hasShownRetention {
                        hasShownRetention = true
                        showRetention = true
                    }
                }
            } catch {
                isPurchasing = false
                if let rcError = error as? RevenueCat.ErrorCode,
                   rcError == .purchaseCancelledError {
                    AnalyticsManager.shared.trackPurchaseResult("cancelled", productID: package.storeProduct.productIdentifier, flowID: flowID)
                    if !hasShownRetention {
                        hasShownRetention = true
                        showRetention = true
                    }
                } else {
                    AnalyticsManager.shared.trackPurchaseResult(
                        "failed",
                        productID: package.storeProduct.productIdentifier,
                        flowID: flowID,
                        errorCode: String((error as NSError).code)
                    )
                    errorMessage = error.localizedDescription
                }
            }
        }
    }

    private func restorePurchases() {
        isPurchasing = true
        errorMessage = nil
        AnalyticsManager.shared.trackRestoreStarted(source: "paywall", flowID: flowID)
        Task {
            do {
                let customerInfo = try await Purchases.shared.restorePurchases()
                await MainActor.run {
                    isPurchasing = false
                    let restored = customerInfo.entitlements[AppConfig.revenueCatEntitlementId]?.isActive == true
                    AnalyticsManager.shared.trackRestoreResult(restored ? "restored" : "no_entitlement", source: "paywall", flowID: flowID)
                    if restored {
                        onPurchaseSuccess(customerInfo)
                    }
                }
            } catch {
                await MainActor.run {
                    isPurchasing = false
                    AnalyticsManager.shared.trackRestoreResult(
                        "failed",
                        source: "paywall",
                        flowID: flowID,
                        errorCode: String((error as NSError).code)
                    )
                    errorMessage = error.localizedDescription
                }
            }
        }
    }
}
