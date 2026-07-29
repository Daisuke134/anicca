import unittest

from job_search_loop.experiments import (
    ExperimentResult,
    evaluate_candidate,
    evidence_hash,
)


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.baseline = {
            "auto_apply_threshold": 75,
            "compensation_floor_jpy": 7_000_000,
        }

    def test_candidate_must_change_exactly_one_strategy_field(self):
        candidate = {
            "auto_apply_threshold": 70,
            "compensation_floor_jpy": 8_000_000,
        }
        result = evaluate_candidate(
            self.baseline,
            candidate,
            baseline_resolved=100,
            baseline_positive=5,
            candidate_resolved=100,
            candidate_positive=20,
            replay_violations=0,
        )
        self.assertEqual(result.decision, "rejected")
        self.assertEqual(result.reason, "candidate_must_change_exactly_one_field")

    def test_fewer_than_ten_resolved_candidate_applications_is_inconclusive(self):
        result = evaluate_candidate(
            self.baseline,
            {**self.baseline, "auto_apply_threshold": 70},
            baseline_resolved=100,
            baseline_positive=5,
            candidate_resolved=9,
            candidate_positive=5,
            replay_violations=0,
        )
        self.assertEqual(result.decision, "inconclusive")
        self.assertEqual(result.reason, "insufficient_resolved_applications")

    def test_any_replay_safety_violation_rejects_candidate(self):
        result = evaluate_candidate(
            self.baseline,
            {**self.baseline, "auto_apply_threshold": 70},
            baseline_resolved=100,
            baseline_positive=5,
            candidate_resolved=100,
            candidate_positive=20,
            replay_violations=1,
        )
        self.assertEqual(result.decision, "rejected")
        self.assertEqual(result.reason, "replay_safety_violation")

    def test_candidate_promotes_only_when_confidence_intervals_separate(self):
        promoted = evaluate_candidate(
            self.baseline,
            {**self.baseline, "auto_apply_threshold": 70},
            baseline_resolved=100,
            baseline_positive=5,
            candidate_resolved=100,
            candidate_positive=20,
            replay_violations=0,
        )
        self.assertEqual(promoted.decision, "promote")
        self.assertGreater(
            promoted.candidate_interval[0], promoted.baseline_interval[1]
        )

        inconclusive = evaluate_candidate(
            self.baseline,
            {**self.baseline, "auto_apply_threshold": 70},
            baseline_resolved=100,
            baseline_positive=10,
            candidate_resolved=100,
            candidate_positive=14,
            replay_violations=0,
        )
        self.assertEqual(inconclusive.decision, "inconclusive")
        self.assertEqual(inconclusive.reason, "confidence_intervals_overlap")

    def test_evidence_hash_is_stable_and_covers_decision(self):
        result = ExperimentResult(
            decision="promote",
            reason="candidate_interval_above_baseline",
            changed_field="auto_apply_threshold",
            baseline_interval=(0.01, 0.02),
            candidate_interval=(0.03, 0.04),
        )
        self.assertEqual(evidence_hash(result), evidence_hash(result))
        changed = ExperimentResult(
            decision="rejected",
            reason=result.reason,
            changed_field=result.changed_field,
            baseline_interval=result.baseline_interval,
            candidate_interval=result.candidate_interval,
        )
        self.assertNotEqual(evidence_hash(result), evidence_hash(changed))


if __name__ == "__main__":
    unittest.main()
