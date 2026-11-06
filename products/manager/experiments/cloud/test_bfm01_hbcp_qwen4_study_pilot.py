"""BFM01 scorer contract tests: small fake rows for software correctness ONLY."""
import unittest
from bfm01_hbcp_qwen4_study_pilot import (
    LABEL, parse_percentage, present_features, create_prompt, study_split
)


class RealSourceEvaluationContractTests(unittest.TestCase):
    def test_percentage_parsing(self):
        for v, expected in [("8%", 8), ("8.25", 8.25), ("100", 100), ("0", 0)]:
            self.assertEqual(parse_percentage(v), expected)

    def test_reject_invalid_scores(self):
        for v in ("-20", "101", "about 8", "", "8% or 9%", "nan"):
            self.assertIsNone(parse_percentage(v))

    def test_study_holdout_never_repeated(self):
        rows = []
        for i in range(40):
            rows.append({"doc": "study-"+str(i), "doc_id": str(i), "arm_id": "a",
                         LABEL: str(i % 30)})
        train, eval_rows, chosen = study_split(rows, n_studies=16, n_eval=12)
        self.assertFalse(set(r["doc"] for r in train) & set(r["doc"] for r in eval_rows))
        self.assertEqual(len(eval_rows), 12)
        self.assertEqual(len(chosen), 16)

    def test_no_outcome_label_or_doc_in_prompt(self):
        row = {"doc": "STUDY NAME NOT FOR MODEL", "doc_id": "12345", "arm_id": "3",
               LABEL: "89", "(6452745, '1.1.Goal setting (behavior)')": "1",
               "(6452948, '11.1 Pharmacological support')": "1"}
        p = create_prompt(row)
        self.assertNotIn("89", p)
        self.assertNotIn("STUDY NAME NOT FOR MODEL", p)
        self.assertNotIn("12345", p)
        self.assertIn("Goal setting", p)
        self.assertIn("Pharmacological", p)

    def test_missing_rows_do_not_use_target(self):
        row = {"doc": "sample", LABEL: "53", "('Outcome', 'Outcome')": "53"}
        p = create_prompt(row)
        self.assertNotIn("53", p)

    def test_unlabeled_rows_are_not_used_in_split(self):
        rows = []
        for i in range(45):
            rows.append({"doc": f"s{i}", "doc_id": str(i), "arm_id": str(i),
                         LABEL: "NA" if i == 0 else "9"})
        t, e, c = study_split(rows, n_studies=16, n_eval=12)
        self.assertTrue(all(r[LABEL] != "NA" for r in t + e))

    def test_no_target_in_numeric_feature_flags(self):
        row = {"doc":"study","arm_id":"1", LABEL:"89",
               "(6452948, '11.1 Pharmacological support')":"1",
               "('Outcome', 'Outcome')":"89"}
        flags = present_features(row)
        self.assertTrue(flags)
        self.assertFalse(any("Outcome" in flag for flag in flags))


if __name__ == "__main__":
    unittest.main()
