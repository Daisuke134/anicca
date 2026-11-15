"""Static source contracts, not an execution of Swift, RevenueCat or a receiver."""
from pathlib import Path
import json
import unittest

APP_ROOT = Path(__file__).resolve().parents[2]
MANAGER = APP_ROOT / 'aniccaios/Services/SubscriptionManager.swift'
DECISION = APP_ROOT / 'docs/gates/server-notifications-decision-2026-11-16.md'
STATE = APP_ROOT / 'docs/gates/server-notifications-state-2026-11-16.json'


class ServerNotificationsWiringTests(unittest.TestCase):
    def test_decision_is_honest_about_external_work(self):
        doc = DECISION.read_text()
        for text in ('RevenueCat', 'App Store Server Notifications V2',
                     'relay is NOT implemented', 'dashboard state is unverified',
                     'Production', 'Sandbox', 'Get Notification History',
                     '1, 12, 24, 48, 72', 'billing/revenuecat/sync'):
            self.assertIn(text, doc)

    def test_informational_is_not_claimed_as_enforcement(self):
        source = MANAGER.read_text()
        self.assertIn('.with(entitlementVerificationMode: .informational)', source)
        self.assertIn('does not block access', source)
        self.assertIn('deliberate tradeoff, not enforcement', source)

    def test_freshness_uses_request_date_not_cache_observation_time(self):
        source = MANAGER.read_text()
        self.assertIn('static let entitlementStalenessLimit: TimeInterval = 72 * 60 * 60', source)
        self.assertIn('private(set) var lastCustomerInfoRequestAt: Date?', source)
        self.assertIn('guard let lastCustomerInfoRequestAt else { return true }', source)
        self.assertIn('age < 0 || age >= Self.entitlementStalenessLimit', source)
        tracking = source.split('private func recordCustomerInfoFreshness', 1)[1].split('private override init', 1)[0]
        self.assertIn('lastCustomerInfoRequestAt = info.requestDate', tracking)
        self.assertNotIn('= Date()', tracking)
        self.assertIn('entitlement_stale=', tracking)
        self.assertIn('customer_info_request_at=', tracking)
        self.assertNotIn('updateSubscriptionInfo', tracking)
        # Stream, explicit refresh, delegate and promoted purchase all record the
        # freshness of the exact CustomerInfo used for the ensuing derivation.
        self.assertEqual(source.count('recordCustomerInfoFreshness(info)'), 2)
        self.assertEqual(source.count('recordCustomerInfoFreshness(customerInfo)'), 2)

    def test_launch_and_foreground_fetch_current_without_changing_access_policy(self):
        source = MANAGER.read_text()
        configure = source.split('func configure()', 1)[1].split('private func listenCustomerInfo', 1)[0]
        self.assertIn('await self.refreshCustomerInfo()', configure)
        app = (APP_ROOT / 'aniccaios/aniccaiosApp.swift').read_text()
        active = app.split('.onChange(of: scenePhase)', 1)[1].split('.onOpenURL', 1)[0]
        self.assertIn('if phase == .active', active)
        self.assertIn('await SubscriptionManager.shared.refreshCustomerInfo()', active)
        refresh = source.split('func refreshCustomerInfo()', 1)[1].split('func syncNow()', 1)[0]
        self.assertIn('customerInfo(fetchPolicy: .fetchCurrent)', refresh)
        self.assertNotIn('isEntitlementStale', refresh)
        failure = refresh.split('} catch {', 1)[1]
        self.assertNotIn('recordCustomerInfoFreshness', failure)
        self.assertNotIn('updateSubscriptionInfo', failure)

    def test_no_notification_decoder_was_added_to_app(self):
        # Scope: executable app sources, not docs/tests. This cannot certify a
        # deployed external receiver; that remains false in the state fixture.
        for path in (APP_ROOT / 'aniccaios').rglob('*.swift'):
            source = path.read_text()
            for field in ('signedPayload', 'signedTransactionInfo', 'signedRenewalInfo'):
                self.assertNotIn(field, source, str(path))

    def test_state_does_not_promote_external_unknowns_to_passes(self):
        state = json.loads(STATE.read_text())
        self.assertTrue(state['inventory']['server_truth_path_decided'])
        for key in ('asc_or_dashboard_state_evidenced', 'relay_to_own_backend_evidenced',
                    'sandbox_and_production_both_covered'):
            self.assertFalse(state['inventory'][key])
        self.assertFalse(any(state['measurement'].values()))
        self.assertTrue(all(state['client_honesty'].values()))
        self.assertFalse(state['coverage']['test_notification_verified_end_to_end'])


if __name__ == '__main__':
    unittest.main()
