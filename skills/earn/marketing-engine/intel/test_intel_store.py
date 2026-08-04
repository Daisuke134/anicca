#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

import intel_store


HERE = pathlib.Path(__file__).resolve().parent


class CanonicalStoreTests(unittest.TestCase):
    def test_gate7_seed_rows_remain_intact_after_later_store_growth(self):
        result = intel_store.validate_all(HERE)
        self.assertTrue(result["passed"])
        rows = intel_store.read_jsonl(HERE / "playbook.jsonl")
        seed_ids = {
            "tactic.gotcha-prd.v1", "tactic.content-first-product.v1",
            "tactic.feed-engineering-creators.v1", "tactic.paid-promo-outreach.v1",
            "tactic.annual-only-trial.v1", "tactic.gotcha-before-paywall.v1",
            "tactic.ad-mechanism-replication.v1", "tactic.parallel-build-ugc.v1",
            "tactic.minimum-format-cohort.v1", "tactic.fixed-character-identity.v1",
        }
        seeds = [row for row in rows if row["id"] in seed_ids]
        self.assertEqual({row["id"] for row in seeds}, seed_ids)
        self.assertEqual(sum(row["status"] == "new" for row in seeds), 9)
        self.assertEqual(sum(row["status"] == "done" for row in seeds), 1)
        self.assertEqual(sum(row["status"] == "won" for row in rows), 0)
        self.assertGreaterEqual(result["counts"]["playbook"], 10)

    def test_all_schemas_are_draft_2020_12_and_object_records(self):
        for store_name in intel_store.STORES:
            with self.subTest(store_name=store_name):
                schema = json.loads((HERE / "schemas" / f"{store_name}.schema.json").read_text())
                self.assertEqual(schema["$schema"],
                                 "https://json-schema.org/draft/2020-12/schema")
                self.assertEqual(schema["type"], "object")

    def test_duplicate_ids_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "playbook.jsonl"
            row = intel_store.read_jsonl(HERE / "playbook.jsonl")[0]
            path.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n")
            with self.assertRaisesRegex(intel_store.StoreError, "duplicate"):
                intel_store.validate_store(path, "playbook")

    def test_blank_line_and_bom_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            row = intel_store.read_jsonl(HERE / "playbook.jsonl")[0]
            blank = root / "blank.jsonl"
            blank.write_text(json.dumps(row) + "\n\n")
            with self.assertRaisesRegex(intel_store.StoreError, "blank"):
                intel_store.validate_store(blank, "playbook")
            bom = root / "bom.jsonl"
            bom.write_bytes(b"\xef\xbb\xbf" + json.dumps(row).encode() + b"\n")
            with self.assertRaisesRegex(intel_store.StoreError, "BOM"):
                intel_store.validate_store(bom, "playbook")

    def test_missing_source_null_reason_and_invalid_status_fail(self):
        row = intel_store.read_jsonl(HERE / "playbook.jsonl")[0]
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "bad.jsonl"
            bad = dict(row, source_url=None, source_null_reason=None)
            path.write_text(json.dumps(bad) + "\n")
            with self.assertRaisesRegex(intel_store.StoreError, "source_null_reason"):
                intel_store.validate_store(path, "playbook")
            bad = dict(row, status="viral")
            path.write_text(json.dumps(bad) + "\n")
            with self.assertRaisesRegex(intel_store.StoreError, "status"):
                intel_store.validate_store(path, "playbook")

    def test_new_tactic_cannot_claim_result_and_done_requires_result(self):
        rows = intel_store.read_jsonl(HERE / "playbook.jsonl")
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "bad.jsonl"
            new_row = next(row for row in rows if row["status"] == "new")
            path.write_text(json.dumps(dict(new_row, our_result="made money")) + "\n")
            with self.assertRaisesRegex(intel_store.StoreError, "our_result"):
                intel_store.validate_store(path, "playbook")
            done_row = next(row for row in rows if row["status"] == "done")
            path.write_text(json.dumps(dict(done_row, our_result=None)) + "\n")
            with self.assertRaisesRegex(intel_store.StoreError, "our_result"):
                intel_store.validate_store(path, "playbook")


if __name__ == "__main__":
    unittest.main()
