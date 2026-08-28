import tempfile
import unittest
from pathlib import Path

from runtime.loop.runtime_event import append_runtime_event, build_install_event, build_runtime_event, validate_runtime_event


BASE = {
    "version": 1, "event_id": "a" * 24, "timestamp": "2026-08-28T00:00:00+00:00",
    "loop_id": "example", "domain": "earn", "run_id": "run-1", "phase": "report",
    "status": "pass", "release_sha": "b" * 40, "provider": "openai",
    "profile_alias": "acct2", "effect_class": "application",
    "effect_status": "unknown", "blocker": None,
    "evidence_refs": ["agent-runner://example/run-1/summary.json"],
}


class RuntimeEventTest(unittest.TestCase):
    def test_valid_event_appends_one_private_jsonl_row(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            append_runtime_event(path, BASE)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(len(path.read_text().splitlines()), 1)

    def test_same_event_id_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            append_runtime_event(path, BASE)
            append_runtime_event(path, BASE)
            self.assertEqual(len(path.read_text().splitlines()), 1)

    def test_unknown_and_secret_values_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            validate_runtime_event({**BASE, "model": "gpt"})
        with self.assertRaisesRegex(ValueError, "secret-like"):
            validate_runtime_event({**BASE, "blocker": "TOKEN=do-not-store"})
        with self.assertRaisesRegex(ValueError, "secret-like"):
            validate_runtime_event({**BASE, "evidence_refs": ["/Users/operator/private.json"]})
        with self.assertRaisesRegex(ValueError, "secret-like"):
            validate_runtime_event({**BASE, "blocker": "sk-abcdefghijklmnopqrstuvwxyz012345"})

    def test_disk_cleanup_loop_id_is_not_mistaken_for_api_key(self):
        event = {
            **BASE,
            "loop_id": "life-manager-disk-cleanup",
            "evidence_refs": ["lm-loop://life-manager-disk-cleanup/install/summary.json"],
        }
        self.assertEqual(validate_runtime_event(event), event)

    def test_runner_success_does_not_claim_external_effect(self):
        event = build_runtime_event(
            loop_id="example", domain="earn", run_id="run-1", release_sha="b" * 40,
            provider="openai", profile_alias="acct2", effect_class="application",
            succeeded=True, blocker=None,
        )
        self.assertEqual(event["status"], "pass")
        self.assertEqual(event["effect_status"], "unknown")
        self.assertEqual(event["evidence_refs"], ["agent-runner://example/run-1/summary.json"])

    def test_no_effect_uses_not_applicable(self):
        event = build_runtime_event(
            loop_id="example", domain="system", run_id="run-1", release_sha="b" * 40,
            provider="deterministic", profile_alias=None, effect_class="none",
            succeeded=False, blocker="runner_failed",
        )
        self.assertEqual(event["effect_status"], "not_applicable")
        self.assertEqual(event["status"], "fail")

    def test_install_event_is_plan_truth_not_external_effect_truth(self):
        event = build_install_event(
            loop_id="example", domain="earn", release_sha="b" * 40,
            provider="shared-agent-runner", effect_class="application")
        self.assertEqual((event["phase"], event["status"], event["effect_status"]),
                         ("plan", "pass", "unknown"))
        self.assertEqual(event["evidence_refs"], ["lm-loop://example/install/summary.json"])


if __name__ == "__main__":
    unittest.main()
