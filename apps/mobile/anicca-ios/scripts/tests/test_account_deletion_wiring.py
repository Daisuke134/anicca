"""Account-deletion App Review gate contracts for the production Settings flow."""

from pathlib import Path
import re
import unittest


APP_ROOT = Path(__file__).resolve().parents[2]
SETTINGS = APP_ROOT / "aniccaios/Views/Feed/SettingsSheet.swift"
CONFIG = APP_ROOT / "aniccaios/Config.swift"
APP_STATE = APP_ROOT / "aniccaios/AppState.swift"


class AccountDeletionWiringTests(unittest.TestCase):
    def setUp(self):
        self.settings = SETTINGS.read_text(encoding="utf-8")

    def test_settings_exposes_a_destructive_confirmed_delete_action(self):
        for required in (
            'showDeleteAccountConfirmation = true',
            'accessibilityIdentifier("settings-delete-account")',
            'isPresented: $showDeleteAccountConfirmation',
            'Button(String(localized: "settings_delete_account_confirm"), role: .destructive)',
            'deleteAccount()',
        ):
            self.assertIn(required, self.settings)

    def test_delete_calls_authenticated_mobile_account_endpoint(self):
        config = CONFIG.read_text(encoding="utf-8")
        self.assertIn('static var accountDeletionURL: URL', config)
        self.assertIn('appendingPathComponent("mobile/account")', config)
        body = self.settings.split("private func deleteAccount()", 1)[1]
        for required in (
            'URLRequest(url: AppConfig.accountDeletionURL)',
            'request.httpMethod = "DELETE"',
            'setAuthHeaders(for: &request)',
            'request.setValue(credentials.userId, forHTTPHeaderField: "user-id")',
        ):
            self.assertIn(required, body)

    def test_local_account_is_wiped_only_after_server_success(self):
        body = self.settings.split("private func deleteAccount()", 1)[1]
        success_guard = re.search(
            r"guard response\.statusCode == 204 \|\| response\.statusCode == 200 else \{.*?\n\s*\}",
            body,
            re.DOTALL,
        )
        self.assertIsNotNone(success_guard)
        wipe_position = body.index("AppState.shared.signOutAndWipe()")
        self.assertGreater(wipe_position, success_guard.end())
        catch = body.split("} catch {", 1)[1]
        self.assertNotIn("signOutAndWipe", catch)

    def test_complete_wipe_removes_refresh_and_app_group_identity(self):
        state = APP_STATE.read_text(encoding="utf-8")
        wipe = state.split("func signOutAndWipe()", 1)[1].split("private func loadUserCredentials", 1)[0]
        self.assertIn('KeychainService.delete(account: "rt")', wipe)
        self.assertIn('AppGroup.userDefaults.removeObject(forKey: "userId")', wipe)
        self.assertIn('AppGroup.userDefaults.removeObject(forKey: "deviceId")', wipe)


if __name__ == "__main__":
    unittest.main()
