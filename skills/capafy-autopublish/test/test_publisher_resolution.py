import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest

MODULE = Path(__file__).parents[1] / 'scripts/publisher_resolution.py'
TENANT = 'lm_11111111-1111-4111-8111-111111111111'
SUBJECT = '2060981302278778880'
TOKEN = 'am_sk_fixturetoken1234567890'
BINDING = {'tenantId': TENANT, 'provider': 'capafy', 'subjectId': SUBJECT,
           'credentialRef': 'capafy-publisher-slot:v1',
           'browserSessionRef': 'tenant-browser:v1'}


def load_module():
    spec = importlib.util.spec_from_file_location('publisher_resolution', MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PublisherResolutionTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.raw = tempfile.mkdtemp()
        self.home = Path(self.raw) / TENANT
        self.publisher = self.home / 'runtime/capafy-publisher'
        (self.home / 'secrets').mkdir(parents=True, mode=0o700)

    def write_slot(self, **overrides):
        slot = {'accessToken': TOKEN, 'userId': SUBJECT,
                'email': 'publisher@example.com', 'name': 'Fixture',
                'hostOpenRouterKey': 'sk-or-fixture',
                'browserAuthState': {'cookies': [{'name': 's', 'value': 'x'}],
                                     'origins': []}}
        slot.update(overrides)
        path = self.home / 'secrets/capafy-publisher.json'
        path.write_text(json.dumps(slot))
        path.chmod(0o600)
        return path

    def fake_http(self, profile=None, account=None):
        def get(path, token):
            self.assertEqual(token, TOKEN)
            if path.endswith('/profile'):
                return profile if profile is not None else {'userId': SUBJECT}
            return account if account is not None else {'email': 'publisher@example.com'}
        return get

    def resolve(self, **kwargs):
        kwargs.setdefault('state_home', self.home)
        kwargs.setdefault('publisher_home', self.publisher)
        kwargs.setdefault('owner', os.geteuid())
        kwargs.setdefault('http_get', self.fake_http())
        return self.module.resolve_publisher(BINDING, **kwargs)

    def test_happy_path_materializes_factory_state_without_secrets_in_receipt(self):
        self.write_slot()
        receipt = self.resolve()
        store = json.loads((self.publisher / 'config.json').read_text())
        self.assertEqual(store, {'access_token': TOKEN, 'user_id': SUBJECT,
                                 'email': 'publisher@example.com', 'name': 'Fixture'})
        env_text = (self.home / '.env').read_text()
        self.assertIn('CAPAFY_ACCESS_TOKEN=' + TOKEN, env_text)
        self.assertIn('CAPAFY_HOST_OPENROUTER_KEY=sk-or-fixture', env_text)
        self.assertTrue((self.publisher / 'browser-auth-state.json').is_file())
        for path in (self.publisher / 'config.json', self.home / '.env',
                     self.publisher / 'resolution.json'):
            self.assertEqual(stat.S_IMODE(path.lstat().st_mode), 0o600)
        receipt_text = (self.publisher / 'resolution.json').read_text()
        self.assertNotIn(TOKEN, receipt_text)
        self.assertNotIn('sk-or-fixture', receipt_text)
        self.assertTrue(receipt['accountVerified'])
        self.assertTrue(receipt['browserSeeded'])

    def test_subject_mismatch_fails_closed(self):
        self.write_slot(userId='999')
        with self.assertRaisesRegex(self.module.ResolutionError, 'binding_subject_mismatch'):
            self.resolve()
        self.assertFalse((self.publisher / 'config.json').exists())

    def test_unknown_refs_fail_closed(self):
        self.write_slot()
        for key, value in (('credentialRef', 'other:v1'), ('browserSessionRef', 'other:v1')):
            binding = dict(BINDING, **{key: value})
            with self.assertRaises(self.module.ResolutionError):
                self.module.resolve_publisher(
                    binding, state_home=self.home, publisher_home=self.publisher,
                    owner=os.geteuid(), http_get=self.fake_http())

    def test_missing_slot_fails_closed(self):
        with self.assertRaisesRegex(self.module.ResolutionError, 'slot_unavailable'):
            self.resolve()

    def test_unverifiable_account_removes_materials(self):
        self.write_slot()
        with self.assertRaisesRegex(self.module.ResolutionError, 'account_verification_failed'):
            self.resolve(http_get=self.fake_http(profile={'userId': 'someone-else'}))
        self.assertFalse((self.publisher / 'config.json').exists())
        self.assertFalse((self.home / '.env').exists())

    def test_http_failure_is_unavailable_not_failed(self):
        self.write_slot()
        def broken(path, token):
            raise OSError('network down')
        with self.assertRaisesRegex(self.module.ResolutionError, 'account_verification_unavailable'):
            self.resolve(http_get=broken)


if __name__ == '__main__':
    unittest.main()
