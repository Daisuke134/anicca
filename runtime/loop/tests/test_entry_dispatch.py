import sys
import unittest
from pathlib import Path

from runtime.loop.entry_dispatch import command_for


class EntryDispatchTest(unittest.TestCase):
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


if __name__=='__main__':unittest.main()
