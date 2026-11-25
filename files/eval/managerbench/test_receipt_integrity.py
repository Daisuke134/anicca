"""Fail-closed synthetic receipt regressions (no personal data or model calls)."""
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("managerbench_guard", HERE / "run.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def mame(override=None):
    row = {"n_correct": 1, "n_human_non_tied": 2, "strict_accuracy": .5,
           "choices": {"a": "A", "b": "B"}, "n_total": 2, "mean_regret": .1}
    row.update(override or {})
    return {"conditions": {}, "case_manifest_test_sha256": "synthetic",
            "test": {"synthetic": row}}


def sample_reads():
    befm = {"scores": {"model_strict_win_accuracy_including_invalid": .5,
                       "mean_model_regret_invalid_counted": .1,
                       "baseline_strict_win_accuracy": .5,
                       "mean_baseline_regret": .1, "n_total": 2,
                       "n_human_non_tied": 2, "n_model_invalid": 0}}
    prior = {"dataset_revision": "fixture", "evaluator_revision": "fixture",
             "definition": {}, "num_samples_per_game": 1, "results": []}
    metadata = {"dataset_revision": "fixture", "evaluator_revision": "fixture",
                "github_actions": {}, "inference_settings_completed_llm_arms": {}}
    final = {"receipts": [], "dataset_revision": "fixture",
             "evaluator_revision": "fixture", "coverage": {},
             "measured_at_utc": "fixture", "session_end": {}, "results": {}}
    final68 = {**final, "supersedes": {}, "completion_source": {},
               "github_actions_completion": {}}
    return [mame(), mame(), mame(), befm, prior, metadata, {}, final, final68]


class IntegrityTest(unittest.TestCase):
    def check_bad_first(self, update, fragment):
        seq = [mame(update), RuntimeError("guard escaped to next receipt")]
        with patch.object(runner, "read", side_effect=seq):
            with self.assertRaisesRegex(ValueError, fragment):
                runner.aggregate(Path("/synthetic-not-used"))

    def test_mamere_accuracy_mismatch(self):
        self.check_bad_first({"strict_accuracy": .6}, "accuracy")

    def test_mamere_choice_count_mismatch(self):
        self.check_bad_first({"n_total": 3}, "choice")

    def test_mamere_illegal_choice(self):
        self.check_bad_first({"choices": {"a": "A", "b": "C"}}, "choice")

    def test_boolean_denominator_is_not_an_observation(self):
        self.check_bad_first({"n_correct": 1, "n_human_non_tied": 1,
                              "strict_accuracy": 1.0, "n_total": True,
                              "choices": {"a": "A"}}, "denominator")

    def test_legacy_full_shard_mismatch(self):
        reads = sample_reads()
        reads[6] = {"bad": {"status": "OK", "shards_done": 1,
                            "shards_expected": 2, "metadata": {},
                            "n": 2, "n_failed_parse": 0, "n_valid": 2,
                            "task": "seq_surv_resp", "arm": "fixture",
                            "metrics_official": {}}}
        with patch.object(runner, "read", side_effect=reads):
            with self.assertRaisesRegex(ValueError, "shard"):
                runner.aggregate(Path("/synthetic-not-used"))

    def test_final68_completion_denominator_mismatch(self):
        reads = sample_reads()
        reads[8]["results"] = {
            "bad": {"status": "OK", "n_receipted": 499, "n_expected": 500,
                    "n": 500, "task": "seq_surv_resp", "arm": "fixture",
                    "metrics_official": {}, "metadata": {}}}
        with patch.object(runner, "read", side_effect=reads):
            with self.assertRaisesRegex(ValueError, "receipt"):
                runner.aggregate(Path("/synthetic-not-used"))


if __name__ == "__main__":
    unittest.main()
