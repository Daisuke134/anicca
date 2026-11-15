"""Source-boundary regressions; these do not substitute for XCTest/StoreKit runs."""
from pathlib import Path
import os
import unittest

ROOT = Path(os.environ.get('ANICCA_SOURCE_ROOT', Path(__file__).resolve().parents[2] / 'aniccaios'))

def source(path):
    return (ROOT / path).read_text()

class AuthPurchaseLifecycleTests(unittest.TestCase):
    def test_native_apple_entry_is_reachable(self):
        view = source('Views/Feed/SettingsSheet.swift')
        self.assertIn('SignInWithAppleButton(.signIn, onRequest: auth.configure)', view)
        self.assertIn('auth.completeSignIn(result: result)', view)

    def test_account_deletion_waits_for_authenticated_server_receipt(self):
        view = source('Views/Feed/SettingsSheet.swift')
        auth = source('Authentication/AuthCoordinator.swift')
        self.assertIn('await auth.deleteAccount()', view)
        delete = auth.split('func deleteAccount()', 1)[1].split('func startObservingCredentials', 1)[0]
        self.assertIn('try await NetworkSessionManager.shared.setAuthHeaders', delete)
        self.assertIn('statusCode == 204', delete)
        self.assertLess(delete.index('statusCode == 204'), delete.index('signOutAndWipe()'))

    def test_credentials_never_written_to_defaults(self):
        state = source('AppState.swift')
        self.assertNotIn('defaults.set(data, forKey: userCredentialsKey)', state)
        for key in ['userCredentialsKey', '"rt"', '"appleFirstGrant"']:
            self.assertIn(f'KeychainService.delete(account: {key})', state)
        self.assertIn('AppGroup.userDefaults.removeObject(forKey: "userId")', state)

    def test_apple_code_and_subject_are_kept_distinct_from_backend_id(self):
        auth = source('Authentication/AuthCoordinator.swift')
        self.assertIn('credential.authorizationCode', auth)
        self.assertIn('"authorization_code": authorizationCode', auth)
        self.assertIn('credentials.appleUserId = grant.userId', auth)
        self.assertIn('credentialState(forUserID: appleUserID)', auth)
        self.assertIn('credentialRevokedNotification', auth)
        self.assertIn('.canceled ? "cancelled" : "failed"', auth)

    def test_legacy_reauth_does_not_wipe_profile(self):
        state = source('AppState.swift')
        migration = state.split('if credentials.appleUserId == nil {', 1)[1].split('return .signedOut', 1)[0]
        self.assertNotIn('signOutAndWipe', migration)
        self.assertIn('credentials.jwtAccessToken = nil', migration)
        self.assertIn('persistAuthenticatedCredentials(credentials)', migration)

    def test_launch_observation_does_not_depend_on_paywall(self):
        app = source('AppDelegate.swift')
        self.assertIn('SubscriptionManager.shared.configure()', app)
        self.assertIn('AuthCoordinator.shared.startObservingCredentials()', app)
        manager = source('Services/SubscriptionManager.swift')
        self.assertIn('customerInfoTask = Task { await listenCustomerInfo() }', manager)
        self.assertIn('purchasesAreCompletedBy: .revenueCat', manager)
        self.assertNotIn('transaction.finish()', manager)

    def test_foreground_reconciles_offer_redemptions(self):
        app = source('aniccaiosApp.swift')
        self.assertIn('.onChange(of: scenePhase)', app)
        self.assertIn('await AuthCoordinator.shared.validateCredentialState()', app)
        self.assertIn('await SubscriptionManager.shared.syncNow()', app)
        manager = source('Services/SubscriptionManager.swift')
        self.assertIn('let info = try await Purchases.shared.syncPurchases()', manager)

    def test_identity_failure_cannot_apply_old_account_entitlements(self):
        manager = source('Services/SubscriptionManager.swift')
        self.assertIn('return Purchases.shared.isAnonymous', manager)
        self.assertIn('guard identityMatchesSession else { continue }', manager)
        self.assertIn('guard identityMatchesSession, Purchases.shared.appUserID == userID', manager)
        self.assertIn('pendingPromotedPurchases.append((product, purchase))', manager)

    def test_delegate_does_not_recursively_resync_receipts(self):
        delegate = source('Services/SubscriptionManager.swift').split('extension SubscriptionManager: PurchasesDelegate', 1)[1].split('readyForPromotedProduct', 1)[0]
        self.assertNotIn('await syncNow()', delegate)
        self.assertIn('await syncBackendUsage()', delegate)

    def test_late_refresh_cannot_restore_signed_out_tokens(self):
        network = source('Services/NetworkSessionManager.swift')
        self.assertIn('KeychainService.load(account: "rt") == rtData', network)
        self.assertNotIn('else if let at = credentials.jwtAccessToken', network)

if __name__ == '__main__':
    unittest.main()
