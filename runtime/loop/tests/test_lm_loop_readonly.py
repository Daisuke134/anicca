import unittest
import json
import subprocess
import tempfile
from pathlib import Path

from runtime.loop.lm_loop import _last_event, doctor_report, status_rows


REGISTRY = {"schema_version": 2, "loops": {"example": {
    "label": "ai.anicca.example", "domain": "earn", "entrypoint": "bin/example.sh",
    "cadence": {"start_interval_seconds": 60}, "effect_class": "application",
    "state_root": "~/.local/state/life-manager/example",
    "log_root": "~/.local/state/life-manager/example/logs",
    "cleanup": {"max_runs": 10, "max_age_days": 7},
    "provider_route": "shared-agent-runner",
}}}


class LmLoopReadonlyTest(unittest.TestCase):
    def test_status_separates_runtime_and_business_truth(self):
        events = {"example": {"timestamp": "2026-08-28T00:00:00Z", "status": "blocked",
                  "effect_status": "unknown", "blocker": "provider_capacity",
                  "release_sha": "a" * 40, "provider": "openai", "profile_alias": "acct2"}}
        row = status_rows(REGISTRY,
            loaded={"ai.anicca.example": {"pid": "123", "last_exit": "0"}}, disabled={},
            events=events, installed_releases={"ai.anicca.example": "b" * 40})[0]
        self.assertEqual((row["launchd_state"], row["pid"], row["last_exit"]),
                         ("loaded-running", "123", "0"))
        self.assertEqual((row["last_terminal_result"], row["effect_status"], row["blocker"]),
                         ("blocked", "unknown", "provider_capacity"))
        self.assertNotEqual(row["installed_release_sha"], row["event_release_sha"])

    def test_doctor_lists_unmanaged_and_missing(self):
        report = doctor_report(REGISTRY,
            installed_labels={"ai.anicca.example", "ai.anicca.unmanaged"},
            loaded_labels={"ai.anicca.example", "ai.anicca.loaded-only"},
            existing_entrypoints=set())
        self.assertEqual(report["unmanaged_labels"],
                         ["ai.anicca.loaded-only", "ai.anicca.unmanaged"])
        self.assertEqual(report["missing_entrypoints"], ["example:bin/example.sh"])
        self.assertFalse(report["ok"])

    def test_no_event_never_becomes_success_from_pid_or_exit(self):
        row = status_rows(REGISTRY, loaded={}, disabled={}, events={}, installed_releases={})[0]
        self.assertEqual(row["next_eligible_run"], "interval:60s")
        self.assertIsNone(row["last_terminal_result"])
        self.assertEqual(row["effect_status"], "unknown")

    def test_watch_snapshot_updates_from_event_envelopes(self):
        first = status_rows(REGISTRY, loaded={}, disabled={}, events={"example": {
            "status": "blocked", "effect_status": "unknown",
        }}, installed_releases={})
        second = status_rows(REGISTRY, loaded={}, disabled={}, events={"example": {
            "status": "pass", "effect_status": "verified",
        }}, installed_releases={})
        self.assertEqual(first[0]["last_terminal_result"], "blocked")
        self.assertEqual(second[0]["last_terminal_result"], "pass")
        self.assertEqual(second[0]["effect_status"], "verified")

    def test_wrapper_runs_outside_repository_working_directory(self):
        root = Path(__file__).resolve().parents[3]
        result = subprocess.run(
            [str(root / "bin/lm-loop"), "status", "fundraiser"],
            cwd="/tmp", capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)[0]["loop_id"], "fundraiser")

    def test_invalid_event_cannot_spoof_pass_or_verified_effect(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "events.jsonl").write_text('{"status":"pass","effect_status":"verified"}\n')
            self.assertIsNone(_last_event(str(root)))


if __name__ == "__main__":
    unittest.main()
