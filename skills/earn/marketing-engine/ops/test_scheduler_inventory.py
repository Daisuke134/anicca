from __future__ import annotations

import importlib.util
import json
import plistlib
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("scheduler_inventory.py")
SPEC = importlib.util.spec_from_file_location("scheduler_inventory", MODULE_PATH)
assert SPEC and SPEC.loader
inventory = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = inventory
SPEC.loader.exec_module(inventory)


class SchedulerInventoryTest(unittest.TestCase):
    def test_launchd_record_resolves_larry_account_and_schedule(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plist = {
                "Label": "ai.anicca.larry-example",
                "ProgramArguments": ["bash", "runner.sh", "--account-key", "en-v1"],
                "StartCalendarInterval": [{"Hour": 9}, {"Hour": 20}],
            }
            (root / "ai.anicca.larry-example.plist").write_bytes(plistlib.dumps(plist))
            config = root / "larry.json"
            config.write_text(json.dumps({"accounts": {"en-v1": {
                "tiktok_connection": "cm12345678901234567890",
                "instagram_connection": None,
            }}}))
            launchctl = "PID\tStatus\tLabel\n-\t1\tai.anicca.larry-example\n"
            rows, invalid = inventory.launch_records(root, launchctl, config)
        self.assertEqual(invalid, [])
        self.assertEqual(rows[0]["integration_ids"], ["cm12345678901234567890"])
        self.assertEqual(rows[0]["schedule"]["entries"], [{"Hour": 9}, {"Hour": 20}])
        self.assertEqual(rows[0]["last_exit"], 1)
        self.assertEqual(rows[0]["disposition"], "retire")

    def test_marketing_measurement_is_migrate_not_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plist = {
                "Label": "ai.anicca.marketing-metrics",
                "ProgramArguments": ["python3", "metrics.py"],
                "StartInterval": 900,
            }
            (root / "metrics.plist").write_bytes(plistlib.dumps(plist))
            rows, _ = inventory.launch_records(root, "PID\tStatus\tLabel\n", root / "none")
        self.assertEqual(rows[0]["disposition"], "migrate")
        self.assertEqual(rows[0]["external_action"], "none")

    def test_openclaw_only_matches_job_name_not_prompt_noise(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "jobs.json"
            path.write_text(json.dumps({"jobs": [
                {"id": "1", "name": "unrelated", "enabled": True,
                 "payload": {"message": "never disable reelclaw"}},
                {"id": "2", "name": "reelclaw-live", "enabled": True,
                 "schedule": {"kind": "cron"},
                 "payload": {"message": "post cm12345678901234567890"}},
            ]}))
            rows = inventory.openclaw_records(path)
        self.assertEqual([row["id"] for row in rows], ["2"])
        self.assertTrue(rows[0]["enabled"])
        self.assertEqual(rows[0]["external_action"], "publish")

    def test_openclaw_monk_account_ids_come_from_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jobs = root / "jobs.json"
            jobs.write_text(json.dumps({"jobs": [{
                "id": "1", "name": "yangmun-monk-noon", "enabled": True,
                "payload": {"message": "run missing dispatcher path"},
            }]}))
            env = root / ".env"
            env.write_text(
                "POSTIZ_EN_TIKTOK_INTEGRATION=cm12345678901234567890\n"
                "POSTIZ_EN_IG_INTEGRATION=cm09876543210987654321\n"
                "POSTIZ_JP_TIKTOK_INTEGRATION=cm11111111111111111111\n"
                "SECRET=must-not-appear\n"
            )
            rows = inventory.openclaw_records(jobs, env)
        self.assertEqual(rows[0]["integration_ids"], [
            "cm09876543210987654321", "cm12345678901234567890",
        ])
        self.assertNotIn("must-not-appear", json.dumps(rows))

    def test_openclaw_live_gateway_overrides_stale_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "jobs.json"
            path.write_text(json.dumps({"jobs": [{
                "id": "2", "name": "reelclaw-live", "enabled": True,
                "payload": {"message": "old cm12345678901234567890"},
            }]}))
            rows = inventory.openclaw_records(path, live_get=lambda _: {
                "id": "2", "name": "reelclaw-live", "enabled": False,
                "payload": {"message": "new cm09876543210987654321"},
            })
        self.assertFalse(rows[0]["enabled"])
        self.assertTrue(rows[0]["store_enabled"])
        self.assertTrue(rows[0]["gateway_live_lookup"])
        self.assertEqual(rows[0]["integration_ids"], ["cm09876543210987654321"])

    def test_account_lookup_keeps_unknown_explicit(self):
        rows = [{"integration_ids": ["missing"]}]
        inventory.add_accounts(rows, {})
        self.assertIsNone(rows[0]["accounts"][0]["profile"])
        self.assertEqual(rows[0]["accounts"][0]["integration_id"], "missing")


if __name__ == "__main__":
    unittest.main()
