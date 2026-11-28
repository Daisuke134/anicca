"""Static SwiftUI wiring contracts; these do not execute Swift or RevenueCat.

Run from any directory with Python 3. Native selection behavior is covered by
PaywallPackageSelectionTests.swift alongside this file.
"""

from pathlib import Path
import re
import unittest


APP_ROOT = Path(__file__).resolve().parents[2]
VIEW = APP_ROOT / "aniccaios/Onboarding/PaywallVariantBView.swift"
HELPER = APP_ROOT / "aniccaios/Onboarding/PaywallPackageSelection.swift"
SUBSCRIPTION_MANAGER = APP_ROOT / "aniccaios/Services/SubscriptionManager.swift"
ONBOARDING = APP_ROOT / "aniccaios/Onboarding/OnboardingFlowView.swift"
ANALYTICS = APP_ROOT / "aniccaios/Services/AnalyticsManager.swift"
PAYWALL_CONTAINER = APP_ROOT / "aniccaios/Onboarding/OnboardingBibleViews.swift"
SETTINGS = APP_ROOT / "aniccaios/Views/Feed/SettingsSheet.swift"
RETENTION_SHEET = APP_ROOT / "aniccaios/Onboarding/RetentionOfferSheet.swift"
LEGACY_PAYWALL = APP_ROOT / "aniccaios/Onboarding/PlanSelectionStepView.swift"


