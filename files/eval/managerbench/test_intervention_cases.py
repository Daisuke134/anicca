import importlib.util
import tempfile
import json
import unittest
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("check", HERE / "check_intervention_cases.py")
check = importlib.util.module_from_spec(spec); spec.loader.exec_module(check)


class InterventionCasesTest(unittest.TestCase):
    def test_existing_manifest_is_zero(self):
        count, errors = check.inspect([HERE / "restraint-v1.json"])
        self.assertEqual((0, []), (count, errors))

    def test_valid_and_missing_propensity(self):
        good = {"case_id":"c1", "person_id":"p1", "decision_point_at":"2026-11-14T00:00:00Z",
                "available":True, "personal_history":{"opens_7d":2}, "treatment_assigned":True,
                "assigned_probability":0.5, "intervention_id":"i1", "delivery_id":"d1",
                "proximal_outcome":1, "outcome_window_sec":3600}
        self.assertIsNone(check.validate(good))
        del good["assigned_probability"]
        self.assertIn("assigned_probability", check.validate(good))


if __name__ == "__main__": unittest.main()
