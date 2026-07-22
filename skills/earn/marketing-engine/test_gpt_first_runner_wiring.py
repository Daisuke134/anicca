import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "earn" / "marketing-engine"
RUN_AGENT = ENGINE / "run_agent.sh"
CONSUMERS = (
    ROOT / "self" / "capafy-loop" / "capafy-loop-daily.sh",
    ROOT / "earn" / "capafy-marketing" / "capafy-ig-marketing-daily.sh",
    ROOT / "earn" / "clip" / "clip_daily.sh",
    ENGINE / "spawn-marketing-loop.sh",
    ROOT / "self" / "self-fix.sh",
)

EXPECTED_TASK_CLASSES = {
    ROOT / "self" / "capafy-loop" / "capafy-loop-daily.sh": "tool-agent",
    ROOT / "earn" / "capafy-marketing" / "capafy-ig-marketing-daily.sh": "tool-agent",
    ROOT / "earn" / "clip" / "clip_daily.sh": "tool-agent",
    ENGINE / "spawn-marketing-loop.sh": "repeatable-agent",
    ROOT / "self" / "self-fix.sh": "high-value-agent",
}


class GptFirstRunnerWiringTest(unittest.TestCase):
    def test_revenue_consumers_use_shared_runner_without_provider_or_model_names(self):
        for script in CONSUMERS:
            with self.subTest(script=script):
                text = script.read_text(encoding="utf-8")
                self.assertIn("run_agent.sh", text)
                self.assertIn(f"--task-class {EXPECTED_TASK_CLASSES[script]}", text)
                self.assertNotRegex(text, r"command -v claude|\$CLAUDE|claude\s+-p|--model\s+sonnet")
                self.assertNotRegex(text, r"codex\s+exec|gpt-5(?:\.|-)" )

    def test_shared_runner_passes_task_class_only_and_records_contract_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args_file = root / "args.json"
            fake_runner = root / "agent-runner"
            fake_runner.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, pathlib, sys\n"
                "args = sys.argv[1:]\n"
                "pathlib.Path(os.environ['ARGS_FILE']).write_text(json.dumps(args))\n"
                "evidence = pathlib.Path(args[args.index('--evidence-dir') + 1])\n"
                "evidence.mkdir(parents=True, exist_ok=True)\n"
                "(evidence / 'summary.json').write_text(json.dumps({\n"
                "  'status': 'success', 'selected_provider': 'codex',\n"
                "  'selected_model': 'fixture-gpt', 'attempt_count': 1}))\n"
                "sys.exit(0)\n",
                encoding="utf-8",
            )
            fake_runner.chmod(0o755)
            evidence = root / "evidence"
            env = os.environ.copy()
            env.update({"AGENT_RUNNER_BIN": str(fake_runner), "ARGS_FILE": str(args_file)})
            proc = subprocess.run(
                [
                    "bash", str(RUN_AGENT), "--task-class", "tool-agent",
                    "--evidence-dir", str(evidence), "--task-label", "capafy-fixture",
                ],
                input="Do one bounded fixture pass.\n",
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            args = json.loads(args_file.read_text(encoding="utf-8"))
            self.assertEqual(args[args.index("--task-class") + 1], "tool-agent")
            self.assertNotIn("--model", args)
            self.assertFalse(any("sonnet" in arg or arg.startswith("gpt-") for arg in args))
            summary = json.loads((evidence / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["attempt_count"], 1)

    def test_shared_output_schemas_are_strict_codex_contracts(self):
        for name in ("loop_pass.schema.json", "manifest_judgment.schema.json"):
            with self.subTest(schema=name):
                schema = json.loads((ENGINE / "schemas" / name).read_text(encoding="utf-8"))
                self.assertIs(schema["additionalProperties"], False)
                self.assertEqual(schema["properties"]["status"]["type"], "string")
                self.assertTrue(set(schema["properties"]).issubset(set(schema["required"])))


if __name__ == "__main__":
    unittest.main(verbosity=2)
