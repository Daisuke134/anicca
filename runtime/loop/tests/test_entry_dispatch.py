import json
import sys
import tempfile
import unittest
from pathlib import Path

from runtime.loop import entry_dispatch
from runtime.loop.entry_dispatch import command_for


class EntryDispatchTest(unittest.TestCase):
    def test_money_printer_bridge_uses_release_code_and_private_ssot_env(self):
        root = Path('/release')
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            private = home / '.local/share/anicca'
            private.mkdir(parents=True, mode=0o700)
            credentials = private / 'credentials.json'
            token = 'a' * 64
            credentials.write_text(json.dumps({
                'version': 1,
                'credentials': [{'service': 'life-manager-symphony-bridge', 'token': token}],
            }))
            credentials.chmod(0o600)

            try:
                command = command_for('money-printer-symphony-bridge', root, home)
            except ValueError:
                self.fail('money printer bridge dispatch is missing')
            self.assertEqual(command, [
                '/opt/homebrew/bin/node',
                '/release/apps/life-manager/scripts/money-printer-symphony-bridge.js',
            ])
            environment_for = getattr(entry_dispatch, 'environment_for', None)
            self.assertTrue(callable(environment_for), 'secure bridge environment loader is missing')
            base = {'PATH': '/usr/bin'}
            environment = environment_for('money-printer-symphony-bridge', home, base)
            self.assertEqual(base, {'PATH': '/usr/bin'})
            self.assertEqual(environment['LM_SYMPHONY_API_BASE_URL'],
                             'https://life-call-production.up.railway.app')
            self.assertEqual(environment['LM_RUNTIME_TENANT_ID'], 'webmcp-judge')
            self.assertEqual(environment['LM_SYMPHONY_BRIDGE_SECRET'], token)

    def test_affiliate_browsers_use_installed_cloakbrowser_python(self):
        root=Path('/release'); home=Path('/home')
        expected=home/'.openclaw/skills/_shared/venv-cloak/bin/python'
        for loop_id in ('affiliate-browser','affiliate-impact-browser','affiliate-x-browser'):
            command=command_for(loop_id,root,home)
            self.assertEqual(Path(command[0]),expected)
            self.assertEqual(command[1],str(root/'skills/affiliate/scripts/local_browser.py'))

    def test_life_manager_daily_driver_uses_release_dispatch_with_exact_argv(self):
        command = command_for('life-manager-daily-driver', Path('/release'), Path('/home'))
        self.assertEqual(command, [
            '/home/.openclaw/skills/_shared/venv-cloak/bin/python',
            '/release/skills/browser/cdp_persistent_context.py',
            '--profile', '/home/.cloak/profiles/daily-driver',
            '--port', '9222',
        ])

    def test_affiliate_subcommand_is_preserved_inside_release(self):
        root=Path('/release'); command=command_for('affiliate-composition',root,Path('/home'))
        self.assertEqual(command,[str(root/'skills/affiliate/affiliate'),'compose','wake'])

    def test_marketing_owner_state_is_outside_release(self):
        root=Path('/release'); command=command_for('marketing-owner-weekly',root,Path('/home'))
        self.assertEqual(command[:4],[sys.executable,str(root/'skills/earn/marketing-engine/report/owner_report_cli.py'),'sweep','--kind'])
        self.assertEqual(command[-1],'/home/.local/state/life-manager/marketing-engine')

    def test_unknown_loop_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'no dispatch command'):
            command_for('missing',Path('/release'),Path('/home'))

    def test_paid_lane_dispatches_complete_legacy_argv(self):
        command=command_for('hf-gig-paid-direct',Path('/release'),Path('/home'))
        self.assertEqual(command,[
            sys.executable,
            '/release/skills/earn/gig/scripts/gig_disk_guard.py',
            sys.executable,
            '/release/skills/earn/gig/scripts/paid_direct.py',
            '--output','/home/gig/evidence/paid-direct-live/latest.json',
            '--evidence-dir','/home/gig/evidence/paid-direct-live',
            '--projects-root','/home/gig/projects',
            '--lock-file','/home/gig/.paid-direct.lock',
            '--cdp-lock-dir','/home/gig/.cdp-gig.lock',
        ])

    def test_other_coconala_lanes_keep_production_modes(self):
        root=Path('/release'); home=Path('/home')
        apply=command_for('hf-gig-apply-direct',root,home)
        reply=command_for('hf-gig-reply-detector',root,home)
        storefront=command_for('hf-gig-storefront-direct',root,home)
        self.assertIn('--all-eligible',apply)
        self.assertEqual(reply[-5:],['--continuous','--poll-seconds','30','--workers','2'])
        self.assertEqual(storefront[-4:],['--effect','--auto-cadence','--full-interval-seconds','60'])

    def test_writer_jobs_keep_mutable_state_outside_release(self):
        root=Path('/release'); home=Path('/home')
        for loop_id in (
            'writer-claim-loop', 'writer-money-sync', 'writer-opportunity-discovery',
            'writer-opportunity-response', 'writer-report',
        ):
            command=command_for(loop_id,root,home)
            joined=' '.join(command)
            self.assertIn('/home/.local/state/life-manager/writer',joined)
            self.assertNotIn('/release/skills/writer-agent/state',joined)

    def test_lancers_browser_disables_code_sign_clone(self):
        script = Path(__file__).parents[3] / 'runtime/legacy/lancers-revenue-browser/run.sh'
        self.assertIn('--disable-features=MacAppCodeSignClone', script.read_text())


if __name__=='__main__':unittest.main()
