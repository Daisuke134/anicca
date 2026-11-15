"""Source wiring contracts only; not an execution of StoreKit or RevenueCat."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SWIFT = ROOT / 'aniccaios'


class PendingPurchaseWiringTests(unittest.TestCase):
    def test_both_purchase_sites_classify_pending_without_grant_or_retention(self):
        for name in ('PaywallVariantBView', 'RetentionOfferSheet'):
            source = (SWIFT / f'Onboarding/{name}.swift').read_text()
            with self.subTest(site=name):
                self.assertIn('rcError == .paymentPendingError', source)
                pending = source.split('rcError == .paymentPendingError', 1)[1].split('} else if', 1)[0]
                self.assertIn('recordPendingPurchase(', pending)
                for forbidden in ('onPurchaseSuccess(', 'onAccepted(', 'showRetention = true', 'localizedDescription', '"failed"', '"cancelled"'):
                    self.assertNotIn(forbidden, pending)
                self.assertLess(source.index('.paymentPendingError'), source.index('"failed"'))
                self.assertIn('guard !isPurchasing, !isPendingPurchase else { return }', source)
                self.assertIn('"purchase_pending_message"', source)
                self.assertIn('"purchase_pending_title"', source)

    def test_persistence_and_positive_evidence_resolution(self):
        source = (SWIFT / 'Services/SubscriptionManager.swift').read_text()
        for token in ('struct PendingPurchase: Codable', 'let productID: String', 'let startedAt: Date', 'let flowID: String', 'UserDefaults.standard.data(forKey:', 'JSONDecoder()', 'JSONEncoder()', 'trackPurchaseResult("pending"', 'trackPendingPurchaseResolved(', 'info.purchaseDate(forProductIdentifier: pending.productID)', 'purchaseDate > previousPurchaseDate', 'reconcilePendingPurchases(customerInfo)', 'reconcilePendingPurchases(info)'):
            self.assertIn(token, source)
        self.assertGreaterEqual(source.count('reconcilePendingPurchases('), 4)
        self.assertIn('await self.recheckPendingPurchases()', source)
        app = (SWIFT / 'aniccaiosApp.swift').read_text()
        self.assertIn('if phase == .active', app)
        self.assertIn('await SubscriptionManager.shared.recheckPendingPurchases()', app)
        self.assertIn('customerInfo(fetchPolicy: .fetchCurrent)', source)

    def test_resolution_matches_owner_and_provider_purchase_baseline(self):
        manager = (SWIFT / 'Services/SubscriptionManager.swift').read_text()
        self.assertIn('info.originalAppUserId == pending.originalAppUserID', manager)
        self.assertIn('let previousPurchaseDate: Date?', manager)
        self.assertNotIn('purchaseDate >= pending.startedAt', manager)
        for name in ('PaywallVariantBView', 'RetentionOfferSheet'):
            source = (SWIFT / f'Onboarding/{name}.swift').read_text()
            self.assertLess(source.index('purchaseBaseline = try await Purchases.shared.customerInfo(fetchPolicy: .fetchCurrent)'), source.index('Purchases.shared.purchase('))
            self.assertIn('baseline: purchaseBaseline', source)

    def test_paywall_checks_storefront_after_baseline_network_await(self):
        source = (SWIFT / 'Onboarding/PaywallVariantBView.swift').read_text().split('private func purchase()', 1)[1]
        self.assertLess(source.index('purchaseBaseline = try await'), source.index('let currentStorefront ='))
        self.assertLess(source.index('let currentStorefront ='), source.index('guard canPurchase else'))
        after_guard = source.split('guard canPurchase else', 1)[1].split('let result = try await Purchases.shared.purchase', 1)[0]
        self.assertNotIn('await Purchases.shared.customerInfo', after_guard)

    def test_unknown_or_failed_refresh_does_not_clear_pending(self):
        source = (SWIFT / 'Services/SubscriptionManager.swift').read_text()
        reconcile = source.split('private func reconcilePendingPurchases', 1)[1].split('func recheckPendingPurchases', 1)[0]
        self.assertIn('else { return false }', reconcile)
        self.assertIn('for pending in confirmed', reconcile)
        self.assertNotIn('removeAll', reconcile)
        self.assertNotIn('updateSubscriptionInfo', reconcile)
        self.assertLess(reconcile.index('persistPendingPurchases()'), reconcile.index('trackPendingPurchaseResolved('))
        refresh = source.split('func refreshCustomerInfo()', 1)[1].split('func syncNow()', 1)[0]
        failure = refresh.split('} catch {', 1)[1]
        self.assertNotIn('pendingPurchases', failure)

    def test_both_buttons_disable_and_start_time_precedes_purchase(self):
        for name in ('PaywallVariantBView', 'RetentionOfferSheet'):
            source = (SWIFT / f'Onboarding/{name}.swift').read_text()
            self.assertIn('@ObservedObject private var subscriptionManager', source)
            self.assertLess(source.index('let purchaseStartedAt ='), source.index('Purchases.shared.purchase('))
            if name == 'PaywallVariantBView':
                self.assertIn('.disabled(isPendingPurchase)', source)
            else:
                self.assertIn('isEnabled: retentionPackage != nil && !isPendingPurchase && !isPurchasing', source)

    def test_localizations_cover_every_existing_locale(self):
        locales = list((SWIFT / 'Resources').glob('*.lproj/Localizable.strings'))
        self.assertEqual(len(locales), 6)
        for path in locales:
            source = path.read_text()
            for key in ('purchase_pending_title', 'purchase_pending_message'):
                self.assertEqual(source.count(f'"{key}" ='), 1, str(path))

    def test_resolution_is_separate_from_new_purchase_and_revenue(self):
        source = (SWIFT / 'Services/AnalyticsManager.swift').read_text()
        self.assertIn('case pendingPurchaseResolved = "pending_purchase_resolved"', source)
        body = source.split('func trackPendingPurchaseResolved(', 1)[1].split('func trackRestoreStarted', 1)[0]
        for token in ('"product_id"', '"flow_id"', '"pending_seconds"', '"result": "confirmed"'):
            self.assertIn(token, body)
        self.assertNotIn('observePurchase(', body)


if __name__ == '__main__':
    unittest.main()
