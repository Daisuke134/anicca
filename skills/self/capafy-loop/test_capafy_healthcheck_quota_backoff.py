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
    def test_stale_marker_with_quota_does_not_kickstart(self):
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
                json.dumps({"provider": "codex", "error_class": "transient_quota"}) + "\n"
                + json.dumps({"provider": "claude", "error_class": "transient_quota"}) + "\n",
                encoding="utf-8",
            )
            # A terminated newer run can leave an evidence directory without a
            # terminal summary. It must not hide the newest completed receipt.
            (evidence.parent / "101-2").mkdir()

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

            self.assertEqual(result.returncode, 0, result.stderr)
            recorded = calls.read_text(encoding="utf-8")
            self.assertNotIn("kickstart", recorded)
            receipt = json.loads(
                (state_home / "state" / "capafy-provider-backoff.json").read_text(encoding="utf-8")
            )
            self.assertEqual(receipt["error_class"], "transient_quota")
            self.assertGreater(receipt["next_eligible_at_epoch"], int(time.time()))


if __name__ == "__main__":
    unittest.main()
