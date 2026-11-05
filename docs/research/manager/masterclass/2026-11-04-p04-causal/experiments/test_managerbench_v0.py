"""Small synthetic unit-test fixtures for ManagerBench; NOT real people."""
import unittest

from managerbench_v0 import (binary_metrics, continuous_metrics, model_card,
                             randomized_itt, verify_disjoint, verify_prediction_cutoff)


class ManagerBenchSoftwareTests(unittest.TestCase):
    def test_disjoint_pass(self):
        verify_disjoint([{"participant_id":"a"}], [{"participant_id":"b"}],
                        [{"participant_id":"c"}])

    def test_leakage_rejected(self):
        with self.assertRaisesRegex(ValueError, "leakage"):
            verify_disjoint([{"participant_id":"a"}], [{"participant_id":"b"}],
                            [{"participant_id":"a"}])

    def test_split_missing_rejected(self):
        with self.assertRaises(ValueError):
            verify_disjoint([{}], [], [])

    def test_time_forward_pass(self):
        verify_prediction_cutoff([{"available_until":"2026-01-01T00:00:00Z",
                                   "target_at":"2026-01-01T00:01:00Z",
                                   "prediction":0.5}])

    def test_time_lookahead_rejected(self):
        with self.assertRaisesRegex(ValueError,"lookahead"):
            verify_prediction_cutoff([{"available_until":"2026-01-01T00:02:00Z",
                                       "target_at":"2026-01-01T00:01:00Z",
                                       "prediction":0.5}])

    def test_binary_known_scores(self):
        r = binary_metrics([0,1],[0.2,0.8])
        self.assertAlmostEqual(r["brier"], .04)
        self.assertAlmostEqual(r["log_loss"], 0.2231435513142097)
        self.assertEqual(r["n"],2)

    def test_binary_probabilities_bounded(self):
        with self.assertRaises(ValueError):
            binary_metrics([0],[1.1])
        with self.assertRaises(ValueError):
            binary_metrics([0],[float("nan")])

    def test_continuous_known_scores(self):
        r = continuous_metrics([0, 2], [1, 1])
        self.assertEqual(r["rmse"],1)
        self.assertEqual(r["mae"],1)

    def test_continuous_nonfinite_rejected(self):
        with self.assertRaises(ValueError):
            continuous_metrics([1], [float("inf")])

    def test_randomized_itt(self):
        rows=[{"design":"randomized","assigned":0,"outcome":1},
              {"design":"randomized","assigned":0,"outcome":3},
              {"design":"randomized","assigned":1,"outcome":4},
              {"design":"randomized","assigned":1,"outcome":6}]
        r=randomized_itt(rows)
        self.assertEqual(r["itt_difference"],3)

    def test_observational_not_labeled_itt(self):
        with self.assertRaisesRegex(ValueError,"nonrandomized"):
            randomized_itt([{"design":"observational","assigned":0,"outcome":1},
                            {"design":"observational","assigned":1,"outcome":2}])

    def test_requires_comparator(self):
        with self.assertRaisesRegex(ValueError, "both assignment arms"):
            randomized_itt([{"design":"randomized","assigned":1,"outcome":2}])

    def test_fixture_not_empirical(self):
        card=model_card("dummy", "test fixture only", "holdout",
                        {"brier":0.04})
        self.assertEqual(card["source"],"software_fixture")
        self.assertFalse(card["causal_effect_established"])


if __name__ == "__main__":
    unittest.main()
