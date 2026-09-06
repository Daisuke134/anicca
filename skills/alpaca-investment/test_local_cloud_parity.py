"""L04.8: the Local Python and Cloud Node adapters share one sealed parity contract."""

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))

from parity_core import run_parity_core


class LocalCloudParityTest(unittest.TestCase):
    def test_sealed_fixture_matches_cloud_exactly(self):
        fixture_path = ROOT / "fixtures/preapproval-replay.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        local = run_parity_core(fixture)
        script = """
const fs = require('node:fs');
const { runParityCore } = require('./apps/life-manager/lib/investment-parity-core.js');
const fixture = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
process.stdout.write(JSON.stringify(runParityCore(fixture)));
"""
        cloud = json.loads(subprocess.check_output(
            ["node", "-e", script, str(fixture_path)], cwd=REPO, text=True
        ))
        expected = json.loads((
            REPO / "apps/life-manager/lib/fixtures/investment-parity-expected.json"
        ).read_text(encoding="utf-8"))
        self.assertEqual(local, cloud)
        self.assertEqual(local, expected)
        self.assertEqual(local["decision"], "NO_TRADE")
        self.assertEqual(local["risk"], {
            "approved": False, "effect_permission": "none", "gate": "model_no_trade"
        })
        self.assertEqual(len(local["core_digest"]), 64)
        self.assertEqual(len(local["idempotency_key"]), 64)

    def test_cloud_mismatch_fails_closed_before_receipt(self):
        source = (REPO / "apps/life-manager/lib/investment-dry-run.js").read_text(encoding="utf-8")
        self.assertIn("assertLocalCloudParity", source)
        self.assertLess(source.index("assertLocalCloudParity"), source.index("completeJob"))


if __name__ == "__main__":
    unittest.main()
