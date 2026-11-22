#!/usr/bin/env python3
"""Synthetic provenance tests, not live model calls or humor measurement."""
import json
import tempfile
import unittest
from pathlib import Path
from audit_comparison_provenance import audit


def record(model, task, sample, receipt):
    return dict(run_id=f"trial-{model}-{sample}", task_id=task, model=model,
                model_version="test-model-v1", skill_version="0.2.1",
                skill_commit="a"*40, skill_blob_sha="b"*40,
                sample_index=sample, response="例文",
                modality="text", temperature=0.5, effort="medium",
                max_output_tokens=256, invocation_source="provider_api",
                provider_receipt=receipt)


class ProvenanceTests(unittest.TestCase):
    def evaluate(self, records):
        with tempfile.TemporaryDirectory() as tmp:
            tasks = Path(tmp) / "tasks.jsonl"
            responses = Path(tmp) / "responses.jsonl"
            tasks.write_text('{"id":"t1"}\n{"id":"t2"}\n', encoding="utf-8")
            responses.write_text("".join(json.dumps(row, ensure_ascii=False)+"\n" for row in records),
                                 encoding="utf-8")
            return audit(tasks, responses)

    def paired(self):
        return [record(m, t, s, f"{m}-{t}-{s}")
                for m in ("model-a", "model-b") for t in ("t1", "t2") for s in (1, 2)]

    def test_valid_complete_metadata_is_only_setup_not_humor(self):
        result = self.evaluate(self.paired())
        self.assertEqual(result["comparison_setup"], "COMPARISON_INPUTS_AUDITED")
        self.assertEqual(result["humor_quality"], "NOT_MEASURED")
        self.assertEqual(result["receipt_authenticity"], "NOT_VERIFIED")

    def test_one_chat_model_is_not_comparable(self):
        rows = self.paired()[:4]
        for row in rows:
            row["invocation_source"] = "chat_session"
            row["provider_receipt"] = None
        result = self.evaluate(rows)
        self.assertEqual(result["comparison_setup"], "NOT_COMPARABLE")
        self.assertIn("fewer_than_two_models", result["reasons"])
        self.assertIn("no_verified_independent_invocation", result["reasons"])

    def test_mismatched_skill_is_rejected(self):
        rows = self.paired()
        rows[-1]["skill_blob_sha"] = "c"*40
        self.assertIn("skill_version_mismatch", self.evaluate(rows)["reasons"])

    def test_unbalanced_task_sample_is_rejected(self):
        rows = self.paired()[:-1]
        self.assertIn("unequal_task_sample_coverage", self.evaluate(rows)["reasons"])

    def test_duplicate_model_task_sample_is_rejected(self):
        rows = self.paired()
        rows.append(dict(rows[0], provider_receipt="extra"))
        self.assertIn("duplicate_model_task_sample", self.evaluate(rows)["reasons"])

    def test_receipt_collision_is_rejected(self):
        rows = self.paired()
        rows[-1]["provider_receipt"] = rows[0]["provider_receipt"]
        self.assertIn("duplicate_provider_receipt", self.evaluate(rows)["reasons"])

    def test_settings_mismatch_is_rejected(self):
        rows = self.paired()
        rows[-1]["temperature"] = 0.9
        self.assertIn("generation_settings_mismatch", self.evaluate(rows)["reasons"])

    def test_unknown_task_raises(self):
        rows = self.paired()
        rows[-1]["task_id"] = "unknown"
        with self.assertRaises(ValueError):
            self.evaluate(rows)

    def test_noninteger_sample_index_raises(self):
        rows = self.paired()
        rows[0]["sample_index"] = True
        with self.assertRaises(ValueError):
            self.evaluate(rows)


if __name__ == "__main__":
    unittest.main()
