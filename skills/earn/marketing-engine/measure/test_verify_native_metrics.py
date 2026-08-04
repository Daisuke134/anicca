from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("verify_native_metrics.py")
SPEC = importlib.util.spec_from_file_location("verify_native_metrics", MODULE_PATH)
assert SPEC and SPEC.loader
verify = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verify
SPEC.loader.exec_module(verify)


class VerifyNativeMetricsTest(unittest.TestCase):
    def test_exact_zero_is_a_real_match(self):
        result = verify.compare_fields(
            {"views": 0, "likes": 0},
            {"views": 0, "likes": 0},
            ("views", "likes"),
        )
        self.assertEqual(result["comparable_fields"], ["views", "likes"])
        self.assertEqual(result["mismatches"], [])

    def test_hidden_public_field_is_excluded_not_counted_as_match(self):
        result = verify.compare_fields(
            {"views": 0, "likes": 0},
            {"views": 0, "likes": None},
            ("views", "likes"),
        )
        self.assertEqual(result["comparable_fields"], ["views"])
        self.assertEqual(result["excluded_fields"], {"likes": "field_unavailable_in_one_source"})
        self.assertEqual(result["mismatches"], [])

    def test_real_difference_is_a_mismatch(self):
        result = verify.compare_fields(
            {"views": 12}, {"views": 13}, ("views",)
        )
        self.assertEqual(
            result["mismatches"],
            [{"field": "views", "primary": 12, "independent": 13}],
        )

    def test_gate_requires_ten_identities_one_field_each_and_zero_mismatch(self):
        records = [
            {
                "identity_match": True,
                "comparison": {
                    "comparable_fields": ["views"],
                    "mismatches": [],
                    "excluded_fields": {},
                },
            }
            for _ in range(10)
        ]
        report = verify.summarize(records)
        self.assertTrue(report["passes_gate"])
        records[0]["comparison"]["mismatches"] = [
            {"field": "views", "primary": 1, "independent": 2}
        ]
        self.assertFalse(verify.summarize(records)["passes_gate"])


if __name__ == "__main__":
    unittest.main()
