"""Observable receipt replay and frozen-value regression checks."""
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("managerbench", HERE / "run.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class ReplayTest(unittest.TestCase):
    def test_recorded_numbers(self):
        d = runner.finite(runner.aggregate(runner.ROOT))
        rows = {(r["condition"], r["task"], r["arm"]): r for r in d["rows"]}
        expected = [
            ("v2.0", "prior", 22, 37, .1243),
            ("v2.1", "prior", 78, 140, .1343),
            ("v2.2", "prior", 169, 294, .1265),
            ("v2.2", "pairwise_logistic", 147, 294, .1442),
            ("v2.2", "ridge_blend", 161, 294, .1327),
            ("v2.2", "ridge_pure", 156, 294, .1354),
        ]
        for version, arm, correct, n, regret in expected:
            r = rows[version, "pair_choice", arm]
            self.assertEqual(r["metrics"]["n_correct"], correct)
            self.assertEqual(r["metrics"]["n_human_non_tied"], n)
            self.assertEqual(round(r["metrics"]["mean_regret"], 4), regret)
            self.assertEqual(r["abstention_rate"], 0)
        r = rows["v1-actions-24", "pair_choice", "befm15-4b"]
        self.assertEqual(r["metrics"]["strict_accuracy"], 10/18)
        self.assertEqual(round(r["metrics"]["mean_regret"], 4), .1333)
        self.assertIsNone(r["abstention_rate"])
        self.assertEqual(sum(r["condition"] == "behaviorbench-full" for r in d["rows"]), 46)
        self.assertEqual(sum(r["condition"] == "behaviorbench-final" for r in d["rows"]), 66)
        final_incomplete = [x for x in d["incomplete"] if x["key"].startswith("behaviorbench-final:")]
        self.assertEqual(len(final_incomplete), 2)
        self.assertEqual({x["key"] for x in final_incomplete}, {
            "behaviorbench-final:qwen3-4b-instruct-2507|multiround_behavior_guessing",
            "behaviorbench-final:qwen3-4b-instruct-2507|multiround_behavior_push_pull"})
        for x in final_incomplete:
            self.assertEqual(x["n_receipted"], 0)
        r = rows["behaviorbench-final", "ieo_economics", "befm15-4b"]
        self.assertEqual(r["n"], 124)
        self.assertEqual(r["metrics"]["accuracy_multi_choice"], 0.5)

    def test_final68_completion_rows(self):
        d = runner.finite(runner.aggregate(runner.ROOT))
        rows = {(r["condition"], r["task"], r["arm"]): r for r in d["rows"]}
        self.assertEqual(sum(r["condition"] == "behaviorbench-final-68" for r in d["rows"]), 68)
        self.assertEqual([x for x in d["incomplete"] if x["key"].startswith("behaviorbench-final-68:")], [])
        cond = d["conditions"]["behaviorbench-final-68"]
        self.assertEqual(cond["coverage"], {"complete": 68, "total": 68, "remaining": 0})
        self.assertEqual(cond["receipts"]["count"], 121)
        src68 = json.loads((runner.ROOT / "files/eval/behaviorbench-full-coverage-final-68of68-2026-11-14.json").read_text())
        import hashlib as hl
        manifest = json.dumps(src68["receipts"], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        self.assertEqual(cond["receipts"]["manifest_sha256"], hl.sha256(manifest.encode()).hexdigest())
        # The 2 completion rows: source omits n and metadata, so n comes from
        # n_receipted (500) and invalid_count stays unmeasured (None), never 0.
        g = rows["behaviorbench-final-68", "multiround_behavior_guessing", "qwen3-4b-instruct-2507"]
        self.assertEqual(g["n"], 500)
        self.assertEqual(g["metrics"]["MAE_with_normalization_mae"], 13.0358)
        self.assertIsNone(g["invalid_count"])
        p = rows["behaviorbench-final-68", "multiround_behavior_push_pull", "qwen3-4b-instruct-2507"]
        self.assertEqual(p["n"], 500)
        self.assertEqual(p["metrics"]["Accuracy"], 0.556)
        self.assertIsNone(p["invalid_count"])
        gap = cond["receipt_gap"]
        self.assertIsNone(gap["model_bytes_sha256"])
        self.assertIsNone(gap["prompt_version"])
        self.assertIsNone(gap["generation_seed"])

    def test_final_receipt_gap_is_explicit(self):
        d = runner.finite(runner.aggregate(runner.ROOT))
        cond = d["conditions"]["behaviorbench-final"]
        self.assertEqual(cond["receipts"]["count"], 116)
        final_src = json.loads((runner.ROOT / "files/eval/behaviorbench-full-coverage-final-2026-11-13.json").read_text())
        import hashlib as hl
        manifest = json.dumps(final_src["receipts"], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        self.assertEqual(cond["receipts"]["manifest_sha256"], hl.sha256(manifest.encode()).hexdigest())
        self.assertEqual(cond["github_actions_inherited"]["value"]["wave2_run"], 43187535316)
        gap = cond["receipt_gap"]
        # Unrecorded provenance stays null (unmeasured); it is never back-filled
        # from the v1 GGUF receipt or any other run.
        self.assertIsNone(gap["model_bytes_sha256"])
        self.assertIsNone(gap["prompt_version"])
        self.assertIsNone(gap["generation_seed"])

    def test_earlier_full_coverage_receipts_unchanged(self):
        old = json.loads((runner.ROOT / "files/eval/behaviorbench-full-coverage-2026-11-12.json").read_text())
        latest = json.loads((runner.ROOT / "files/eval/behaviorbench-full-coverage-2026-11-12-2150.json").read_text())
        complete = {k:r for k,r in old["arms_llm_aggregate"].items() if r["status"] == "OK"}
        self.assertEqual(len(complete), 6)
        for key, row in complete.items():
            self.assertEqual(row["metrics_official"], latest[key]["metrics_official"])

    def test_changed_score_fails_closed(self):
        baseline = json.loads((HERE / "baseline-2026-11-12.json").read_text())
        changed = copy.deepcopy(baseline)
        changed["rows"][0]["n"] += 1
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "changed.json"
            path.write_text(json.dumps(changed))
            p = subprocess.run([sys.executable, str(HERE / "run.py"), "--check", str(path)],
                               capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("REPRODUCTION_CONDITION_DIFFERENCE", p.stderr)


if __name__ == "__main__":
    unittest.main()