class PaywallSelectionWiringTests(unittest.TestCase):
    def setUp(self):
        self.source = VIEW.read_text(encoding="utf-8")
        self.helper = HELPER.read_text(encoding="utf-8")

    def test_offering_load_rejects_honne_current_and_falls_back_to_anicca_variant_b(self):
        manager = SUBSCRIPTION_MANAGER.read_text(encoding="utf-8")
        for required in (
            'private static let aniccaFallbackOfferingIdentifier = "anicca_variant_b"',
            "PaywallOfferingSelection.resolve(",
            "isUsableForAnicca:",
            'productIdentifiers: packages.map { $0.storeProduct.productIdentifier }',
            "resolveAniccaOffering(from: cached)",
            "resolveAniccaOffering(from: result)",
        ):
            self.assertIn(required, manager)
        self.assertIn('productIdentifiers.allSatisfy { $0.hasPrefix("ai.anicca.app.ios.") }', self.helper)
        self.assertNotIn("if let offering = result.current", manager)

    def test_initial_appearance_reconciles_selection(self):
        self.assertIsNotNone(re.search(
            r"(?s)\.onAppear\s*\{\s*synchronizePackageSelection\(\)\s*\}",
            self.source,
        ), "Initial appearance must reconcile selection")

    def test_async_load_and_same_id_replacement_reconcile_selection(self):
        # IDs and Package's value equality can stay the same on a refresh.
        # Observing object identity must still select the new Package instance.
        self.assertIsNotNone(re.search(
            r"(?s)\.onChange\(of: packages\.map\s*\{\s*ObjectIdentifier\(\$0\)"
            r"\s*\}\)\s*\{\s*_ in\s*synchronizePackageSelection\(\)\s*\}",
            self.source,
        ), "Package instance changes must reconcile selection after load or retry")

    def test_reconciliation_passes_current_packages_and_user_selection(self):
        match = re.search(
            r"(?s)private func synchronizePackageSelection\(\)\s*\{(.*?)\n    \}",
            self.source,
        )
        self.assertIsNotNone(match, "The view must reconcile asynchronously loaded packages")
        body = match.group(1)
        for required in (
            "selectedPackage = PaywallPackageSelection.resolve(",
            "packages: packages,",
            "selectedID: selectedPackage?.id,",
            "isAnnual: { $0.packageType == .annual },",
            "isMonthly: { $0.packageType == .monthly }",
        ):
            self.assertIn(required, body)
        for forbidden in ("Purchases.", "purchase()", "isPurchasing =", "onDismiss(", "onPurchaseSuccess("):
            self.assertNotIn(forbidden, body)

    def test_purchase_requires_selection_and_blocks_repeated_cta_taps(self):
        self.assertIn(".disabled(selectedPackage == nil || isPurchasing)", self.source)
        self.assertRegex(
            self.source,
            r"private func purchase\(\)\s*\{\s*guard let package = selectedPackage else \{ return \}",
        )
        self.assertIn("Button { purchase() } label:", self.source)

    def test_lifetime_is_gated_by_current_app_store_storefront(self):
        self.assertIn("import StoreKit", self.source)
        self.assertIn("await Storefront.current", self.source)
        self.assertIn("AsyncStream<Void>", self.source)
        self.assertIn("for await storefront in Storefront.updates", self.source)
        self.assertIn("await Task.yield()", self.source)
        self.assertIn("latestStorefront?.countryCode.uppercased() == countryCode?.uppercased()", self.source)
        self.assertIn("PaywallStorefrontEligibility.includesLifetime(", self.source)
        purchase = self.source.split("private func purchase()", 1)[1].split("private func restorePurchases()", 1)[0]
        self.assertIn("let currentStorefront = isLifetimePackage ? await Storefront.current : nil", purchase)
        self.assertIn("PaywallStorefrontEligibility.allowsPurchase(", purchase)
        self.assertLess(purchase.index("PaywallStorefrontEligibility.allowsPurchase("), purchase.index("Purchases.shared.purchase(package: package)"))
        self.assertIn("containsCurrentInstance(package, in: currentPackages)", purchase)
        self.assertIn("appState.cachedOfferingStorefrontCountryCode", self.source)
        self.assertNotIn("Locale.preferredLanguages", self.source)

    def test_retry_and_timeout_recheck_storefront_eligibility(self):
        retry = self.source.split("private var loadingContent:", 1)[1].split(
            "private var legalLinks:", 1
        )[0]
        self.assertIn("let loaded = await refreshStorefrontEligibility()", retry)
        self.assertIn("trackOfferingLoadResult(loaded)", retry)
        timeout = self.source.split("private func scheduleReloadTimeout()", 1)[1].split("private func purchase()", 1)[0]
        self.assertIn("let loaded = await refreshStorefrontEligibility()", timeout)
        self.assertIn("trackOfferingLoadResult(loaded)", timeout)

    def test_subscription_refresh_discards_outdated_and_cross_storefront_results(self):
        manager = SUBSCRIPTION_MANAGER.read_text(encoding="utf-8")
        self.assertIn("offeringsRefreshGeneration", manager)
        self.assertIn("PaywallOfferingSelection.isLatestRefresh(", manager)
        self.assertIn("PaywallStorefrontEligibility.sameStorefront(", manager)
        self.assertLess(manager.index("PaywallOfferingSelection.isLatestRefresh("), manager.index("AppState.shared.updateOffering(aniccaOffering"))

    def test_storefront_revision_rejects_roundtrip_and_purchase_time_races(self):
        app_state = (APP_ROOT / "aniccaios/AppState.swift").read_text(encoding="utf-8")
        manager = SUBSCRIPTION_MANAGER.read_text(encoding="utf-8")
        self.assertIn("@Published private(set) var storefrontRevision", app_state)
        self.assertIn("func recordStorefrontCountryCode(", app_state)
        refresh = manager.split("func refreshOfferings()", 1)[1].split("func syncNow()", 1)[0]
        self.assertIn("let requestStorefrontRevision = AppState.shared.storefrontRevision", refresh)
        self.assertIn("isUnchangedStorefrontRevision(", refresh)
        self.assertLess(refresh.index("isUnchangedStorefrontRevision("), refresh.index("updateOffering(aniccaOffering"))
        self.assertIn("AppState.shared.recordStorefrontCountryCode(storefront.countryCode)", self.source)
        purchase = self.source.split("private func purchase()", 1)[1].split("private func restorePurchases()", 1)[0]
        self.assertIn("let purchaseStorefrontRevision = appState.storefrontRevision", purchase)
        self.assertIn("isUnchangedStorefrontRevision(", purchase)
        self.assertIn("appState.currentStorefrontCountryCode", purchase)
        self.assertIn("Task { @MainActor in", purchase)
        self.assertNotIn("await MainActor.run", purchase)

    def test_free_onboarding_completes_without_a_network_or_purchase_gate(self):
        onboarding = ONBOARDING.read_text(encoding="utf-8")
        resume = onboarding.split("if appState.onboardingQuestionsCompleted", 1)[1].split(
            "step = appState.onboardingStep", 1
        )[0]
        self.assertIn("completeFreeOnboarding()", resume)
        # Winner spec section 6: the paywall is the final journey step, not a
        # cover gate. Dismissing it or purchasing both advance, entitled
        # users skip its presentation entirely, and advancing from it
        # completes onboarding locally.
        paywall_step = onboarding.split("case .paywall:", 1)[1].split("case .name:", 1)[0]
        self.assertIn("PaywallFlowContainer(onPurchaseSuccess: { _ in advance() }, onDismiss: advance)", paywall_step)
        self.assertIn("PaywallPresentationPolicy.shouldPresent(", paywall_step)
        completion = onboarding.split("if step == .paywall {", 1)[1].split(
            "if let next = step.nextStep(", 1
        )[0]
        self.assertIn("completeFreeOnboarding()", completion)
        self.assertNotIn("showPaywall", onboarding)
        self.assertNotIn("showFirstIntervention", onboarding)

    def test_soft_paywall_does_not_emit_retired_hard_experiment_exposure(self):
        container = PAYWALL_CONTAINER.read_text(encoding="utf-8").split("struct PaywallFlowContainer", 1)[1]
        self.assertNotIn("trackExperimentExposure", container)
        self.assertIn('accessibilityIdentifier("paywall-close-button")', container)

    def test_optional_paywall_opens_plan_selection_and_records_paywall_shown(self):
        container = PAYWALL_CONTAINER.read_text(encoding="utf-8").split(
            "struct PaywallFlowContainer", 1
        )[1]
        analytics = ANALYTICS.read_text(encoding="utf-8")
        self.assertIn("@State private var step: PaywallStep = .planSelection", container)
        self.assertIn(".analyticsScreen(.paywall, flowID: flowID)", container)
        track_viewed = analytics.split("private func recordScreenView(", 1)[1].split(
            "func trackScreenViewedIfNeeded", 1
        )[0]
        self.assertIn("if screenID == AnalyticsScreenID.paywall.rawValue", track_viewed)
        self.assertIn("track(.paywallShown, properties: properties)", track_viewed)
        self.assertNotIn("trackPaywallViewed", self.source)
        self.assertIn('case paywallShown = "paywall_shown"', analytics)

    def test_trial_started_tracks_a_confirmed_active_trial_entitlement(self):
        purchase = self.source.split("private func purchase()", 1)[1].split(
            "private func restorePurchases()", 1
        )[0]
        analytics = ANALYTICS.read_text(encoding="utf-8")
        observer = analytics.split("func observePurchase(", 1)[1].split("func updateSKANConversionValue", 1)[0]
        self.assertIn("AnalyticsManager.shared.observePurchase(package: package, transaction: result.transaction, customerInfo: result.customerInfo, flowID: flowID)", purchase)
        self.assertIn("guard purchaseObservations.record(transaction?.transactionIdentifier)", observer)
        self.assertIn("let entitlement = customerInfo.entitlements[AppConfig.revenueCatEntitlementId]", observer)
        self.assertIn("let isTrial = entitlement?.isActive == true && entitlement?.periodType == .trial", observer)
        self.assertIn('"flow_id": flowID', observer)
        self.assertIn('track(.onboardingPaywallPurchased, properties: ["flow_id": flowID])', observer)
        self.assertIn('trackTrialStarted(productId: package.storeProduct.productIdentifier, flowID: flowID)', observer)

    def test_purchase_trial_and_restore_events_carry_their_flow_id(self):
        analytics = ANALYTICS.read_text(encoding="utf-8")
        for name in (
            "trackTrialStarted", "trackPurchaseStarted", "trackPurchaseResult",
            "trackRestoreStarted", "trackRestoreResult",
        ):
            method = re.search(rf"(?s)func {name}\((.*?)\)\s*\{{(.*?)\n    \}}", analytics)
            self.assertIsNotNone(method, f"Missing analytics helper {name}")
            self.assertIn("flowID: String", method.group(1), name)
            self.assertIn('"flow_id": flowID', method.group(2), name)

    def test_settings_purchase_is_not_counted_as_onboarding_conversion(self):
        settings = SETTINGS.read_text(encoding="utf-8")
        self.assertIn('flowID: "settings_subscription"', settings)
        observer = ANALYTICS.read_text(encoding="utf-8").split("func observePurchase(", 1)[1].split("func updateSKANConversionValue", 1)[0]
        self.assertRegex(
            observer,
            r'if flowID == "onboarding" \|\| flowID == "legacy_paywall"\s*\{\s*'
            r'track\(\.onboardingPaywallPurchased, properties: \["flow_id": flowID\]\)\s*\}',
            "Only onboarding-owned purchase observations may emit the onboarding conversion event",
        )
        self.assertLess(
            observer.index("guard purchaseObservations.record(transaction?.transactionIdentifier)"),
            observer.index('if flowID == "onboarding" || flowID == "legacy_paywall"'),
            "Duplicate or missing transactions must stop before the onboarding conversion event",
        )

    def test_purchase_and_retention_callers_share_transaction_dedup_and_flow_scope(self):
        retention = RETENTION_SHEET.read_text(encoding="utf-8")
        legacy = LEGACY_PAYWALL.read_text(encoding="utf-8")
        for source, call in (
            (self.source, "observePurchase(package: package, transaction: result.transaction, customerInfo: result.customerInfo, flowID: flowID)"),
            (retention, "observePurchase(package: pkg, transaction: result.transaction, customerInfo: result.customerInfo, flowID: flowID)"),
        ):
            self.assertIn(call, source)
            self.assertNotIn("track(.onboardingPaywallPurchased)", source)
        self.assertIn("PaywallVariantBView(", legacy)
        self.assertIn('flowID: "legacy_paywall"', legacy)
        self.assertNotIn("Purchases.shared.purchase", legacy)

    def test_experiment_exposure_wires_mixpanel_and_revenuecat_custom_impression(self):
        analytics = ANALYTICS.read_text(encoding="utf-8")
        onboarding = ONBOARDING.read_text(encoding="utf-8")
        container = PAYWALL_CONTAINER.read_text(encoding="utf-8").split("struct PaywallFlowContainer", 1)[1]

        # AnalyticsManager must fire both Mixpanel experiment_exposure and RevenueCat trackCustomPaywallImpression
        exposure_method = analytics.split("func trackExperimentExposure(", 1)[1].split("func trackPurchaseResult(", 1)[0]
        self.assertIn("track(.experimentExposure, properties: [", exposure_method)
        self.assertIn('"experiment_id": PaywallGateVariant.experimentIdentifier', exposure_method)
        self.assertIn('"variant": gateVariant.rawValue', exposure_method)
        self.assertIn('"offering_id": offeringIdentifier ?? "unknown"', exposure_method)
        self.assertIn('"paywall_gate_variant": gateVariant.rawValue', exposure_method)
        self.assertIn('"flow_id": flowID', exposure_method)
        self.assertIn("Purchases.shared.trackCustomPaywallImpression()", exposure_method)

        # Retain the historical helper, but the new soft experience must not
        # be recorded as exposure to the retired hard-paywall experiment.
        self.assertNotIn("trackExperimentExposure(", onboarding)
        self.assertNotIn("trackExperimentExposure(", container)
        themes = SETTINGS.read_text(encoding="utf-8").split("struct ThemePickerView", 1)[1]
        cover = themes.split(".fullScreenCover(isPresented: $showThemePaywall)", 1)[1]
        self.assertIn(".environmentObject(appState)", cover)
        self.assertIn('flowID: "premium_theme"', cover)

    def test_premium_theme_success_closes_the_settings_owner_sheet(self):
        settings, themes = SETTINGS.read_text(encoding="utf-8").split("struct ThemePickerView", 1)
        self.assertIn("ThemePickerView(onPremiumActivated: { dismiss() })", settings)
        success = themes.split("onPurchaseSuccess: { customerInfo in", 1)[1].split("onDismiss:", 1)[0]
        self.assertIn("if let onPremiumActivated", success)
        self.assertIn("onPremiumActivated()", success)
        self.assertIn("guard appState.subscriptionInfo.isEntitled", success)

    def test_sdk_configuration_never_logs_the_api_key(self):
        manager = SUBSCRIPTION_MANAGER.read_text(encoding="utf-8")
        self.assertIn("Configuration.Builder(withAPIKey: apiKey)", manager)
        self.assertFalse(any("print(" in line and "apiKey" in line for line in manager.splitlines()), "SDK configuration must not print its credential")

    def test_relaunch_handles_store_account_prompt_before_verifying_free_use(self):
        flow = (APP_ROOT / "maestro/v1.9.14/01-soft-paywall.yaml").read_text(encoding="utf-8")
        relaunch = flow.split("- stopApp", 1)[1]
        self.assertIn("text: Cancel", relaunch)
        self.assertIn("optional: true", relaunch)
        self.assertLess(relaunch.index("text: Cancel"), relaunch.index("id: feed-today"))
        self.assertIn("maestro.copiedText === output.savedAffirmation", relaunch)
        self.assertNotIn("maestro.copiedText !== output.relaunchedQuote", relaunch)

    def test_trial_disclosures_never_fall_back_to_another_product(self):
        self.assertNotIn("offerFreeTrialDiscount", self.source)
        self.assertNotIn("displayedTrialDiscount", self.source)
        self.assertIn("freeTrialDiscount(for: selectedPackage)", self.source)
        self.assertIn("checkTrialOrIntroDiscountEligibility(productIdentifiers:", self.source)
        self.assertIn("eligibility[package.storeProduct.productIdentifier]?.status", self.source)
        self.assertIn("PaywallTrialPresentation.resolve(", self.source)

    def test_primary_offer_is_the_annual_card_and_other_plans_fold_inline(self):
        # Issue #731: one annual card. Weekly/lifetime unfold in place.
        # A sheet must not replace that disclosure.
        self.assertNotIn(".sheet(isPresented: $showOtherPlans)", self.source)
        self.assertIn("PaywallPlanPresentation.featured", self.source)
        self.assertIn("PaywallPlanPresentation.folded", self.source)
        self.assertIn('accessibilityIdentifier("paywall-other-plans")', self.source)
        self.assertIn("AnalyticsManager.shared.track(.paywallOtherPlansExpanded", self.source)
        self.assertIn("PaywallTrustLine.localizationKey(trialEligible: hasTrialEligibility)", self.source)
        self.assertIn('accessibilityIdentifier("paywall-trust-line")', self.source)
        self.assertIn('accessibilityIdentifier("paywall-plan-cta")', self.source)
        cta = self.source.index('accessibilityIdentifier("paywall-plan-cta")')
        trust = self.source.index('accessibilityIdentifier("paywall-trust-line")')
        self.assertLess(cta, trust)
        self.assertIn("private var planCards", self.source)
        self.assertIn('accessibilityIdentifier("paywall-billed-amount")', self.source)
        self.assertIn('accessibilityIdentifier("paywall-monthly-equivalent")', self.source)
        self.assertIn('accessibilityIdentifier("paywall-plan-\\(Self.planIdentifierName(for: package.packageType))")', self.source)
        self.assertNotIn("dailyPrice", self.source)
        self.assertNotIn(".lineLimit(1)", self.source)
        for key in ("paywall_plan_restore", "paywall_plan_terms", "paywall_plan_privacy"):
            self.assertIn(key, self.source)
        analytics = ANALYTICS.read_text(encoding="utf-8")
        self.assertIn('case paywallShown = "paywall_shown"', analytics)
        self.assertIn('case productSelected = "product_selected"', analytics)
        self.assertIn('case purchaseStarted = "purchase_started"', analytics)
        self.assertIn('case purchaseResult = "purchase_result"', analytics)
        self.assertIn('case paywallOtherPlansExpanded = "paywall_other_plans_expanded"', analytics)

    def test_trust_line_copy_is_localized_for_english_and_japanese(self):
        en = (APP_ROOT / "aniccaios/Resources/en.lproj/Localizable.strings").read_text(encoding="utf-8")
        ja = (APP_ROOT / "aniccaios/Resources/ja.lproj/Localizable.strings").read_text(encoding="utf-8")
        self.assertIn(
            '"paywall_no_payment_now_cancel" = "No payment now. Cancel anytime in Settings.";',
            en,
        )
        self.assertIn('"paywall_cancel_anytime_settings" = "Cancel anytime in Settings.";', en)
        self.assertIn('"paywall_other_plans" = "Other plans";', en)
        self.assertIn(
            '"paywall_no_payment_now_cancel" = "今は支払いなし。設定からいつでも解約できます。";',
            ja,
        )
        self.assertIn('"paywall_cancel_anytime_settings" = "設定からいつでも解約できます。";', ja)
        self.assertIn('"paywall_other_plans" = "その他のプラン";', ja)

    def test_policy_returns_current_match_before_annual_monthly_defaults(self):
        # Structural contract only. Execute the companion Swift tests to verify
        # actual selection behavior and reference identity in the Swift runtime.
        helper = HELPER.read_text(encoding="utf-8")
        self.assertIsNotNone(re.search(
            r"(?s)if let selectedID,\s*let current = packages\.first\(where:"
            r"\s*\{\s*\$0\.id == selectedID\s*\}\)\s*\{\s*return current\s*\}"
            r"\s*return packages\.first\(where: isAnnual\)"
            r"\s*\?\? packages\.first\(where: isMonthly\)",
            helper,
        ), "Preserve only a current instance, then prefer annual over monthly")


if __name__ == "__main__":
    unittest.main()
## tests complete
