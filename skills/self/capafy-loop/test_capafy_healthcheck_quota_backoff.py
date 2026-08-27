#!/usr/bin/env python3
import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HEALTHCHECK = ROOT / "skills" / "self" / "capafy-loop" / "capafy-loop-healthcheck.sh"


class CapafyHealthcheckQuotaBackoffTest(unittest.TestCase):
    def run_healthcheck(self, error_class, incomplete_name, expected_return=0):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state_home = root / "state-home"
            marker = state_home / "state" / "capafy-autopublish" / ".capafy-healthy-pass"
            marker.parent.mkdir(parents=True)
            marker.touch()
            stale = time.time() - (31 * 60 * 60)
            os.utime(marker, (stale, stale))

            evidence = state_home / "state" / "agent-runner-evidence" / "capafy-marketplace" / "100-1"
            evidence.mkdir(parents=True)
            (evidence / "summary.json").write_text(
                json.dumps({"status": "failed", "finished_at": "2026-08-24T00:00:00Z"}),
                encoding="utf-8",
            )
            (evidence / "attempts.jsonl").write_text(
                json.dumps({"provider": "codex", "error_class": error_class}) + "\n",
                encoding="utf-8",
            )
            (evidence.parent / incomplete_name).mkdir()

            calls = root / "launchctl-calls"
            fake_bin = root / "bin"
            fake_bin.mkdir()
            launchctl = fake_bin / "launchctl"
            launchctl.write_text(
                "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$CAPAFY_TEST_CALLS\"\nexit 0\n",
                encoding="utf-8",
            )
            launchctl.chmod(0o755)

            env = os.environ | {
                "LIFE_MANAGER_STATE_HOME": str(state_home),
                "PATH": f"{fake_bin}:{os.environ['PATH']}",
                "CAPAFY_TEST_CALLS": str(calls),
            }
            result = subprocess.run(
                ["bash", str(HEALTHCHECK)], env=env, text=True, capture_output=True, check=False
            )

            self.assertEqual(result.returncode, expected_return, result.stderr)
            recorded = calls.read_text(encoding="utf-8")
            receipt_path = state_home / "state" / "capafy-provider-backoff.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.exists() else None
            return recorded, receipt

    def test_stale_marker_with_quota_does_not_kickstart(self):
            recorded, receipt = self.run_healthcheck("transient_quota", "101-2")
            self.assertNotIn("kickstart", recorded)
            self.assertEqual(receipt["error_class"], "transient_quota")
            self.assertGreater(receipt["next_eligible_at_epoch"], int(time.time()))

    def test_recent_incomplete_attempt_gets_grace_without_kickstart(self):
            recorded, _ = self.run_healthcheck("transient_unavailable", f"{int(time.time())}-2")
            self.assertNotIn("kickstart", recorded)

    def test_stale_nonquota_receipt_is_reported_without_kickstart(self):
            recorded, _ = self.run_healthcheck(
                "transient_unavailable", "101-2", expected_return=1)
            self.assertNotIn("kickstart", recorded)


if __name__ == "__main__":
    unittest.main()
