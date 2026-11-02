import importlib.util
import json
import os
import signal
import time
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
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

    def test_upstream_zero_with_unknown_basis_is_not_free_model_usage(self):
        b = self.implementation()
        row = {"passed": True, "error": None, "grader_errors": [], "turns": [{"exit_code": 0, "timed_out": False}], "cost_usd": 0}
        self.assertIsNone(b.summarize_process([row], expected=1, model_cost_basis="unknown")["model_cost_usd"])

    def test_missing_executable_still_records_missing_artifact(self):
        b = self.implementation()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            args = SimpleNamespace(suite="business-process", sources=root, state=root,
                                   run_id="no-executable", seed=0, policy="oracle", task="payment-run",
                                   faults=None, wall_seconds=1)
            with patch.object(b, "source_info", return_value=(root, {"commit": "test"})), patch.object(b, "command_for", return_value=(["/nonexistent-businessrun-executable"], root, "test")):
                code = b.execute(args)
            receipt = json.loads((root / "runs/no-executable/receipt.json").read_text())
            self.assertEqual(code, 127)
            self.assertFalse(receipt["artifact_present"])
            self.assertEqual(receipt["summary"]["missing"], 1)
            self.assertEqual(receipt["error_class"], "executable_not_found")

    def test_wall_timeout_stops_child_in_a_separate_session(self):
        b = self.implementation()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            pidfile = root / "child.pid"
            script = root / "spawn.py"
            script.write_text("import subprocess,sys,time,pathlib\np=subprocess.Popen([sys.executable,'-c', 'import time; time.sleep(60)'],start_new_session=True)\npathlib.Path(sys.argv[1]).write_text(str(p.pid))\ntime.sleep(60)\n")
            args = SimpleNamespace(suite="business-process", sources=root, state=root, run_id="timeout",
                                   seed=0, policy="oracle", task="payment-run", faults=None, wall_seconds=1)
            try:
                with patch.object(b, "source_info", return_value=(root, {"commit": "test"})), patch.object(b, "command_for", return_value=([sys.executable, str(script), str(pidfile)], root, "test")):
                    code = b.execute(args)
                pid = int(pidfile.read_text())
                state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
                self.assertTrue(not state or state.startswith("Z"), "detached child is still running")
                self.assertEqual(code, 124)
            finally:
                if pidfile.exists():
                    try: os.kill(int(pidfile.read_text()), signal.SIGKILL)
                    except ProcessLookupError: pass

    def test_diagnostics_expose_only_exception_type_and_module_name(self):
        b = self.implementation()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "stderr.log").write_text("secret-token-private\nModuleNotFoundError: No module named 'requests'\nRuntimeError: api token secret-token-private\n")
            result = b.failure_diagnostics(root)
            self.assertIn("requests", json.dumps(result))
            self.assertIn("RuntimeError", json.dumps(result))
            self.assertNotIn("secret-token-private", json.dumps(result))
            self.assertNotIn(str(root), json.dumps(result))

    def test_diagnostics_mask_arbitrary_identifiers(self):
        b = self.implementation()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "PRIVATE_FILE.log").write_text("ModuleNotFoundError: No module named 'PRIVATE_MODULE'\nPRIVATE_CLASSError: confidential\n")
            result = json.dumps(b.failure_diagnostics(root))
            for value in ["PRIVATE_FILE", "PRIVATE_MODULE", "PRIVATE_CLASS", "confidential"]:
                self.assertNotIn(value, result)
            self.assertIn("other", result)

    def test_process_cache_and_outputs_are_separate_for_identical_task_seed(self):
        b = self.implementation()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / "source"
            for part in ["bench", "tasks", "erp"]: (source / part).mkdir(parents=True)
            (source / "bench/write.py").write_text("import pathlib,sys\np=pathlib.Path(__file__).absolute().parent.parent / '.cache'\np.mkdir(exist_ok=True)\n(p/'seed0').write_text(sys.argv[1])\n")
            paths = []
            for name in ["first", "second"]:
                run = b.new_run(root, name)
                p = b.process_workspace(source, run)
                subprocess.run([sys.executable, str(p / "bench/write.py"), name], cwd=p, check=True)
                paths.append(p / ".cache/seed0")
            self.assertEqual(paths[0].read_text(), "first")
            self.assertEqual(paths[1].read_text(), "second")
            self.assertFalse((source / ".cache").exists())

if __name__ == "__main__": unittest.main()
