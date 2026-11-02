import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent

class RunnerContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("businessrun", HERE / "bench.py")
        if not spec or not spec.loader or not (HERE / "bench.py").exists():
            cls.b = None
        else:
            cls.b = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.b)

    def implementation(self):
        self.assertIsNotNone(self.b, "executable benchmark runner is missing")
        return self.b

    def test_incomplete_and_failed_process_attempts_are_retained(self):
        b = self.implementation()
        rows = [{"passed": True, "error": None, "grader_errors": [], "turns": [{"exit_code": 0, "timed_out": False}], "cost_usd": None},
                {"passed": False, "error": "timeout", "grader_errors": [], "turns": [{"exit_code": 124, "timed_out": True}], "cost_usd": None}]
        r = b.summarize_process(rows, expected=3)
        self.assertEqual((r["attempts"], r["passed"], r["missing"]), (2, 1, 1))
        self.assertFalse(r["campaign_complete"])
        self.assertIsNone(r["model_cost_usd"])

    def test_grader_pass_does_not_hide_failed_agent_execution(self):
        b = self.implementation()
        row = {"passed": True, "error": None, "grader_errors": [], "turns": [{"exit_code": 1, "timed_out": False}], "cost_usd": 0.1}
        r = b.summarize_process([row], expected=1)
        self.assertEqual(r["passed"], 0)
        self.assertEqual(r["invalid"], 1)

    def test_receipt_does_not_publish_private_raw_fields(self):
        b = self.implementation()
        raw = {"passed": True, "error": None, "grader_errors": [], "turns": [{"exit_code": 0, "timed_out": False}], "cost_usd": 0.2,
               "ERP_TOKEN": "private-token", "work_dir": "/private/home", "response": "secret"}
        result = json.dumps(b.summarize_process([raw], expected=1))
        for s in ["private-token", "/private/home", "secret"]:
            self.assertNotIn(s, result)

    def test_duplicate_trial_identity_is_rejected(self):
        b = self.implementation()
        row = {"run_id": "a", "passed": True, "error": None, "grader_errors": [], "turns": [{"exit_code": 0, "timed_out": False}], "cost_usd": 0}
        with self.assertRaises(ValueError): b.summarize_process([row, row], expected=2)

    def test_existing_run_directory_is_never_overwritten(self):
        b = self.implementation()
        with tempfile.TemporaryDirectory() as d:
            p = b.new_run(Path(d), "run-1")
            (p / "receipt.json").write_text("original")
            with self.assertRaises(FileExistsError): b.new_run(Path(d), "run-1")
            self.assertEqual((p / "receipt.json").read_text(), "original")
            with self.assertRaises(ValueError): b.new_run(Path(d), "../outside")

    def test_zero_success_has_no_cost_per_success(self):
        b = self.implementation()
        row = {"passed": False, "error": None, "grader_errors": [], "turns": [{"exit_code": 0, "timed_out": False}], "cost_usd": 0.2}
        r = b.summarize_process([row], expected=1)
        self.assertTrue(r["campaign_complete"])
        self.assertIsNone(r["cost_per_success_usd"])

if __name__ == "__main__": unittest.main()
