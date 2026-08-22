from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SKILL_ROOT / "scripts" / "agent_checkpoint.py"


def load_module():
    spec = importlib.util.spec_from_file_location("agent_checkpoint", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AgentCheckpointTests(unittest.TestCase):
    def test_restart_uses_last_transition_without_replaying_completed_effect(self) -> None:
        self.assertTrue(MODULE_PATH.is_file(), f"missing checkpoint store: {MODULE_PATH}")
        module = load_module()
        with tempfile.TemporaryDirectory() as root:
            state = Path(root)
            checkpoint = {
                "goal_id": "goal-1",
                "job_id": "job-1",
                "stage": "X_POST",
                "proposed_action": {"command": "x post publish"},
                "tool_attempt": {"attempt": 1, "effect_id": "effect-1"},
                "observation": {"state": "X_LIVE", "readback_status": "EXACT"},
                "effect_certainty": "EFFECT_CONFIRMED",
                "next_due_at": None,
            }
            first = module.commit(state, checkpoint)
            duplicate = module.commit(state, checkpoint)

            restarted = load_module()
            loaded = restarted.load(state)
            self.assertEqual(loaded, first)
            self.assertEqual(duplicate, first)
            self.assertEqual(restarted.resume(loaded), {
                "state": "ADVANCE",
                "replay_proposed_action": False,
                "transition_id": first["transition_id"],
            })
            history = (state / "agent-checkpoints.jsonl").read_text().splitlines()
            self.assertEqual(len(history), 1)
            self.assertEqual(json.loads(history[0]), first)

    def test_unknown_effect_restarts_with_readback_only(self) -> None:
        self.assertTrue(MODULE_PATH.is_file(), f"missing checkpoint store: {MODULE_PATH}")
        module = load_module()
        with tempfile.TemporaryDirectory() as root:
            state = Path(root)
            saved = module.commit(state, {
                "goal_id": "goal-1", "job_id": "job-1", "stage": "PROVIDER_WRITE",
                "proposed_action": {"command": "programs acquire-placement-link"},
                "tool_attempt": {"attempt": 1}, "observation": {"state": "TIMEOUT"},
                "effect_certainty": "UNKNOWN", "next_due_at": "2026-08-23T00:00:00Z",
            })
            self.assertEqual(module.resume(module.load(state)), {
                "state": "READBACK_ONLY",
                "replay_proposed_action": False,
                "transition_id": saved["transition_id"],
            })

    def test_corrupt_tail_fails_closed_instead_of_rolling_back(self) -> None:
        self.assertTrue(MODULE_PATH.is_file(), f"missing checkpoint store: {MODULE_PATH}")
        module = load_module()
        with tempfile.TemporaryDirectory() as root:
            state = Path(root)
            module.commit(state, {
                "goal_id": "goal-1", "job_id": "job-1", "stage": "X_POST",
                "proposed_action": {"command": "x post publish"},
                "tool_attempt": {"attempt": 1}, "observation": {"state": "X_LIVE"},
                "effect_certainty": "EFFECT_CONFIRMED", "next_due_at": None,
            })
            with (state / "agent-checkpoints.jsonl").open("a") as stream:
                stream.write('{"truncated":')
            with self.assertRaises(module.JobStateError):
                module.load(state)


if __name__ == "__main__":
    unittest.main()
