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


if __name__=='__main__':unittest.main()
